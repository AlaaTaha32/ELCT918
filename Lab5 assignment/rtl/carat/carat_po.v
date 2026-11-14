`timescale 1ns/1ps
//==============================================================================
// carat_po.v  --  Post-Processing (PO) for ONE row
//------------------------------------------------------------------------------
// Paper reference : Carat Section 4.4 "Product masking" and Section 4.6
//
// The PE delivered the integer part of the product:
//         prod = (8 + MD) * w              (signed 12 bit)
// The full result is:
//         result = (-1)^S * 2^(ED-10) * prod
// We output it in fixed point Q20.12 (20 integer bits, 12 fraction bits), i.e.
// the real value multiplied by 2^12:
//         out = (-1)^S * prod * 2^(ED-10+12) = (-1)^S * prod * 2^(ED+2)
// Because ED >= -2 the shift (ED+2) is always 0..17 -> the result is an
// exact integer, no rounding is needed.
//
// Steps:  1) shift left by (ED+2)     2) negate if S = 1     3) force 0 if Z
// The output is REGISTERED and only updated when en = 1, so it stays stable
// until the next batch is finished.
//==============================================================================
module carat_po (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               en,        // 1 = latch the result now
    input  wire signed [11:0] prod_in,   // (8+MD)*w from the PE
    input  wire               sign_in,   // S of the FP8 input
    input  wire signed [4:0]  ed_in,     // adjusted exponent ED (-2..15)
    input  wire               zero_in,   // input was zero -> product masked, also true for NaN
    output reg  signed [31:0] result_q   // Q20.12 product
);

    // shift amount = ED + 2  (0..17)  -> 5 bits is enough
    wire [4:0] shamt = ed_in + 5'sd2;

    // 1) sign-extend to 32 bits, then shift (a shift is just wiring/muxes)
    wire signed [31:0] shifted = $signed({{20{prod_in[11]}}, prod_in}) <<< shamt;

    // 2) apply the sign of x   3) apply the zero mask
    wire signed [31:0] signed_val = sign_in ? -shifted : shifted;
    wire signed [31:0] final_val  = zero_in ? 32'sd0 : signed_val;

    always @(posedge clk) begin
        if (!rst_n)
            result_q <= 32'sd0;
        else if (en)
            result_q <= final_val;
    end

endmodule
