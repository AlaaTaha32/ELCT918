// ==================================================================================
//  baseline_column.sv  --  conventional baseline for the Carat column
//
//  Eight ordinary FP8(E4M3) x INT8 multipliers, one per row, all sharing the
//  weight w.  Same interface convention and the same Q20.12 output format as
//  carat_column, so the testbench can compare them output by output.
//
//  Latency: the result is registered at the same edge that accepts `start`,
//  so `done` is high in the very next cycle (1 cycle, versus 8 for Carat).
//
//  Synthesis note: the `*` below is deliberately a real multiplier (Vivado maps
//  it to LUTs or a DSP48; add (* use_dsp = "yes" *) / "no" on the multiply if you
//  want to force one or the other when you compare resources with Carat).
// ==================================================================================
module baseline_column #(
    parameter int ROWS = 8                      // number of rows in the column
) (
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    start,      // Start processing the column
    input  logic signed [7:0]       w,          // Weight, in INT8 format
    input  logic [ROWS*8-1:0]       x_flat,     // Input column, in FP8 E4M3 format
    output logic                    done,       // Done processing the column
    output logic [ROWS*32-1:0]      y_flat,     // Output column, in Q20.12 format
    output logic [ROWS-1:0]         nan_flat    // NaN flags for each row
);
    // FP8 E4M3 x INT8 -> Q20.12, written directly from the number format:
    //   value = (-1)^s * 2^(E-10) * M * w,   with M = {1,m}, E = e   (normal)
    //                                         or  M = {0,m}, E = 1 (subnormal, meaning that exponent = 0000)
    // Q20.12 results is calculated by multiplying the decimal value by 2^12, so the result is:
    //   Q20.12 result = (M * w) << (E + 2)

    function automatic logic signed [31:0] fp8_times_int8 (
        input logic [7:0]        Input, // 1 bit sign, 4 bit exponent, 3 bit mantissa
        input logic signed [7:0] Weight
    );
    // the function calculates the Q20.12 result of multiplying an FP8 E4M3 number by an INT8 number, using only integer arithmetic
        logic [3:0]         mant;            // 4-bit modified mantissa (the extra bit is the implicit 1 for normal numbers, or 0 for subnormal numbers)
        logic [4:0]         ex;              // 5-bit modified exponent   
        logic signed [31:0] p;               // the intermediate product of mantissa and weight 
        begin
            if (Input[6:3] == 4'd0) begin    // zero or subnormal (exponent = 0000)
                mant = {1'b0, Input[2:0]};   // M = {0,m}
                ex   = 5'd1;                 // E = 1 for subnormal
            end else begin                   // normal
                mant = {1'b1, Input[2:0]};   // M = {1,m}
                ex   = {1'b0, Input[6:3]};   // E = e
            end
            p = $signed({1'b0, mant}) * Weight;  // the real multiplier
            p = p <<< (ex + 5'd2);               // shift left by (E + 2) to get Q20.12 result 
            fp8_times_int8 = Input[7] ? -p : p;  // apply sign of the FP8 number to the result
        end
    endfunction

    function automatic logic is_nan_fp8 (input logic [7:0] Input);
        // returns true if the input is a NaN (i.e. exponent = 1111 and mantissa = 111) in FP8 E4M3 format 
        is_nan_fp8 = (Input[6:3] == 4'hF) && (Input[2:0] == 3'h7);
    endfunction

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            done <= 1'b0;
            nan_flat <= '0;
            y_flat <= '0;
        end else begin
            done <= start;
            if (start) begin
                for (int i = 0; i < ROWS; i++) begin
                    nan_flat[i]        <= is_nan_fp8(x_flat[8*i +: 8]);
                    y_flat[32*i +: 32] <= is_nan_fp8(x_flat[8*i +: 8]) ? 32'sd0
                                          : fp8_times_int8(x_flat[8*i +: 8], w); // calculate Q20.12 result only for non-NaN inputs
                end
            end
        end
    end
endmodule
