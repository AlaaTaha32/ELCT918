`timescale 1ns/1ps
//==============================================================================
// seg7_hex.v  --  8-digit multiplexed 7-segment hex display (Nexys 4 DDR)
//------------------------------------------------------------------------------
// Shows a 32-bit value as 8 hex digits.  Only one digit is lit at a time; the
// digit index changes fast (about 760 Hz for the whole scan with SCAN_BITS=17),
// so the eye sees all 8 digits.  On the Nexys 4 DDR anodes (AN) and cathodes
// (SEG) are ACTIVE-LOW.  SEG[0]=CA(a) ... SEG[6]=CG(g).  AN[0] = right-most digit.
//==============================================================================
module seg7_hex #(
    parameter SCAN_BITS = 17           // scan counter width (smaller = faster, for simulation)
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] value,          // value to show, digit 0 = value[3:0]
    input  wire [7:0]  dp_mask,        // 1 = light the decimal point of that digit
    output reg  [6:0]  seg,            // {g,f,e,d,c,b,a}, active-low
    output wire [7:0]  an,             // digit enables, active-low
    output wire        dp              // decimal point of the lit digit, active-low
);
    reg [SCAN_BITS-1:0] scan_cnt;
    always @(posedge clk) begin
        if (!rst_n) scan_cnt <= {SCAN_BITS{1'b0}};
        else        scan_cnt <= scan_cnt + 1'b1;
    end

    wire [2:0] digit = scan_cnt[SCAN_BITS-1 -: 3];        // which digit is lit now
    assign an = ~(8'b0000_0001 << digit);                 // one-hot, inverted (active-low)

    wire [3:0] nibble = value[4*digit +: 4];              // the 4 bits of that digit
    assign dp = ~dp_mask[digit];                          // point on the right of the lit digit

    // hex -> 7 segments, active-low, bit order {g,f,e,d,c,b,a}
    always @(*) begin
        case (nibble)
            4'h0: seg = 7'b1000000;
            4'h1: seg = 7'b1111001;
            4'h2: seg = 7'b0100100;
            4'h3: seg = 7'b0110000;
            4'h4: seg = 7'b0011001;
            4'h5: seg = 7'b0010010;
            4'h6: seg = 7'b0000010;
            4'h7: seg = 7'b1111000;
            4'h8: seg = 7'b0000000;
            4'h9: seg = 7'b0010000;
            4'hA: seg = 7'b0001000;
            4'hB: seg = 7'b0000011;
            4'hC: seg = 7'b1000110;
            4'hD: seg = 7'b0100001;
            4'hE: seg = 7'b0000110;
            default: seg = 7'b0001110;                     // F
        endcase
    end
endmodule
