// ============================================================================
//  nexys4_baseline_top.sv  --  switch + 7-segment test of baseline_column
//                              Digilent Nexys 4 DDR (Artix-7 xc7a100tcsg324-1)
//
//  HOW TO USE THE BOARD
//    SW[7:0]    x : FP8 E4M3 input   (SW7 = sign, SW6..SW3 = exponent, SW2..SW0 = mantissa)
//    SW[15:8]   w : signed INT8 weight, two's complement (SW15 = sign bit)
//    Display    y = x * w as a Q20.12 number, 8 hex digits, with a decimal point:
//
//                    AN7 AN6 AN5 AN4 AN3 AN2 AN1 AN0
//                     0   0   0   0   3 . 0   0   0       -> 0x00003000 = 3.0
//                     \_____ integer ____/   \_ fraction _/
//
//               The 12 fractional bits are exactly the 3 right-hand hex digits, so
//               the three digits after the point are the fraction in units of 1/4096
//               (0x800 = .5, 0x400 = .25, 0x008 = 2^-9 ...).  Negative results are
//               two's complement: -1.0 is FFFFF.000.
//    LED0       NaN flag (x = 0x7F or 0xFF).  The display then shows 0.
//    LED1       "done" from the baseline (should be on all the time)
//
//  The baseline is free-running: start is tied to 1, so the result follows the
//  switches within a couple of clock cycles.
//
//  Needs: baseline_column.sv  (ROWS = 1; one multiplier is enough to test the logic)
// ============================================================================
`timescale 1ns/1ps

module nexys4_baseline_top (
    input  logic        CLK100MHZ,      // 100 MHz oscillator
    input  logic       CPU_RESETN,      // pushbutton, active low
    input  logic [15:0] SW,             // slide switches
    output logic [15:0] LED,
    output logic [7:0]  AN,             // digit enables, active low (AN0 = right-most digit)
    output logic [6:0]  SEG,            // {CG,CF,CE,CD,CC,CB,CA}, active low
    output logic        DP              // decimal point, active low
);

    // ------------------------------------------------------------------
    //  1. Synchronise the switches (they are asynchronous to the clock).
    //     Two flip-flops in series; ASYNC_REG tells Vivado to place them together.
    // ------------------------------------------------------------------
    (* ASYNC_REG = "TRUE" *) logic [15:0] sw_meta;
    (* ASYNC_REG = "TRUE" *) logic [15:0] sw_sync;

    always_ff @(posedge CLK100MHZ) begin
        sw_meta <= SW;
        sw_sync <= sw_meta;
    end

    wire [7:0] x_in = sw_sync[7:0];     // FP8 E4M3 input
    wire [7:0] w_in = sw_sync[15:8];    // signed INT8 weight

    // ------------------------------------------------------------------
    //  2. Device under test: the conventional FP8 x INT8 multiplier
    // ------------------------------------------------------------------
    wire        done;
    wire [31:0] y;                      // Q20.12 result
    wire [0:0]  nan_f;

    
    btn_pulse u_resetn (
        .clk   (CLK100MHZ),
        .rst_n (1'b1),                  // no reset for the button conditioner
        .btn_in(CPU_RESETN),
        .pulse (CPU_RESETN_debounced)
    );
    
    
    baseline_column #(.ROWS(1)) u_baseline (
        .clk      (CLK100MHZ),
        .rst_n    (CPU_RESETN_debounced),
        .start    (1'b1),               // free-running: compute every clock cycle
        .w        (w_in),
        .x_flat   (x_in),
        .done     (done),
        .y_flat   (y),
        .nan_flat (nan_f)
    );

    assign LED = {14'd0, done, nan_f[0]};

    // ------------------------------------------------------------------
    //  3. 8-digit multiplexed 7-segment display
    //     A 19-bit counter's top 3 bits pick the digit: each digit is lit for
    //     2^16 clocks = 0.66 ms, so the whole display refreshes at ~190 Hz.
    // ------------------------------------------------------------------
    logic [18:0] refresh_cnt = '0;
    always_ff @(posedge CLK100MHZ) refresh_cnt <= refresh_cnt + 1'b1;

    wire [2:0] sel = refresh_cnt[18:16];        // which digit is lit now (0 = right-most)

    logic [3:0] nibble;

    always_comb begin
        nibble = y[4*sel +: 4];                 // the 4 bits of y shown on that digit

        AN      = 8'hFF;                        // all digits off ...
        AN[sel] = 1'b0;                         // ... except the selected one (active low)

        DP = (sel != 3'd3);                     // point lit (low) on digit 3 = between the
                                                // 5 integer digits and the 3 fraction digits

        // hex digit -> segments {g,f,e,d,c,b,a}, 0 = lit
        case (nibble)
            4'h0: SEG = 7'b1000000;
            4'h1: SEG = 7'b1111001;
            4'h2: SEG = 7'b0100100;
            4'h3: SEG = 7'b0110000;
            4'h4: SEG = 7'b0011001;
            4'h5: SEG = 7'b0010010;
            4'h6: SEG = 7'b0000010;
            4'h7: SEG = 7'b1111000;
            4'h8: SEG = 7'b0000000;
            4'h9: SEG = 7'b0010000;
            4'hA: SEG = 7'b0001000;
            4'hB: SEG = 7'b0000011;             // shown as "b"
            4'hC: SEG = 7'b1000110;
            4'hD: SEG = 7'b0100001;             // shown as "d"
            4'hE: SEG = 7'b0000110;
            4'hF: SEG = 7'b0001110;
        endcase
    end

endmodule






`timescale 1ns/1ps
//===================================================================================
// btn_pulse.v  --  Push-button conditioner: synchronizer + debounce + 1-cycle pulse
//------------------------------------------------------------------------------
// A mechanical button (a) is asynchronous to the clock and (b) bounces for a few
// milliseconds.  This module fixes both and gives ONE clock-cycle pulse per press.
//   1) two flip-flops (s0, s1) synchronize the button to clk
//   2) the synchronized level must differ from the accepted level (stable) for
//      DEBOUNCE_CYCLES clocks in a row before it is accepted
//   3) the pulse is generated when the accepted level goes 0 -> 1 (button pressed)
// 1,000,000 cycles at 100 MHz = 10 ms.
//===================================================================================
module btn_pulse #(
    parameter DEBOUNCE_CYCLES = 1000000
)(
    input  wire clk,
    input  wire rst_n,       // synchronous, active-low
    input  wire btn_in,      // raw button
    output reg  pulse        // 1 clock cycle high per accepted press
);
    reg        s0, s1;       // synchronizer
    reg        stable;       // debounced button level
    reg [23:0] cnt;          // counts how long the level has been different

    always @(posedge clk) begin
        if (!rst_n) begin
            s0 <= 1'b0;  s1 <= 1'b0;
            stable <= 1'b0;  cnt <= 24'd0;  pulse <= 1'b0;
        end else begin
            s0 <= btn_in;
            s1 <= s0;
            pulse <= 1'b0;                       // default: no pulse
            if (s1 == stable) begin
                cnt <= 24'd0;                    // no change pending
            end else begin
                cnt <= cnt + 24'd1;              // level differs: measure how long
                if (cnt == DEBOUNCE_CYCLES - 1) begin
                    stable <= s1;                // accept the new level
                    cnt    <= 24'd0;
                    if (s1) pulse <= 1'b1;       // rising edge = button pressed
                end
            end
        end
    end
endmodule

