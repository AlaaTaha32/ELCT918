// Behaviour observed with en = 1:
//   dout[7:4] : counts enabled cycles (1, 2, 3 ... F, 0, 1 ...)
//   dout[3:0] : ciphertext nibble = din + K, K steps through 6, 7, 4, 5 on each enabled cycle
//   flag      : high when the last four ciphertext nibbles (including the onebeing output this cycle) spell CAFE
// Nothing changes while en = 0 (state and outputs hold).

module solution (
    input            clk,
    input            rst_n,
    input            en,
    input      [3:0] din,
    output reg [7:0] dout,
    output reg       flag
);

    reg [1:0]  phase;                        // enabled cycles since reset, mod 4
    reg [11:0] hist;                         // previous 3 ciphertext nibbles, oldest is the most significant nibble

    // K = 6, 7, 4, 5 for phase = 0, 1, 2, 3  ->  6 XOR phase
    wire [3:0]  key    = 4'd6 ^ {2'b00, phase};
    wire [3:0]  cipher = din + key;          // ciphertext nibble produced on this enabled cycle
    wire [15:0] window = {hist, cipher};     // last 4 ciphertext nibbles, including the new one

    always @(posedge clk) begin
        if (!rst_n) begin
            dout  <= 8'h00;
            phase <= 2'd0;
            hist  <= 12'h000;
            flag  <= 1'b0;
        end else if (en) begin
            dout  <= {dout[7:4] + 4'd1, cipher};
            phase <= phase + 2'd1;
            hist  <= window[11:0];           // drop the oldest nibble, keep the previous 2 + the new cipher nibble in this cycle
            flag  <= (window == 16'hCAFE);   // high together with the 4th nibble
        end
    end

endmodule