// ===================================================================================
//  tb_compare.sv -- compares an 8-row baseline_column with an 8-row carat_column
//
//  * both DUTs get the same x_flat / w / start
//  * baseline result is valid right after the start edge, Carat after 4..11 cycles
//  * latency = clock edges from the start edge (E0) up to the edge where done=1
//              (max adjusted mantissa 0 -> 4 cycles, 7 -> 11 cycles)
//  * value mismatch  -> FAIL      latency different from the model (maxMD+4) -> WARN
// ===================================================================================
`timescale 1ns/1ps

module tb_compare;

    localparam int ROWS    = 8;         // number of rows (inputs) in the column
    localparam int LAT_TMO = 40;        // latency timeout for Carat

    logic                    clk = 1'b0, rst_n = 1'b0, start = 1'b0;
    logic signed [7:0]       w = 8'sd0;
    logic [ROWS*8-1:0]       x_flat = '0;

    wire                     b_done;
    wire [ROWS*32-1:0]       b_y;
    wire [ROWS-1:0]          b_nan;

    wire                     c_ready, c_done;
    wire [ROWS*32-1:0]       c_y;
    wire [ROWS-1:0]          c_nan, c_zero;

    baseline_column #(.ROWS(ROWS)) u_base (
        .clk(clk), .rst_n(rst_n), .start(start), .w(w), .x_flat(x_flat),
        .done(b_done), .y_flat(b_y), .nan_flat(b_nan));

    carat_column #(.N_PE(ROWS)) u_carat (
        .clk(clk), .rst_n(rst_n), .start(start), .x_flat(x_flat), .w(w),
        .ready(c_ready), .done(c_done), .prod_flat(c_y),
        .nan_flat(c_nan), .zero_flat(c_zero));

    always #5 clk = ~clk;                       // 100 MHz

    // ------------------------------------------------------------------
    //  bookkeeping
    // ------------------------------------------------------------------
    int n_batch = 0, n_fail = 0, n_warn = 0;
    int lat_hist [0:LAT_TMO];                   // histogram of latencies observed in all tests
    int lat_by_m [0:7];                         // latency observed in test 1

    // adjusted mantissa MD (paper Eq. 1): subnormal -> drop leading 1, left-align
    function automatic logic [2:0] md_of(input logic [7:0] x);
        logic [2:0] m;
        m = x[2:0];
        if (x[6:3] != 4'd0)  return m;
        else if (m[2])       return {m[1:0], 1'b0};
        else if (m[1])       return {m[0], 2'b00};
        else                 return 3'd0;
    endfunction

    function automatic int exp_latency(input logic [ROWS*8-1:0] xv);
        logic [2:0] mx = 3'd0;
        for (int i = 0; i < ROWS; i++)
            if (md_of(xv[8*i +: 8]) > mx) mx = md_of(xv[8*i +: 8]); // max adjusted mantissa
        return int'(mx) + 4;
    endfunction

    // ------------------------------------------------------------------
    //  apply one batch to both designs and compare
    // ------------------------------------------------------------------
    task automatic run_batch(input logic [ROWS*8-1:0] xv,
                             input logic signed [7:0] wv,
                             input string             tag,
                             input bit                show,
                             output int               lat_out);
        int  lat, elat;
        bit  ok, b_done_seen;
        logic [ROWS*32-1:0] y_b;
        logic [ROWS-1:0]    nan_b;

        @(negedge clk);
        while (!c_ready) @(negedge clk);
        x_flat = xv;  w = wv;  start = 1'b1;
        @(posedge clk); #1;                     // E0: both DUTs accept start
        start = 1'b0;
        lat = 1;
        b_done_seen = b_done;                   // baseline: done right after E0
        y_b   = b_y;
        nan_b = b_nan;

        while (!c_done && lat < LAT_TMO) begin  // x_flat / w stay stable meanwhile
            @(posedge clk); #1;
            lat++;
        end

        n_batch++;
        lat_out = lat;
        lat_hist[lat]++;
        elat = exp_latency(xv);

        ok = c_done && b_done_seen && (c_y === y_b) && (c_nan === nan_b);
        if (!ok) begin
            n_fail++;
            $display("FAIL %-12s w=%0d x=%h  carat_done=%0b lat=%0d base_done=%0b", tag, wv, xv, c_done, lat, b_done_seen);
            for (int i = 0; i < ROWS; i++)
                if (c_y[32*i +: 32] !== y_b[32*i +: 32] || c_nan[i] !== nan_b[i])
                    $display("     row %0d x=0x%02h : carat y=%0d nan=%0b | baseline y=%0d nan=%0b",
                             i, xv[8*i +: 8], $signed(c_y[32*i +: 32]), c_nan[i],
                             $signed(y_b[32*i +: 32]), nan_b[i]);
        end
        if (c_done && lat != elat) begin
            n_warn++;
            $display("WARN %-12s x=%h  latency %0d, model expects %0d", tag, xv, lat, elat);
        end
        if (show && ok)
            $display("PASS %-12s w=%4d  x=%h  latency=%2d (model %2d)", tag, wv, xv, lat, elat);
    endtask

    // ------------------------------------------------------------------
    //  vector builders
    // ------------------------------------------------------------------
    function automatic logic [ROWS*8-1:0] fill_all(input logic [7:0] code);
        logic [ROWS*8-1:0] v;
        for (int i = 0; i < ROWS; i++) v[8*i +: 8] = code;
        return v;
    endfunction

    // ------------------------------------------------------------------
    //  main
    // ------------------------------------------------------------------
    logic [ROWS*8-1:0] xv;
    int   dummy;
    logic signed [7:0] wlist [6] = '{-8'sd128, -8'sd1, 8'sd0, 8'sd1, 8'sd127, 8'sd93};
    logic [7:0] specials [10]    = '{8'h00, 8'h80, 8'h7F, 8'hFF, 8'h7E, 8'hFE, 8'h01, 8'h81, 8'h07, 8'h08};

    initial begin
        for (int i = 0; i <= LAT_TMO; i++) lat_hist[i] = 0;

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        // ---- 1. uniform mantissa 0..7 on every row (normal numbers) --------
        $display("\n--- Test 1: mantissa 0..7 on all rows (normal) ---");
        for (int m = 0; m < 8; m++) begin
            for (int i = 0; i < ROWS; i++)
                xv[8*i +: 8] = {i[0], 4'(1 + i), 3'(m)};
            run_batch(xv, 8'sd93, $sformatf("uniform m=%0d", m), 1, lat_by_m[m]);
        end

        // ---- 2. a single row carries mantissa m, others 0 -------------------
        $display("\n--- Test 2: one row has mantissa m, all others 0 (checks max over every row position) ---");
        for (int m = 0; m < 8; m++)
            for (int r = 0; r < ROWS; r++) begin
                xv = fill_all({1'b0, 4'd7, 3'd0});
                xv[8*r +: 8] = {1'b0, 4'd7, 3'(m)};
                run_batch(xv, -8'sd101, $sformatf("onehot m=%0d r=%0d", m, r), 0, dummy);
            end

        // ---- 3. special values --------------------------------------------------
        $display("\n--- Test 4: zero / NaN / extremes ---");
        for (int s = 0; s < 10; s++) begin
            run_batch(fill_all(specials[s]), 8'sd127, $sformatf("special %02h", specials[s]), 1, dummy);
            xv = fill_all(8'h00);  xv[8*3 +: 8] = specials[s];       // one special among zeros
            run_batch(xv, -8'sd128, $sformatf("special1 %02h", specials[s]), 0, dummy);
        end

        // ---- report ---------------------------------------------------------------
        $display("\n================ latency vs mantissa (test 1) ================");
        for (int m = 0; m < 8; m++)
            $display("  max mantissa %0d -> latency %0d cycles", m, lat_by_m[m]);
        $display("\n================ latency histogram (all batches) =============");
        for (int l = 0; l <= LAT_TMO; l++)
            if (lat_hist[l] != 0) $display("  %2d cycles : %0d batches", l, lat_hist[l]);
        $display("\nbatches: %0d   value failures: %0d   latency warnings: %0d", n_batch, n_fail, n_warn);
        $display(n_fail == 0 ? "RESULT: PASS" : "RESULT: FAIL");
        $finish;
    end

endmodule
