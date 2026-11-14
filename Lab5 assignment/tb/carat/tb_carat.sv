//===============================================================================================
// tb_carat_column.v  --  Self-checking testbench for carat_column (parameterized)
//------------------------------------------------------------------------------
// N_PE : number of rows of the column under test (inputs = rows = products).
//        N_PE = 1 tests a single PE row, N_PE = 8 the paper's column, etc.
//        Change it here, or from the command line without editing the file:
//            iverilog -P tb_carat_column.N_PE=1 ...        (Icarus)
//            xelab -generic_top N_PE=1 ...                 (Vivado)
//===============================================================================================
`timescale 1ns/1ps

module tb_carat #(parameter N_PE = 1);

    // ------------------------------------------------------------------
    //  DUT hookup
    // ------------------------------------------------------------------
    logic              clk   = 1'b0;
    logic              rst_n = 1'b0;
    logic              start = 1'b0;
    logic signed [7:0] w     = 8'sd0;
    logic [N_PE*8-1:0] x     = 8'd0;

    wire               done;
    wire              ready;
    wire [N_PE*32-1:0]    y;
    wire [N_PE-1:0]   nan_f;
    wire [N_PE-1:0]   zero_f;

     carat_column #(.N_PE(N_PE)) dut (
        .clk      (clk),
        .rst_n    (rst_n),
        .start    (start),
        .w        (w),
        .x_flat   (x),
        .ready    (ready),
        .done     (done),
        .prod_flat   (y),
        .nan_flat (nan_f),
        .zero_flat (zero_f)
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

    logic [7:0]  vx;                      // input vector values (FP8 x)   
    logic [7:0]  vw;                      // weight values (INT8 w)
    logic [31:0] vy;                      // expected Q20.12 (two's complement)
    logic [3:0]  vn;                      // expected NaN flag (one hex digit)
    reg   [8*16-1:0] label;               // category name from the vector file

    logic [31:0] got_y;                   // DUT output, Q20.12
    logic        got_nan, got_done;       // DUT output flags
    bit          ok;                      // true if the DUT output matches the expected value
    real         got_real, exp_real;      // DUT and expected values converted to real for printing

    
    //--------------------------------------------------------------------------
    // Map an 8-byte pattern onto N_PE rows: row i gets byte (i mod 8)
    //--------------------------------------------------------------------------
    function [N_PE*8-1:0] map_rows(input [63:0] p);
        integer i;
        begin
            for (i = 0; i < N_PE; i = i + 1)
                map_rows[8*i +: 8] = p[8*(i % 8) +: 8];
        end
    endfunction

    
    
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
            $display("%-10s  x      w | got y (hex)    got y (dec) = real      | exp y (hex)  nan | result | latency",
                     "label");

        while (!$feof(fd)) begin
            rd = $fscanf(fd, "%h %h %h %h %s\n", vx, vw, vy, vn, label);
            if (rd == 5) begin
                // wait until the column can accept a new batch
                 while (!ready) @(negedge clk);
                // ---- apply one vector -----------------------------------
                // @(negedge clk);
                x     = vx;
                w     = vw;
                start = 1'b1;
                @(negedge clk);           // DUT registers inputs and result on this edge
                #1;
                start    = 1'b0;

                // wait for done and measure latency (in clock cycles)
                latency = 1;
                while (!done) begin
                    @(negedge clk);
                    latency = latency + 1;
                    if (latency > 40) begin
                        $display("[FAIL] timeout waiting for done");
                        // errors = errors + 1;
                        $finish;
                    end
                end

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
                    $display("%-10s 0x%02h %4d | %08h  %12d = %-12g  | %08h      %0b  | %s   | %0d cycles",
                             label, vx, $signed(vw), got_y, $signed(got_y), got_real,
                             vy, vn[0], ok ? "PASS" : "FAIL", latency);
                if (!ok) begin
                    $display("           ^^^ expected %0d (= %g), nan=%0b ; got %0d (= %g), nan=%0b",
                             $signed(vy), exp_real, vn[0], $signed(got_y), got_real, got_nan);

                    //$display("busy = %0b, fire = %0b, last = %0b, c = %0d, max_mantissa = %0d",
                      //       dut.busy, dut.fire, dut.last, dut.c, dut.max_mantissa);
                end
                // raw DUT result, same field order as vectors.txt (without the label)
                $fdisplay(fr, "%02h %02h %08h %h %0d cycles_latency", vx, vw, got_y, got_nan, latency);
            end
            @(negedge clk);                    // let 'done' drop before next batch
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
