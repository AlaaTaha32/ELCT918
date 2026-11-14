// ============================================================================
//  tb_baseline.sv  --  file-driven, self-checking testbench for baseline_column
//
//  Flow
//    1. python3 ref_model.py            -> vectors.txt  (inputs + EXPECTED outputs,
//                                          computed in Python with exact arithmetic)
//    2. this testbench reads vectors.txt, applies one (x, w) pair per start pulse,
//       compares the DUT output with the expected value, prints a line per vector
//       and writes the raw DUT results to sim_results.txt
//    3. python3 compare.py              -> independent Python-side report per category
//
//  The DUT is instantiated with ROWS = 1: every row of the 8-row baseline contains
//  the same multiplier logic, so one row tests it fully, and each vector can use its
//  own weight (all rows in a column share one w).
//
//  Plusargs:   +VEC=<file>   vector file   (default vectors.txt)
//              +RES=<file>   results file  (default sim_results.txt)
//              +QUIET        print only failures and the summary
// ============================================================================
`timescale 1ns/1ps

module tb_baseline;

    // ------------------------------------------------------------------
    //  DUT hookup
    // ------------------------------------------------------------------
    logic              clk   = 1'b0;
    logic              rst_n = 1'b0;
    logic              start = 1'b0;
    logic signed [7:0] w     = 8'sd0;
    logic [7:0]        x     = 8'd0;

    wire               done;
    wire [31:0]        y;
    wire [0:0]         nan_f;

    baseline_column #(.ROWS(1)) dut (
        .clk      (clk),
        .rst_n    (rst_n),
        .start    (start),
        .w        (w),
        .x_flat   (x),
        .done     (done),
        .y_flat   (y),
        .nan_flat (nan_f)
    );

    always #5 clk = ~clk;                 // 100 MHz, same as the Nexys 4 DDR clock

    // ------------------------------------------------------------------
    //  Test bookkeeping
    // ------------------------------------------------------------------
    string  vec_file = "vectors.txt";
    string  res_file = "sim_results.txt";
    bit     verbose;                      // print all vectors, not just failures

    integer latency;                      // latency of the DUT, measured in clock cycles
    integer fd;                           // file descriptor for input vector file
    integer fr;                           // file descriptor for output results file
    integer rd;                           // return value from $fscanf (number of items read per line)
    integer n_vec = 0, n_fail = 0;        // number of vectors read, number of failures

    logic [7:0]  vx, vw;                  // input vector values (FP8 x, INT8 w)
    logic [31:0] vy;                      // expected Q20.12 (two's complement)
    logic [3:0]  vn;                      // expected NaN flag (one hex digit)
    reg   [8*16-1:0] label;               // category name from the vector file

    logic [31:0] got_y;                   // DUT output, Q20.12
    logic        got_nan, got_done;       // DUT output flags
    bit          ok;                      // true if the DUT output matches the expected value
    real         got_real, exp_real;      // DUT and expected values converted to real for printing

    // ------------------------------------------------------------------
    //  Main sequence
    // ------------------------------------------------------------------
    initial begin
        void'($value$plusargs("VEC=%s", vec_file));
        void'($value$plusargs("RES=%s", res_file));
        verbose = !$test$plusargs("QUIET");

        fd = $fopen(vec_file, "r");
        if (fd == 0) begin
            $display("FATAL: cannot open vector file '%s' (run ref_model.py first)", vec_file);
            $finish;
        end
        fr = $fopen(res_file, "w");

        // reset
        repeat (3) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        if (verbose)
            $display("%-10s  x      w | got y (hex)    got y (dec) = real      | exp y (hex)  nan | result",
                     "label");

        while (!$feof(fd)) begin
            rd = $fscanf(fd, "%h %h %h %h %s\n", vx, vw, vy, vn, label);
            if (rd == 5) begin
                // ---- apply one vector -----------------------------------
                @(negedge clk);
                x     = vx;
                w     = vw;
                start = 1'b1;
                @(posedge clk);           // DUT registers inputs and result on this edge
                #1;
                start    = 1'b0;
                got_y    = y;             // outputs are valid right after the edge
                got_nan  = nan_f;
                got_done = done;

                // ---- compare --------------------------------------------
                ok = (got_done === 1'b1) && (got_y === vy) && (got_nan === vn[0]);
                n_vec++;
                if (!ok) n_fail++;

                got_real = $itor($signed(got_y)) / 4096.0;
                exp_real = $itor($signed(vy))    / 4096.0;

                if (verbose || !ok)
                    $display("%-10s 0x%02h %4d | %08h  %12d = %-12g  | %08h      %0b  | %s",
                             label, vx, $signed(vw), got_y, $signed(got_y), got_real,
                             vy, vn[0], ok ? "PASS" : "FAIL");
                if (!ok)
                    $display("           ^^^ expected %0d (= %g), nan=%0b ; got done=%0b nan=%0b",
                             $signed(vy), exp_real, vn[0], got_done, got_nan);

                // raw DUT result, same field order as vectors.txt (without the label)
                $fdisplay(fr, "%02h %02h %08h %h", vx, vw, got_y, got_nan);
            end
        end

        $fclose(fd);
        $fclose(fr);

        $display("--------------------------------------------------------------------------------------------------------------");
        $display("vectors: %0d   failures: %0d", n_vec, n_fail);
        if (n_vec == 0)        $display("RESULT: FAIL (no vectors were read)");
        else if (n_fail == 0)  $display("RESULT: PASS");
        else                   $display("RESULT: FAIL");
        $finish;
    end

endmodule
