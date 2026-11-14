# Carat Temporal PE vs. Conventional Multiplier

A multiplier-free **processing element (PE)** from the paper *Carat: Unlocking Value-Level Parallelism for Multiplier-Free GEMMs* (Pan, San Miguel, Wu, ASPLOS '24), implemented in Verilog/SystemVerilog and compared against a conventional multiplier baseline on the **Digilent Nexys 4 DDR** (Artix-7 `xc7a100tcsg324-1`).

Both designs compute the same function: **FP8 (E4M3) input × signed INT8 weight → signed Q20.12 output**.

## Idea in brief

- **Baseline:** one ordinary FP8 × INT8 multiplier per row.
- **Carat column:** the rows share one weight. A single accumulator produces the multiples `8w, 9w, …, 15w` on successive cycles, and each row captures the multiple that matches its 3-bit mantissa, so no multiplier is needed. Subnormal, zero and NaN inputs are handled in the temporal converter.

## Repository layout

| Folder | Contents |
|---|---|
| `rtl/Baseline/` | Conventional multiplier column |
| `rtl/Carat/` | Carat temporal column (temporal converter, PE, post-processing, row, column) |
| `rtl/common/` | Shared board helpers: UART receiver/transmitter, FIFO, 7-segment driver |
| `tb/Baseline/`, `tb/Carat/` | Self-checking testbenches for each design |
| `tb/compare/` | Testbench that runs both designs on the same vectors |
| `sim/Baseline/`, `sim/Carat/`, `sim/compare/` | Questa `run.do` scripts |
| `Python/` | Reference model, vector generator, result comparison, UART host script |
| `FPGA/Baseline/`, `FPGA/Carat/` | Board top levels and constraints, each with `manual_switch/` and `uart/` |
| `Vivado_Reports/Baseline/`, `Vivado_Reports/Carat/` | Utilization and timing reports |
| `Bitstreams/` | Final `.bit` files |

## Number formats

| Signal | Format |
|---|---|
| Input `x` | FP8 E4M3: 1 sign, 4 exponent (bias 7), 3 mantissa bits. Zero, subnormals and NaN supported, no infinity |
| Weight `w` | Signed INT8 (two's complement) |
| Output `y` | Signed Q20.12 (32 bits): `y = value × 2^12`. The result is exact, never rounded |
| NaN input | Output forced to 0 and a NaN flag is raised |

## Requirements

- Questa (or ModelSim) for simulation
- Vivado for synthesis and bitstreams
- Python 3 (standard library only for the reference model; `pyserial` for the UART test)
- Digilent Nexys 4 DDR board (for the hardware tests)

## Running a simulation

Start Questa from the matching `sim/` folder. The `run.do` scripts use paths relative to it.

```
cd sim/Baseline
vsim -c -do run.do
python ../../Python/compare.py ../../Python/vectors.txt sim_results.txt
```

Use `vsim -do run.do` instead for the GUI with waveforms. The simulation should end with `RESULT: PASS`. The same steps apply to `sim/Carat/` and `sim/compare/`.

## Python tools

| Script | Purpose |
|---|---|
| `ref_model.py` | Exact reference model and test-vector generator (`python ref_model.py --help`) |
| `compare.py` | Checks simulation results against the reference, per test category |
| `uart_test.py` | Sends vectors to the FPGA over UART and checks every reply |
| `vectors.txt` | Pre-generated test vectors |

```
python Python/ref_model.py                # directed + random vectors
python Python/ref_model.py --exhaustive   # all 65,536 (x, w) pairs
```

## FPGA tests

Each design has two bitstreams, built from separate top levels and constraint files.

| Variant | How to test |
|---|---|
| `manual_switch/` | `SW[7:0]` = FP8 input `x`, `SW[15:8]` = INT8 weight `w`. The 7-segment display shows the Q20.12 result as hex digits with a point after the 5th digit. LED0 shows the NaN flag |
| `uart/` | Install `pyserial`, find the port with `python Python/uart_test.py --list`, then run `python Python/uart_test.py --port COM5 --vectors Python/vectors.txt` |

Build in Vivado for the part `xc7a100tcsg324-1`: add the sources from `rtl/` and the chosen `FPGA/` folder, add that folder's `.xdc`, set its top module, then generate the bitstream. Do not keep two constraint files in one project.

## Results

| Metric | Baseline | Carat column |
|---|---|---|
| LUTs | TBD | TBD |
| Flip-flops | TBD | TBD |
| DSP48 slices | TBD | TBD |
| Max clock frequency | TBD | TBD |
| Latency (cycles per batch) | TBD | TBD |
| Accuracy vs. exact reference | TBD | TBD |

Full reports are in `Vivado_Reports/`.

## Reference

Z. Pan, J. San Miguel, D. Wu. *Carat: Unlocking Value-Level Parallelism for Multiplier-Free GEMMs.* ASPLOS '24, La Jolla, CA, 2024.

## Team

- **Your Name**: [@your-github-username](https://github.com/your-github-username)
- **Teammate Name**: [@teammate-github-username](https://github.com/teammate-github-username)

Course: *Lab Assignment 5 – From Paper to Silicon*.
