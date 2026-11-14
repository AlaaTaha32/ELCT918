`timescale 1ns/1ps
//==============================================================================
// carat_pe.v  --  Carat Processing Element (one per row)
//------------------------------------------------------------------------------
// Paper reference : Carat Section 4.3, Fig. 6(b), Fig. 5(c)
//
// The PE does NOT compute anything.  It only SUBSCRIBES (selects) the partial
// product that is passing by when its temporal spike arrives:
//
//      spike = 1  -> the PE selects  A  (= (8+MD) * w  at that moment)
//      spike = 0  -> the PE outputs  0
//
// Structure (all widths = W bits, default 12 = signed range of 15*w) 
//
//   spike_in --> [mt_q] --+
//                         v
//   a_in ------> [a_q] --> AND ---> sel ---> OR with prod_q ---> [prod_q]
//
//   mt_q  : spike register         (MT register in Fig. 6b)
//   a_q   : partial-product register (A register in Fig. 6b)
//   AND   : sel = mt_q ? a_q : 0   (the "AND gate" of Fig. 6b)
//   prod_q: output product register = the yellow "Val/En" register of Fig. 5.
//           It must exist because the spike lasts only ONE cycle, while the
//           product has to be kept until the post-processing stage reads it.
//           Since only one spike happens per batch, ORing 'sel' into the
//           register is the same as writing it (the paper uses an OR gate
//           to merge PE outputs for the same reason, Section 4.6).
//
// Latency: a spike presented at cycle k gives mt_q/a_q at k+1 and the product
//          in prod_q at k+2.
//==============================================================================
module carat_pe #(
    parameter W = 12                       // width of the partial product A
)(
    input  wire                 clk,
    input  wire                 rst_n,     // synchronous, active-low reset

    input  wire                 clear,     // 1 = erase prod_q (start of a batch)
    input  wire                 spike_in,  // temporal signal from the TC
    input  wire signed [W-1:0]  a_in,      // partial product from the shared ACC

    output wire signed [W-1:0]  sel_out,   // AND-gate output (visible for waveforms)
    output reg  signed [W-1:0]  prod_q     // captured product (8+MD)*w
);

    reg                mt_q;               // registered spike
    reg  signed [W-1:0] a_q;               // registered partial product

    // 1) Pipeline registers: align the spike and the partial product.
    always @(posedge clk) begin
        if (!rst_n) begin
            mt_q <= 1'b0;
            a_q  <= {W{1'b0}};
        end else begin
            mt_q <= spike_in;
            a_q  <= a_in;
        end
    end

    // 2) AND / select: pass A only while the spike is present, else 0.
    assign sel_out = a_q & {W{mt_q}};

    // 3) Output register: clear at batch start, otherwise OR in the selection.
    always @(posedge clk) begin
        if (!rst_n)
            prod_q <= {W{1'b0}};
        else if (clear)
            prod_q <= {W{1'b0}};
        else
            prod_q <= prod_q | sel_out;
    end

endmodule
