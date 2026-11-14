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
