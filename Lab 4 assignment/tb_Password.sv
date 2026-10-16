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
  10- Generating all 65536 four-nibble windows (de Bruijn sequence) to find the password
  11- Back-to-back and overlapping words, interrupted words, and reset right after a word
*/
`timescale 1ns/1ps
module tb;

  // Signals for the testbench
  localparam int NW = 18;            // number of candidate "famous" words

  reg clk = 0, rst_n = 0, en = 0;
  reg [3:0] din = 0;
  wire [7:0] dout_solution, dout_mystery;
  wire flag_solution, flag_mystery;

  int match = 0, mismatch = 0;    // Counter for the number of cycles where the two designs' outputs match or mismatch
  int cycle = 0;                  // Counter for the number of cycles elapsed thoughout the simulation
  int flag_hits = 0;              // Counter for the number of cycles where the mystery design's flag is high
  reg show = 1;                   // Simulation control: 1 - print every step, 0 - print only mismatches
  reg [3:0] d_cur = 0;            // Current din of the random phases

  int n_en = 0;                   // enabled cycles since the last reset (tracks the key phase)
  reg log_flag = 0;               // Simulation control: 1 - print every cycle the reference flag is high
  reg warned   = 0;               // 1: cipher model warning has been printed (only print it once), indicating that the cipher model is off (the mystery design is not behaving as expected)
  reg [15:0] last4 = 0;           // last 4 ciphertext nibbles seen on mystery's dout
  reg [15:0] WORDS [NW];          // candidate words (a guess; Experiment 4 finds the real ones)

  // 1 whenever the two designs disagree (handy in the wave window)
  wire differ = (dout_mystery !== dout_solution) || (flag_mystery !== flag_solution);
  //------------------------------------------------------------------------------------------------------------------------------------

  // Instantiating the two designs under test and clock generation
  mystery  bb2 (.clk(clk), .rst_n(rst_n), .en(en), .din(din), .dout(dout_mystery),  .flag(flag_mystery));
  solution bb  (.clk(clk), .rst_n(rst_n), .en(en), .din(din), .dout(dout_solution), .flag(flag_solution));

  always #5 clk = ~clk;
  //------------------------------------------------------------------------------------------------------------------------------------

  // Taskes and functions for genearating random inputs and applying them to the designs, as well as printing the outputs
  
  // Random number in [0, n-1]
  function int rnd(input int n);
    return {$random} % n;
  endfunction

  // Applies one input set at the negedge, then look at the outputs after the posedge
  task step_r(input r, input e, input [3:0] d);
    begin
      @(negedge clk); rst_n = r; en = e; din = d;
      if (!r) n_en = 0; else if (e) n_en++;
      @(posedge clk); #1;
      if (show)
        $display("%t | %b   %b  %h   | %02h       %b        | %02h       %b",
                 $time, r, e, d, dout_mystery, flag_mystery, dout_solution, flag_solution);
    end
  endtask

  // Normal step (reset released)
  task step(input e, input [3:0] d);
    step_r(1'b1, e, d);
  endtask

  // n cycles of reset; en and din are random so reset priority is tested too
  task do_reset(input int n);
    repeat (n) step_r(1'b0, rnd(2), rnd(16));
  endtask

  // Send one ciphertext nibble c: din is chosen so the chip outputs c.
  // Model from the observed data: low nibble = din + K, K = 6,7,4,5 = (6 ^ phase),
  // phase = enabled cycles since reset, mod 4.
  task send_nib(input [3:0] c);
    begin
      step(1, c - (4'd6 ^ n_en[1:0]));
      if (dout_mystery[3:0] !== c && !warned) begin
        warned = 1;
        $display("WARNING: cipher model is off at cycle %0d (wanted low nibble %h, chip gave %h)",
                 cycle, c, dout_mystery[3:0]);
      end
    end
  endtask

  // Send a 4-nibble word as 4 consecutive ciphertext nibbles, oldest is the most significant nibble.
  task send_word(input [15:0] w);
    begin
      send_nib(w[15:12]); send_nib(w[11:8]); send_nib(w[7:4]); send_nib(w[3:0]);
    end
  endtask

  // Sending each window separately would need 4 × 65,536 = 262,144 nibbles if done naively. 
  // Instead, we use a de Bruijn sequence to generate all 65,536 windows with only 65,539 nibbles (the first three nibbles are just leading zeros).
  // Every possible 4-nibble window exactly once (de Bruijn sequence, 65536 + 3 nibbles).
  // With log_flag = 1 the checker prints each cycle the reference flag is high.
  task sweep_all_words;
    bit seen [65536];       // For every possible 4-nibble window, 1 if it has been sent already, 0 if not
    logic [15:0] w, cand;   // Current window, candidate next window
    int found;              // Records if a candidate next window has been found (1) or not (0)
    begin
      for (int i = 0; i < 65536; i++) seen[i] = 0; 
      w = 16'h0000;
      do_reset(1);
      repeat (3) send_nib(4'h0);                    // the three leading zeros
      for (int i = 0; i < 65536; i++) begin
        found = 0;
        for (int s = 15; s >= 0 && !found; s--) begin // finding the next candidate window: trying all 16 possible next nibble's value
          cand = {w[11:0], s[3:0]};
          if (!seen[cand]) begin  // if this candidate next window has not been sent yet, send it
            seen[cand] = 1; found = 1;
            send_nib(s[3:0]);
            w = cand;
          end
        end
        if (!found) begin
          $display("WARNING: sweep ended early at window %0d", i);
          i = 65536;
        end
      end
    end
  endtask

  // Random phase: p_en = en probability in %, p_rst = reset probability in %,
  // din changes with probability 1/hold each cycle (hold = 1: new din every cycle)
  task random_phase(input int n, input int p_en, input int p_rst, input int hold);
    repeat (n) begin
      if (rnd(hold) == 0) d_cur = rnd(16);
      step_r(!(rnd(100) < p_rst), rnd(100) < p_en, d_cur);
    end
  endtask

  // Title for the next experiment, and print the header for the following steps if show = 1
  task title(input string name);
    begin
      $display("\n--- %s ---", name);
      if (show) $display("  time  | rst en din | dout_mys flag_mys | dout_sol flag_sol");
    end
  endtask
  //------------------------------------------------------------------------------------------------------------------------------------

  // The main simulation block
  initial begin
    $timeformat(-9, 0, " ns", 7);   // units 1ns, 0 decimals, suffix, min width
    $dumpfile("dump.vcd"); $dumpvars(0, tb);

    WORDS = '{16'hDEAD, 16'hBEEF, 16'hCAFE, 16'hBABE, 16'hFACE, 16'hFADE,
              16'hFEED, 16'hF00D, 16'hC0DE, 16'hDEAF, 16'hACED, 16'hDEED,
              16'hBAAD, 16'hB00B, 16'hD00D, 16'hFA11, 16'h5EED, 16'hABBA};

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

    // From here on only mismatches are printed (set show = 1 to look at a section)
    show = 0;

    // Experiment 4: exhaustive discovery of the flag words
    title("Experiment 4: all 65536 four-nibble windows (reference flag hits are printed)");
    log_flag = 1;
    sweep_all_words;
    log_flag = 0;

    // Experiment 5: each word at all 4 key phases, plus a one-bit near miss
    title("Experiment 5: candidate words at every key phase, plus a near miss");
    for (int k = 0; k < NW; k++) begin
      for (int p = 0; p < 4; p++) begin
        do_reset(1);
        repeat (p) step(1, rnd(16));          // shift the key phase
        send_word(WORDS[k]);
        repeat (3) step(1, rnd(16));          // keep going: does flag drop?
        repeat (3) step(0, rnd(16));          // idle: does flag hold?
      end
      do_reset(1);
      send_word(WORDS[k] ^ (16'h1 << (4 * (k % 4))));   // one bit wrong
    end

    // Experiment 6: back-to-back and overlapping words
    title("Experiment 6: back-to-back and overlapping words");
    do_reset(1); send_word(16'hDEAD); send_word(16'hDEAD);                              // DEAD DEAD
    do_reset(1); send_word(16'hDEAD); send_word(16'hBEEF);                              // DEADBEEF
    do_reset(1); send_word(16'hCAFE); send_word(16'hBABE);                              // CAFEBABE
    do_reset(1); send_word(16'hFEED); send_word(16'hFACE);                              // FEEDFACE
    do_reset(1); send_word(16'hBEEF); send_nib(4'hE); send_nib(4'hE); send_nib(4'hD);   // BEEF then FEED
    do_reset(1); send_word(16'hFACE); send_nib(4'hD);                                   // FACE then ACED
    do_reset(1); send_word(16'hDEAD); send_nib(4'hE); send_nib(4'hA); send_nib(4'hF);   // DEAD then DEAF
    repeat (100) begin                                                                  // random word pairs
      do_reset(1);
      send_word(WORDS[rnd(NW)]);
      send_word(WORDS[rnd(NW)]);
    end

    // Experiment 7: words interrupted by idle or reset, and reset right after a word
    title("Experiment 7: interrupted words");
    for (int k = 0; k < NW; k++) begin
      do_reset(1);                                       // idle gap: does idle shift the history?
      send_nib(WORDS[k][15:12]); send_nib(WORDS[k][11:8]);
      repeat (5) step(0, rnd(16));
      send_nib(WORDS[k][7:4]);   send_nib(WORDS[k][3:0]);

      do_reset(1);                                       // reset in the middle: is history cleared?
      send_nib(WORDS[k][15:12]); send_nib(WORDS[k][11:8]);
      do_reset(1);
      send_nib(WORDS[k][7:4]);   send_nib(WORDS[k][3:0]);

      do_reset(1);                                       // reset right after the word: does flag clear?
      send_word(WORDS[k]);
      do_reset(2);
    end

    // Experiment 8: long uninterrupted runs
    title("Experiment 8: long runs (300 x same din, then 1100 x random din)");
    do_reset(2);
    repeat (300)  step(1, 4'h7);
    repeat (1100) step(1, rnd(16));

    // Experiment 9: din ramps, en toggling, repeat-then-change, idle
    title("Experiment 9: ramps, en toggling, repeat-then-change");
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
    do_reset(1);                                                     // idle with din wiggling
    repeat (9)  step(1, 4'h3);
    repeat (40) step(0, rnd(16));
    repeat (9)  step(1, 4'h3);

    // Experiment 10: random phases, with candidate words injected at random moments
    title("Experiment 10: random phases");
    //             cycles  en%  rst%       din changes every ~N cycles
    random_phase(  10000,  50,    0,             1);
    random_phase(   5000,  90,    0,             1);
    random_phase(   5000,  10,    0,             1);
    random_phase(   5000,  70,    0,            30);   // sticky din: long runs of one value
    random_phase(  10000,  70,    2,             1);   // random resets (about 2% of cycles)
    random_phase(   5000, 100,    0.5,           8);   // always enabled, rare resets: long runs
    repeat (500) begin                                 // random noise, then a word at a random key phase
      random_phase(rnd(30), 70, 1, 1);
      send_word(WORDS[rnd(NW)]);
    end

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

  // Compare after every rising edge
  always @(posedge clk) begin
    #1;
    cycle++;

    // Monitor: last 4 ciphertext nibbles (low nibble of dout on each enabled cycle)
    if (!rst_n)  last4 = 16'h0000;
    else if (en) last4 = {last4[11:0], dout_mystery[3:0]};

    if (flag_mystery === 1'b1) begin
      flag_hits++;
      if (log_flag) $display("reference flag high at cycle %0d: last 4 ciphertext nibbles = %h", cycle, last4);
    end

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
