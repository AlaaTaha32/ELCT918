/*
Included testcases:
  1- Priority of reset over enable and din
  2- Behavior when enable is low
  3- Behavior when enable is high and din is the same for several cycles
  4- Behavior when enable is high and din is the same for several cycles, then enable is low for several cycles, then enable is high again
  5- Behavior with every din value, with reset in between
  6- Behavior with long uninterrupted long runs of same and random din values
  7- Behavior with din ramps (ascending and descending)
  8- Enable toggling every cycle
  9- Long runs of random phases (probablities of enable, reset, and din changing)
*/

`timescale 1ns/1ps
module tb;

  // Signals for the testbench
  reg clk = 0, rst_n = 0, en = 0;
  reg [3:0] din = 0;
  wire [7:0] dout_solution, dout_mystery;
  wire flag_solution, flag_mystery;

  int match = 0, mismatch = 0;    // Counter for the number of cycles where the two designs' outputs match or mismatch
  int cycle = 0;                  // Counter for the number of cycles elapsed thoughout the simulation
  int flag_hits = 0;              // Counter for the number of cycles where the mystery design's flag is high
  reg show = 1;                   // Simulation control: 1 - print every step, 0 - print only mismatches
  reg [3:0] d_cur = 0;            // Current din of the random phases

  // A signal that is asserted whenever the two designs' outputs are different
  wire differ = (dout_mystery !== dout_solution) || (flag_mystery !== flag_solution);
  //-----------------------------------------------------------------------------------------------------------------------------------

  // Instantiating the two designs under test and clock generation
  mystery  bb2 (.clk(clk), .rst_n(rst_n), .en(en), .din(din), .dout(dout_mystery),  .flag(flag_mystery));
  solution bb  (.clk(clk), .rst_n(rst_n), .en(en), .din(din), .dout(dout_solution), .flag(flag_solution));

  always #5 clk = ~clk;
  //-----------------------------------------------------------------------------------------------------------------------------------

  // Taskes and functions for genearating random inputs and applying them to the designs, as well as printing the outputs

  // Returns a random number in [0, n-1]
  function int rnd(input int n);
    return {$random} % n;
  endfunction

  // Applies one input set at the negedge, then look at the outputs after the posedge
  task step_r(input r, input e, input [3:0] d);
    begin
      @(negedge clk); rst_n = r; en = e; din = d;
      @(posedge clk); #1;
      if (show)
        $display("%t | %b   %b  %h   | %02h       %b        | %02h       %b",
                 $time, r, e, d, dout_mystery, flag_mystery, dout_solution, flag_solution);
    end
  endtask

  // Normal step (reset deasserted) with en and din as inputs
  task step(input e, input [3:0] d);
    step_r(1'b1, e, d);
  endtask

  // n cycles of reset; en and din are random so reset priority is tested too
  task do_reset(input int n);
    repeat (n) step_r(1'b0, rnd(2), rnd(16));
  endtask

  // Random phase: p_en = en probability in %, p_rst = reset probability in %,
  // din changes with probability 1/hold each cycle (hold = 1: new din every cycle)
  task random_phase(input int n, input int p_en, input int p_rst, input int hold);
    repeat (n) begin
      if (rnd(hold) == 0) d_cur = rnd(16);  // For a higher hold value, the same din is repeated (not randomized) for more cycles, so the design is tested with longer runs of the same din
      step_r(!(rnd(100) < p_rst), rnd(100) < p_en, d_cur);
    end
  endtask


  // Title for the next experiment, and print the header for the following steps
  task title(input string name);
    begin
      $display("\n--- %s ---", name);
      if (show) $display("  time  | rst en din | dout_mys flag_mys | dout_sol flag_sol");
    end
  endtask

  //-----------------------------------------------------------------------------------------------------------------------------------

  // The main simulation block

  initial begin
    $timeformat(-9, 0, " ns", 7);   // units 1ns, 0 decimals, suffix, min width
    $dumpfile("dump.vcd"); $dumpvars(0, tb);

    title("Reset");
    do_reset(3);

    // Experiment 1: what happens when en is low
    title("Experiment 1: en low");
    step(0, 4'h5); step(0, 4'h9);

    // Experiment 2: same value, then idle with din changing, then resume
    title("Experiment 2: din = 0, idle with din changing, resume");
    repeat (10) step(1, 4'h0);
    repeat (5)  step(0, 4'h0);
    repeat (4)  step(0, 4'h1);
    repeat (10) step(1, 4'h0);

    // Experiment 3: every din value, reset in between
    title("Experiment 3: every din value, 20 enabled cycles each");
    for (int v = 0; v < 16; v++) begin
      do_reset(2);
      repeat (20) step(1, v);
    end

    // From here on only mismatches are printed
    show = 0;

    // Experiment 4: long uninterrupted runs
    title("Experiment 4: long runs (300 x same din, then 1100 x random din)");
    do_reset(2);
    repeat (300)  step(1, 4'h7);
    repeat (1100) step(1, rnd(16));

    // Experiment 5: din ramps, en toggling, repeat-then-change
    title("Experiment 5: ramps, en toggling, repeat-then-change");
    do_reset(1);
    for (int v = 0;  v < 16;  v++) step(1, v);                       // ascending
    for (int v = 15; v >= 0;  v--) step(1, v);                       // descending
    for (int v = 0;  v < 100; v++) step(v % 2, 4'hA);                // en toggles every cycle
    for (int n = 2; n <= 20; n++) begin                              // same din n times, change, again
      do_reset(1);
      repeat (n) step(1, 4'h3);
      step(1, 4'h4);
      repeat (n) step(1, 4'h3);
    end

    // Experiment 6: idle after activity
    title("Experiment 6: idle with din changing after activity");
    do_reset(1);
    repeat (9)  step(1, 4'h3);
    repeat (40) step(0, rnd(16));
    repeat (9)  step(1, 4'h3);

    // Experiment 7: random phases
    title("Experiment 7: random phases");
    //             cycles  en%  rst%        din changes every ~N cycles
    random_phase(  10000,  50,    0,             1);
    random_phase(   5000,  90,    0,             1);
    random_phase(   5000,  10,    0,             1);
    random_phase(   5000,  70,    0,            30);   // sticky din: long runs of one value
    random_phase(  10000,  70,    2,             1);   // random resets (2% of cycles)
    random_phase(   5000, 100,    0.5,           8);   // always enabled, rare resets: long runs
    #2;
    // Display the final results
    $display("\n\n----------------------- Final Results -----------------------");
    $display("%0d cycles checked: %0d matches, %0d mismatches", cycle, match, mismatch);
    $display("mystery flag was high in %0d cycles", flag_hits);
    if (mismatch == 0) $display("PASS");
    else               $display("FAIL");
    $display("-------------------------------------------------------------\n\n");
    $finish;
  end
  //------------------------------------------------------------------------------------------------------------------------------------

  // Compare after every rising edge, prints a mismatch message for the first 10 mismatches, then only counts the remaining mismatches
  always @(posedge clk) begin
    #1;
    cycle++;
    if (flag_mystery === 1'b1) flag_hits++;
    if (dout_mystery !== dout_solution || flag_mystery !== flag_solution) begin
      mismatch++;
      if (mismatch <= 10)
        $display("Mismatch at cycle %0d, time %t: dout_mystery = %02h, flag_mystery = %b, dout_solution = %02h, flag_solution = %b",
                 cycle, $time, dout_mystery, flag_mystery, dout_solution, flag_solution);
      else if (mismatch == 11)
        $display("(further mismatches are counted but not printed)");
    end else begin
      match++;
    end
  end
endmodule
