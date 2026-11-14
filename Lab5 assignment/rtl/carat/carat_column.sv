`timescale 1ns/1ps
//==============================================================================
// carat_column.v  --  Carat PE column: N_PE rows, 1 shared counter, 1 shared ACC
//------------------------------------------------------------------------------
// Paper reference : Carat Section 4.5, Fig. 6(d), Fig. 5(d), Section 4.4
//                   "Accumulation forwarding"
//
// Computes N_PE products  x[i] * w  (x[i] = FP8 E4M3, w = INT8) with NO multiplier
//
// PARAMETER N_PE : number of rows = number of inputs = number of products.
//   N_PE = 1  -> a single row (one TC + one PE row), handy for debugging
//   N_PE = 8  -> the paper's group of 8 sharing one C and one A (default)
//   N_PE = 16 -> works too (more rows share the same C and A; fan-out grows)
// Only the number of rows changes.  The SWEEP length is always 8 cycles because
// the mantissa has 3 bits (8 possible spike positions), so latency (11 cycles)
// does NOT depend on N_PE.
//
// Idea (Fig. 5):  instead of multiplying, the accumulator A walks through
//        8w, 9w, 10w, ... 15w   (one new value per cycle, A <= A + w)
// while the counter C walks through 0,1,...,7.  Row i has the mantissa MD_i
// (3 bits).  The full mantissa is {1,MD_i} = 8+MD_i, so the wanted product
// (8+MD_i)*w is exactly the value of A on the cycle when C == MD_i.
// That cycle is the "spike" of row i; the PE grabs A at that moment.
//
// Accumulation forwarding: A does not start at 0 (the first 8 multiples would
// never be used because of the hidden 1).  It starts directly at 8*w, which
// is just a left shift by 3 - no adder needed.
//
// Timing (E0 = clock edge where start is accepted)
//   E0      : x and w captured, C=0, A=8w, busy=1
//   cycle k : C=k, A=(8+k)w, spike of every row whose MD==k  (k = 0..7)
//   E(k+1)  : PE registers mt_q/a_q capture spike and A
//   E(k+2)  : PE output register holds the product
//   E8      : last sweep cycle done, busy=0       (fin1 goes high)
//   E9      : last product stored in the PEs      (fin2 goes high)
//   E10     : post-processing registers latch -> done=1, results valid
//   ready returns to 1 after E10, so one batch of N_PE products takes 11 cycles.
//==============================================================================
`include "carat_tc.v"
`include "carat_pe.v"
`include "carat_po.v"
`include "carat_row.v"

module carat_column #(parameter N_PE = 8)(
    input  wire                clk,
    input  wire                rst_n,

    input  wire                start,       // request a new batch (used if ready=1)
    input  wire [N_PE*8-1:0]   x_flat,      // N_PE FP8 inputs, row i = x_flat[8*i +: 8]
    input  wire signed [7:0]   w,           // INT8 weight shared by all N_PE rows

    output wire                ready,       // 1 = a new start is accepted
    output reg                 done,        // 1-cycle pulse: results are valid
    output wire [N_PE*32-1:0]  prod_flat,   // N_PE Q20.12 products, row i = prod_flat[32*i +: 32]
    output wire [N_PE-1:0]     nan_flat,    // bit i = x[i] was NaN  (product forced to 0)
    output wire [N_PE-1:0]     zero_flat    // bit i = x[i] was +0/-0
);

    //--------------------------------------------------------------------------
    // Control: busy flag, shared counter C, end-of-batch delay chain
    //--------------------------------------------------------------------------
    reg        busy;                         // sweep in progress
    reg  [2:0] c;                            // shared counter 0..7
    reg        fin1, fin2;                   // delay chain after the last sweep cycle

    // logic [2:0] max_mantissa;                // maximum mantissa among all rows
    
    wire fire = start & ready;               // start accepted on this clock edge
    
    assign ready = ~busy & ~fin1 & ~fin2;

    //--------------------------------------------------------------------------
    // Calculate the maximum mantissa among all rows (used for normalization)
    //--------------------------------------------------------------------------
    function automatic [2:0] md_of(input [7:0] x);
    reg [2:0] m;
    begin
        m = x[2:0];
        if (x[6:3] != 4'd0) md_of = m;                 // normal: no adjustment
        else if (m[2])      md_of = {m[1:0], 1'b0};    // subnormal: drop leading 1, left-align
        else if (m[1])      md_of = {m[0], 2'b00};
        else                md_of = 3'd0;              // 001 or 000
    end
    endfunction

    reg [2:0] max_md, tmp;
    integer k;
    always @(*) begin
        tmp = 3'd0;
        for (k = 0; k < N_PE; k = k + 1)
            if (md_of(x_flat[8*k +: 8]) > tmp) tmp = md_of(x_flat[8*k +: 8]);
        end
    always @(posedge clk) if (fire) max_md <= tmp;         // latched at start
    wire last = busy & (c == max_md);

    always @(posedge clk) begin
        if (!rst_n) begin
            busy <= 1'b0;
            c    <= 3'd0;
            fin1 <= 1'b0;
            fin2 <= 1'b0;
            done <= 1'b0;
        end else begin
            // busy: set by a start, cleared after the last sweep cycle
            if (fire)      busy <= 1'b1;
            else if (last) busy <= 1'b0;

            // counter: restart at 0 on start, then count 0..7 (wraps by itself)
            if (fire)      c <= 3'd0;
            else if (busy) c <= c + 3'd1;

            // wait for the PE pipeline (2 cycles), then pulse done
            fin1 <= last;
            fin2 <= fin1;
            done <= fin2;
        end
    end

    //--------------------------------------------------------------------------
    // Shared accumulator A (Fig. 6d, top of the column)
    //   start : A <= 8*w          (accumulation forwarding: shift left by 3)
    //   busy  : A <= A + w        (next multiple of w every cycle)
    // 12 bits signed hold -15*128 = -1920 ... 15*127 = 1905.
    //--------------------------------------------------------------------------
    reg signed [7:0]  w_q;                   // weight kept for the whole sweep
    reg signed [11:0] a;                     // shared partial product

    always @(posedge clk) begin
        if (!rst_n) begin
            w_q <= 8'sd0;
            a   <= 12'sd0;
        end else if (fire) begin
            w_q <= w;
            a   <= {w[7], w, 3'b000};       // = 8*w  (sign bit + w + 3 zeros)
        end else if (busy) begin
            a   <= a + w_q;                  // sign extension is automatic (signed)
        end
    end

    //--------------------------------------------------------------------------
    // N_PE rows (generate loop).  All rows see the SAME c and a in the same cycle
    // (the paper shares C and A among groups of 8 rows).
    //--------------------------------------------------------------------------
    genvar i;
    generate
        for (i = 0; i < N_PE; i = i + 1) begin : g_row
            carat_row u_row (
                .clk(clk), .rst_n(rst_n),
                .load(fire),
                .x_in(x_flat[8*i +: 8]),
                .c(c), .a(a), .active(busy),
                .po_en(fin2),                // latch results once all PEs are final
                .result(prod_flat[32*i +: 32]),
                .nan_flag(nan_flat[i]),
                .zero_flag(zero_flat[i])
            );
            
            // if (i == 0) assign max_mantissa = x_flat[2:0];  // first row's mantissa
            // else        assign max_mantissa = (x_flat[8*i +: 3] > max_mantissa) ? x_flat[8*i +: 3] : max_mantissa;
        end
    endgenerate
endmodule
