`timescale 1ns/1ps
//==============================================================================
// carat_tc.v  --  Temporal Converter (TC) for ONE row of the Carat column
//------------------------------------------------------------------------------
// Paper reference : Carat (ASPLOS'24) Section 4.4, Fig. 6(c), Eq. (1), Fig. 4
//
// What it does
//   1. PRE-PROCESSING of the FP8 E4M3 input x = {S, E[3:0], M[2:0]}
//        - zero detection            (E == 0 and M == 0)
//        - subnormal adjustment      (Eq. 1) so that every non-zero number
//          has the form   (-1)^S * 2^(ED-10) * {1,MD}      (4-bit mantissa)
//   2. Stores S, ED, MD, Zero in registers when a new batch starts (load=1).
//   3. TEMPORAL CODING: spike = (MD == C) while the column is busy.
//        C is the shared counter 0..7, so a number with MD = 5 produces its
//        one-cycle spike on the 5th cycle (Fig. 4).
//
// Number format reminder (E4M3, bias 7)
//   normal    (E != 0): x = (-1)^S * 2^(E-7)  * (1 + M/8)  = 2^(E-10) * (8+M)
//   subnormal (E == 0): x = (-1)^S * 2^(-6)   * (M/8)      = 2^(-9)   * M
//
// Subnormal adjustment (design decision - see report)
//   We shift M left until its leading 1 sits in the "hidden bit" position.
//   Each shift of one position lowers the exponent by one:
//        M = 1xx  -> shift 1 -> MD = {M[1:0],0}   ED =  0
//        M = 01x  -> shift 2 -> MD = {M[0],0,0}   ED = -1
//        M = 001  -> shift 3 -> MD = 000          ED = -2
//   Check  M=3 (011): {0,011} -> {1,100}: 12 * 2^(-1-10) = 3 * 2^-9   (OK)
//   (The paper writes ED = E - offset; we derived the constants ourselves
//    because a subnormal's real exponent is 1-7, not 0-7.)
//   ED is therefore a SIGNED 5-bit number in the range -2 .. 15.
//
// NaN (E=1111, M=111) is DETECTED (nan_q flag, paper Section 4.4 "Product masking").  
// The spike/ED/MD path still treats it as a normal number (harmless);
// the post-processing stage masks the product to 0 and the flag is passed on.
// This matches the reference model convention: NaN -> y = 0, nan = 1.
//==============================================================================
module carat_tc (
    input  wire              clk,
    input  wire              rst_n,     // synchronous, active-low reset

    // ---- loading a new input value ----
    input  wire              load,      // 1 = capture x_in at the next clock edge
    input  wire        [7:0] x_in,      // FP8 E4M3 input {S,E[3:0],M[2:0]}

    // ---- temporal coding ----
    input  wire        [2:0] c,         // shared counter value 0..7
    input  wire              active,    // 1 while the column is sweeping 0..7
    output wire              spike,     // 1-cycle temporal signal (MD == C)

    // ---- side information needed later by the post-processing stage ----
    output reg               sign_q,    // sign of the input
    output reg  signed [4:0] ed_q,      // adjusted exponent ED (signed)
    output reg               zero_q,    // input is exactly zero (+0 or -0)
    output reg               nan_q      // input is NaN (E=1111, M=111)
);

    //--------------------------------------------------------------------------
    // 1) Field extraction (pure wiring)
    //--------------------------------------------------------------------------
    wire       s_in = x_in[7];                              // sign bit of the input
    wire [3:0] e_in = x_in[6:3];                            // exponent field of the input
    wire [2:0] m_in = x_in[2:0];                            // mantissa field of the input

    wire       nan_in = (e_in == 4'hF) && (m_in == 3'h7);   // E4M3 has a single NaN code

    //--------------------------------------------------------------------------
    // 2) Subnormal adjustment (Eq. 1) and zero detection - combinational
    //--------------------------------------------------------------------------
    reg              zero_in;           // input is zero
    reg  signed [4:0] ed_in;            // adjusted exponent
    reg        [2:0] md_in;             // adjusted mantissa (without hidden 1)

    always @(*) begin
        zero_in = 1'b0;
        if (e_in != 4'd0) begin
            // Normal number: no adjustment, hidden bit is already 1.
            ed_in = {1'b0, e_in};       // 1..15 as a positive signed value
            md_in = m_in;
        end else if (m_in[2]) begin     // subnormal, M = 1xx  (shift by 1)
            ed_in = 5'sd0;
            md_in = {m_in[1:0], 1'b0};
        end else if (m_in[1]) begin     // subnormal, M = 01x  (shift by 2)
            ed_in = -5'sd1;
            md_in = {m_in[0], 2'b00};
        end else if (m_in[0]) begin     // subnormal, M = 001  (shift by 3)
            ed_in = -5'sd2;
            md_in = 3'b000;
        end else begin                  // E = 0 and M = 0  -> exact zero
            ed_in   = 5'sd0;            // don't care, product is masked later
            md_in   = 3'b000;
            zero_in = 1'b1;
        end
    end

    //--------------------------------------------------------------------------
    // 3) Registers: hold the adjusted fields for the whole 8-cycle sweep
    //    (the paper: "all registers remain constant during the 8 cycles",
    //     which is why temporal coding has low switching activity)
    //--------------------------------------------------------------------------
    reg [2:0] md_q;                     // adjusted mantissa register

    always @(posedge clk) begin
        if (!rst_n) begin
            sign_q <= 1'b0;
            ed_q   <= 5'sd0;
            md_q   <= 3'd0;
            zero_q <= 1'b0;
            nan_q  <= 1'b0;
        end else if (load) begin
            sign_q <= s_in;
            ed_q   <= ed_in;        // signed adjusted exponent (range -2..15)
            md_q   <= md_in;        // adjusted mantissa (range 0..7), without the hidden 1
            zero_q <= zero_in;
            nan_q  <= nan_in;
        end
    end

    //--------------------------------------------------------------------------
    // 4) Temporal signal: equality comparator (EQ in Fig. 6c)
    //    Produces exactly one spike per sweep, on the cycle where C == MD.
    //--------------------------------------------------------------------------
    assign spike = active && (md_q == c);

endmodule
