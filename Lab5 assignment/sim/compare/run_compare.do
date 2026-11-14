# run_compare.do -- ModelSim/Questa:  vsim -do run_compare.do   (or  do run_compare.do  in the transcript)
# Put baseline_column.sv, carat_column.v, carat_tc.v, carat_pe.v, carat_po.v, carat_row.v
# and tb_compare.sv in the same folder.  carat_column.v `include`s the other carat_*.v
# files, so only carat_column.v is compiled (compiling them separately would redefine modules).

# Setting files location
set RTL ../../RTL
set TB  ../../tb
set PY  ../../Python

quit -sim
if {[file exists work]} { vdel -lib work -all }
vlib work
vmap work work

vlog -sv -work work $RTL/Baseline/baseline_column.sv $RTL/Carat/carat_column.sv $TB/compare/tb_compare.sv

vsim -voptargs=+acc -onfinish stop work.tb_compare

# ---------------------------------------------------------------- waves
add wave -divider {stimulus}
add wave -label clk      /tb_compare/clk
add wave -label start    /tb_compare/start
add wave -label w        -radix decimal /tb_compare/w
add wave -label x_flat   -radix hex     /tb_compare/x_flat

add wave -divider {baseline}
add wave -label b_done   /tb_compare/b_done
add wave -label b_y      -radix hex /tb_compare/b_y
add wave -label b_nan    -radix bin /tb_compare/b_nan

add wave -divider {carat}
add wave -label c_ready  /tb_compare/c_ready
add wave -label c_done   /tb_compare/c_done
add wave -label c_y      -radix hex /tb_compare/c_y
add wave -label c_nan    -radix bin /tb_compare/c_nan
add wave -label busy     /tb_compare/u_carat/busy
add wave -label C        -radix unsigned /tb_compare/u_carat/c
add wave -label A        -radix decimal  /tb_compare/u_carat/a

run -all
wave zoom full
