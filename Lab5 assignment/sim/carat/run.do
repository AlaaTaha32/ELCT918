# ----------------------------------------------------------------------------
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

vlog -sv -work work $RTL/Carat/carat_column.sv $TB/Carat/tb_carat.sv

# +acc keeps signals visible for the wave window; -onfinish stop keeps the GUI open
# after $finish so you can inspect the waveform
vsim -voptargs=+acc -onfinish stop work.tb_carat +VEC=$PY/vectors.txt +RES=sim_results.txt

if {![batch_mode]} {
    add wave -divider {clock / control}
    add wave sim:/tb_carat/clk sim:/tb_carat/rst_n sim:/tb_carat/start sim:/tb_carat/done sim:/tb_carat/ready
    add wave -divider {inputs}
    add wave -radix hex     sim:/tb_carat/x
    add wave -radix decimal sim:/tb_carat/w
    add wave -divider {outputs}
    add wave -radix hex     sim:/tb_carat/y
    add wave -radix decimal sim:/tb_carat/y
    add wave sim:/tb_carat/nan_f sim:/tb_carat/zero_f
}

run -all

if {[batch_mode]} {
    quit -f
} else {
    wave zoom full
}
