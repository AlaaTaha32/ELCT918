`timescale 1ns/1ps
//==============================================================================
// carat_row.v  --  One row of the Carat column = TC + PE + PO
//------------------------------------------------------------------------------
// Paper reference : Fig. 6(c)/(d)/(e).  The shared counter C and the shared
// accumulator A come from the column (they are NOT inside the row).
//
//   x_in --> [TC] --spike--> [PE] --prod--> [PO] --> result (Q20.12)
//              |  sign/ED/zero/nan -----------^
//              +-- nan/zero flags -> [flag regs, latched with po_en] -> nan_flag, zero_flag
//
// NaN handling: the TC detects NaN; here it is OR-ed into the "zero" mask of the
// PO, so a NaN input gives result = 0 (reference convention) and nan_flag = 1.
// nan_flag / zero_flag are latched at the same edge as result, so they always
// describe the same batch as `result`.
//==============================================================================
module carat_row (
    input  wire               clk,
    input  wire               rst_n,

    input  wire               load,       // new batch: capture x and clear PE
    input  wire        [7:0]  x_in,       // FP8 E4M3 input of this row
    input  wire        [2:0]  c,          // shared counter
    input  wire signed [11:0] a,          // shared partial product
    input  wire               active,     // sweep in progress
    input  wire               po_en,      // latch post-processed result

    output wire signed [31:0] result,     // product x*w in Q20.12 (0 for NaN)
    output reg                nan_flag,   // x was NaN        (valid together with result)
    output reg                zero_flag   // x was +0 or -0   (valid together with result)
);

    wire               spike;
    wire               sign_q, zero_q, nan_q;
    wire signed [4:0]  ed_q;
    wire signed [11:0] sel_unused;
    wire signed [11:0] prod;

    carat_tc u_tc (
        .clk(clk), .rst_n(rst_n),
        .load(load), .x_in(x_in),
        .c(c), .active(active), .spike(spike),
        .sign_q(sign_q), .ed_q(ed_q), .zero_q(zero_q), .nan_q(nan_q)
    );

    carat_pe #(.W(12)) u_pe (
        .clk(clk), .rst_n(rst_n),
        .clear(load),                 // clear the old product when a batch starts
        .spike_in(spike), .a_in(a),
        .sel_out(sel_unused), .prod_q(prod)
    );

    carat_po u_po (
        .clk(clk), .rst_n(rst_n), .en(po_en),
        .prod_in(prod), .sign_in(sign_q), .ed_in(ed_q),
        .zero_in(zero_q | nan_q),     // mask the product to 0 if the input was zero or NaN
        .result_q(result)
    );

    // Flags latched together with the PO result register (same enable, same reset)
    always @(posedge clk) begin
        if (!rst_n) begin
            nan_flag  <= 1'b0;
            zero_flag <= 1'b0;
        end else if (po_en) begin
            nan_flag  <= nan_q;
            zero_flag <= zero_q;
        end
    end

endmodule
