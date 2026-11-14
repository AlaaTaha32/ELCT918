`timescale 1ns/1ps
//==============================================================================
// carat_sw16_top.v  --  Nexys 4 DDR demo: ONE multiplication with the 16 switches
//------------------------------------------------------------------------------
//   SW[7:0]   x : FP8 E4M3 input   {S, E[3:0], M[2:0]}   (SW[7] = sign)
//   SW[15:8]  w : signed INT8 weight (two's complement)   (SW[15] = sign)
//   7-segment : the result x*w in Q20.12, as 8 hex digits with a point:
//                  IIIII.FFF   (5 hex digits integer part, 3 hex digits fraction)
//               e.g. 6.875  -> 00006.E00   (E00 hex = 14/16 = 0.875)
//   BTNC      : toggles the display mode
//                  mode 1 (default, LED14 on) : SIGN-MAGNITUDE  -> shows |x*w|,
//                                               LED15 tells if the result is negative
//                  mode 0                     : RAW two's complement as the column outputs it
//   BTNU      : "step" button, used only when AUTO_RUN = 0
//   LED[15]   : result is negative        LED[14] : sign-magnitude mode
//   LED[0]    : column ready
//   LED[1]    : x is zero (+0/-0)    LED[2] : x is NaN (result shown as 0)
//   CPU_RESETN: reset
//
// How it works
//   The design under test is the N_PE-row carat_column (default 8).  The same x is
//   given to all rows (x_flat = {N_PE{x}}) and row 0 is displayed.  The column multiplies by
//   addition only (Carat), exactly as in simulation.
//   AUTO_RUN = 1 : the column is restarted all the time, so the display follows the
//                  switches about 0.3 microseconds after you move them (no button).
//   AUTO_RUN = 0 : a new multiplication is done only when BTNU is pressed (step mode).
//==============================================================================
module carat_sw16_top #(
    parameter N_PE            = 8,         // rows in the column (1 = single PE row)
    parameter AUTO_RUN        = 1,
    parameter DEBOUNCE_CYCLES = 1000000,   // 10 ms at 100 MHz
    parameter SCAN_BITS       = 17         // 7-segment scan counter width
)(
    input  wire        CLK100MHZ,
    input  wire        CPU_RESETN,
    input  wire [15:0] SW,
    input  wire        BTNC,
    input  wire        BTNU,
    output wire [15:0] LED,
    output wire [6:0]  SEG,
    output wire        DP,
    output wire [7:0]  AN
);
    wire clk = CLK100MHZ;

    // ---- reset synchronizer ------------------------------------------------
    reg rst_s0, rst_n;
    always @(posedge clk) begin
        rst_s0 <= CPU_RESETN;
        rst_n  <= rst_s0;
    end

    // ---- switch synchronizer (2 flip-flops per switch) ---------------------
    reg [15:0] sw_s0, sw_s1;
    always @(posedge clk) begin
        sw_s0 <= SW;
        sw_s1 <= sw_s0;
    end
    wire [7:0]        x_in = sw_s1[7:0];      // FP8 E4M3
    wire signed [7:0] w_in = sw_s1[15:8];     // INT8

    // ---- buttons -----------------------------------------------------------
    wire mode_pulse, step_pulse;
    btn_pulse #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) u_btn_mode (.clk(clk), .rst_n(rst_n), .btn_in(BTNC), .pulse(mode_pulse));
    btn_pulse #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) u_btn_step (.clk(clk), .rst_n(rst_n), .btn_in(BTNU), .pulse(step_pulse));

    reg signmag;                               // display mode
    always @(posedge clk) begin
        if (!rst_n)          signmag <= 1'b1;
        else if (mode_pulse) signmag <= ~signmag;
    end

    // ---- the design under test: carat_column --------------------------------
    wire         start = (AUTO_RUN != 0) ? 1'b1 : step_pulse;   // column accepts it only when ready
    wire         col_ready, col_done;
    wire [N_PE*32-1:0] prod_flat;
    wire [N_PE-1:0]    nan_flat, zero_flat;

    carat_column #(.N_PE(N_PE)) u_col (
        .clk(clk), .rst_n(rst_n),
        .start(start),
        .x_flat({N_PE{x_in}}),                 // same x in all N_PE rows
        .w(w_in),
        .ready(col_ready), .done(col_done),
        .prod_flat(prod_flat),
        .nan_flat(nan_flat), .zero_flat(zero_flat)
    );

    // ---- result of row 0 -> display value ------------------------------------
    wire signed [31:0] result = prod_flat[31:0];       // Q20.12, two's complement
    wire               neg    = result[31];
    wire        [31:0] mag    = neg ? (~result + 32'd1) : result;   // |result|
    wire        [31:0] shown  = signmag ? mag : result;

    seg7_hex #(.SCAN_BITS(SCAN_BITS)) u_seg (
        .clk(clk), .rst_n(rst_n),
        .value(shown),
        .dp_mask(8'b0000_1000),                // point after digit 3 -> IIIII.FFF
        .seg(SEG), .an(AN), .dp(DP)
    );

    assign LED = {neg, signmag, 11'd0, nan_flat[0], zero_flat[0], col_ready};

endmodule
