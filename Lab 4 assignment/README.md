# Crack the Cipher Chip: Black-Box Reverse Engineering in Verilog

ELCT918, Selected Topics in AI Accelerators Hardware Design.

A small encryption chip was intercepted. Only its synthesized gate-level netlist (`mystery.v`) is available, so its behavior was found by simulation. This repository contains the clean RTL re-implementation (`solution.v`), two self-checking testbenches that compare it with the chip cycle by cycle, and the password that makes the chip raise its `flag`.

## Repository contents

| File | Description |
|---|---|
| `mystery.v` | The intercepted gate-level netlist, unchanged |
| `solution.v` | Readable RTL re-implementation of the chip (module `solution`, same ports as `mystery`) |
| `tb.sv` | Simple self-checking testbench, tests 1-9 |
| `tb_Password.sv` | Full testbench: tests 1-9, plus the password search (test 10) and the word experiments (test 11) |
| `run_compare.do` | ModelSim / Questa script: compile, simulate, show waveforms |

## The chip in short

| Port | Dir | Width | Description |
|---|---|---|---|
| `clk` | in | 1 | Rising-edge clock |
| `rst_n` | in | 1 | Synchronous, active-low reset. Starts a new message |
| `en` | in | 1 | When high, the nibble on `din` is encrypted at the clock edge |
| `din` | in | 4 | Plaintext nibble |
| `dout` | out | 8 | `{cycle counter, ciphertext nibble}` |
| `flag` | out | 1 | High when the last four ciphertext nibbles spell the secret word |

The cipher found in the experiments:

```
key    = 6 ^ phase            // phase = enabled cycles since reset, mod 4 -> key 6, 7, 4, 5
cipher = (din + key) mod 16   // 4-bit addition
dout   = {counter, cipher}    // counter = enabled cycles since reset, 4 bits
```

On each rising clock edge: if `rst_n` is low, everything is cleared; otherwise, if `en` is high, the counter, the key phase and the history of the last four ciphertext nibbles advance, and `flag` is set when those four nibbles equal the secret word; otherwise nothing changes.

## How to run

**ModelSim / Questa**

```
do run_compare.do
```

Edit `TOP` at the top of the script to choose the testbench: `tb` (simple) or `tb_Password` (full).

**Icarus Verilog**

```
iverilog -g2012 -o sim mystery.v solution.v tb.sv
vvp sim
```

Use `tb_Password.sv` instead of `tb.sv` for the full testbench.

**EDA Playground**

- `design.sv`: the contents of `mystery.v` (unchanged) followed by `solution.v`.
- `testbench.sv`: the contents of `tb_Password.sv`.
- Simulator: Icarus Verilog 12.0.

## Testbenches

Both testbenches instantiate `mystery` and `solution` side by side and drive them with the same inputs. Inputs change at the falling clock edge, and `dout` and `flag` of both designs are compared 1 ns after every rising edge. Mismatches are counted, the first ten are printed with their cycle number, and the run ends with `PASS` or `FAIL`.

### `tb.sv` (simple testbench)

| # | Test |
|---|---|
| 1 | Priority of reset over enable and din |
| 2 | Behavior when enable is low |
| 3 | Enable high and din the same for several cycles |
| 4 | Enable high and din the same for several cycles, then enable low for several cycles, then enable high again |
| 5 | Every din value, with a reset in between |
| 6 | Long uninterrupted runs of the same din and of random din values |
| 7 | din ramps (ascending and descending) |
| 8 | Enable toggling every cycle |
| 9 | Long runs of random phases (probabilities of enable, reset and din changing) |

Test 9 alone is 40,000 cycles of `$random` stimulus, with enable toggling and resets at random times.

### `tb_Password.sv` (full testbench)

It contains tests 1-9 above, plus:

| # | Test |
|---|---|
| 10 | All 65,536 four-nibble windows (de Bruijn sequence) to find the password, followed by the password test |
| 11 | Back-to-back and overlapping words, interrupted words (idle cycles or a reset in the middle), reset right after a word, candidate words at every key phase, near misses, and words injected into random stimulus |

## Password

The password is the four plaintext nibbles **6, 3, B, 9**, entered one per clock cycle right after reset with `en` high. The chip then outputs the ciphertext nibbles C, A, F, E (the word `CAFE`) and raises `flag` on the fourth cycle.

Derivation: after reset the key sequence is 6, 7, 4, 5, and plaintext = ciphertext - key (mod 16):

| Cycle | Ciphertext | Key | Plaintext |
|---|---|---|---|
| 1 | C | 6 | 6 |
| 2 | A | 7 | 3 |
| 3 | F | 4 | B |
| 4 | E | 5 | 9 |

## Finding the secret word: de Bruijn sequence and Martin's algorithm

The flag depends on the last four ciphertext nibbles, and each nibble has 16 possible values, so there are 16^4 = 65,536 possible four-nibble windows. Random stimulus would hit a given window only about once per 65,536 enabled cycles and gives no guarantee of covering them all. A de Bruijn sequence covers every window exactly once.

### What is a de Bruijn sequence?

A de Bruijn sequence of order *n* over an alphabet of *k* symbols contains every possible string of *n* symbols exactly once [2]. Tiny example with bits (*k* = 2) and *n* = 3:

```
0011101000
```

Its ten symbols contain the windows `001, 011, 111, 110, 101, 010, 100, 000`, which are all 8 possible 3-bit patterns, each once. It is much shorter than writing the 8 patterns one after the other (24 symbols). It works like brute-forcing a keypad lock: one overlapping run of key presses tries every code [2].

For the chip, *k* = 16 (a nibble) and *n* = 4, so the sequence has 16^4 = 65,536 windows. The first three nibbles complete no window, so the sweep sends 65,536 + 3 = 65,539 nibbles. Plaintext is chosen cycle by cycle so that the chip's ciphertext follows this sequence, and the testbench prints every cycle the chip's `flag` is high together with the nibbles that caused it.

### Martin's greedy algorithm [1]

The sequence is generated with Martin's greedy algorithm (the "prefer-largest" version):

1. Start with *n* - 1 copies of the smallest symbol (three 0 nibbles).
2. Look at the last *n* - 1 symbols and append the largest symbol that does not create a window already used.
3. Repeat until no symbol can be appended. This always ends with a sequence of length *k*^*n* + *n* - 1 that contains every window exactly once.

Small example (*k* = 2, *n* = 3), starting from `00`:

| Sequence so far | Appended | New window |
|---|---|---|
| `00` | 1 | `001` |
| `001` | 1 | `011` |
| `0011` | 1 | `111` |
| `00111` | 0 (`111` already used) | `110` |
| `001110` | 1 | `101` |
| `0011101` | 0 (`011` already used) | `010` |
| `00111010` | 0 (`101` already used) | `100` |
| `001110100` | 0 (`001` already used) | `000` |

The result is `0011101000`. In `tb_Password.sv`, the task `sweep_all_words` does exactly this with nibbles: the array `seen` marks the windows already used, the loop `for (s = 15; s >= 0; ...)` tries the largest nibble first, and the three leading zeros are step 1.

## References

[1] M. H. Martin, "A problem in arrangements," *Bulletin of the American Mathematical Society*, vol. 40, no. 12, pp. 859-864, 1934.

[2] G. Cox, "The de Bruijn Sequence," *Baeldung on Computer Science*, Sep. 21, 2022 (updated Mar. 18, 2024). [Online]. Available: https://www.baeldung.com/cs/de-bruijn-sequence.
