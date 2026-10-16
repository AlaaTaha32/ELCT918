set DUT_FILES  {mystery.v solution.v}
set TB_FILES   {tb_Password.sv}

# ---- Clean start ----
quit -sim
if {[file exists work]} { vdel -lib work -all }
vlib work
vmap work work

# ---- Compile ----
foreach f $DUT_FILES { vlog -work work $f }
foreach f $TB_FILES  { vlog -work work -sv $f }

# ---- Load design ----
vsim -voptargs=+acc work.tb

# ---- Waveforms ----
view wave
delete wave *
configure wave -namecolwidth 150
configure wave -valuecolwidth 80
configure wave -timelineunits ns

add wave -divider "Inputs"
add wave -noupdate -color yellow /tb/clk
add wave -noupdate -color orange /tb/rst_n
add wave -noupdate               /tb/en
add wave -noupdate -radix hex    /tb/din

add wave -divider "mystery (reference)"
add wave -noupdate -radix hex /tb/dout_mystery
add wave -noupdate            /tb/flag_mystery

add wave -divider "solution"
add wave -noupdate -radix hex /tb/dout_solution
add wave -noupdate            /tb/flag_solution

add wave -divider "Result"
add wave -noupdate -color red /tb/differ

# ---- Run ----
onfinish stop
run -all
wave zoom range 0ns 700ns
