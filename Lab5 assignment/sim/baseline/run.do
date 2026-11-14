# ----------------------------------------------------------------------------
#  run.do -- compile and run tb_baseline in Questa
#
#  Batch (no GUI):   vsim -c -do run.do
#  GUI:              vsim -do run.do        (or, inside Questa:  do run.do)
#
#  Optional vector file:  vsim -c -do run.do +VEC=my_vectors.txt   (edit the vsim line)
#  Run this from the folder that contains the .sv files and vectors.txt.
# ----------------------------------------------------------------------------

# Setting files location
set RTL ../../RTL
set TB  ../../tb
set PY  ../../Python

if {[file exists work]} { vdel -lib work -all }
vlib work
vmap work work

vlog -sv -work work $RTL/Baseline/baseline_column.sv $TB/Baseline/tb_baseline.sv

# +acc keeps signals visible for the wave window; -onfinish stop keeps the GUI open
# after $finish so you can inspect the waveform
vsim -voptargs=+acc -onfinish stop work.tb_baseline +VEC=$PY/vectors.txt +RES=sim_results.txt

if {![batch_mode]} {
    add wave -divider {clock / control}
    add wave sim:/tb_baseline/clk sim:/tb_baseline/rst_n sim:/tb_baseline/start sim:/tb_baseline/done
    add wave -divider {inputs}
    add wave -radix hex     sim:/tb_baseline/x
    add wave -radix decimal sim:/tb_baseline/w
    add wave -divider {outputs}
    add wave -radix hex     sim:/tb_baseline/y
    add wave -radix decimal sim:/tb_baseline/y
    add wave sim:/tb_baseline/nan_f
}

run -all

if {[batch_mode]} {
    quit -f
} else {
    wave zoom full
}
