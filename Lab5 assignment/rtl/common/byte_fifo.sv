// ============================================================================================
//  byte_fifo.sv  --  small first-in first-out queue of bytes (64 entries)
//
//  Why it exists: the FPGA needs longer to answer a request (5 reply bytes) than the PC
//  needs to send it (2 bytes), and the receiver has no way to say "wait". The FIFO
//  lets the PC send up to 32 requests (64 bytes) back to back; the FPGA works through
//  them one at a time. `overflow` stays 1 (sticky) if more than 64 bytes ever pile up.
//
//  Reading is "show-ahead": `dout` always shows the oldest byte; pulse `rd_en` to drop it.
//
//  `clear` (optional, synchronous, active HIGH): empties the queue and clears `overflow`.
//  It is active high on purpose: if a design that does not know about it (e.g. the baseline top)
//  leaves it unconnected, it is simply 0 and the FIFO behaves exactly as before.
// ============================================================================================
module byte_fifo #(
    parameter int DEPTH_LOG2 = 6                      // 2^6 = 64 entries
) (
    input  logic       clk,
    input  logic       wr_en,
    input  logic [7:0] din,
    input  logic       rd_en,
    input  logic       clear,                        // 1 = flush the queue and clear `overflow`
    output logic [7:0] dout,
    output logic       empty,
    output logic       overflow = 1'b0               // sticky: 1 once a byte has been lost
);
    localparam int DEPTH = 1 << DEPTH_LOG2;

    logic [7:0]            mem [0:DEPTH-1];
    logic [DEPTH_LOG2:0]   wr_ptr = '0;               // one extra bit tells "full" from "empty"
    logic [DEPTH_LOG2:0]   rd_ptr = '0;

    wire full = (wr_ptr[DEPTH_LOG2] != rd_ptr[DEPTH_LOG2]) &&
                (wr_ptr[DEPTH_LOG2-1:0] == rd_ptr[DEPTH_LOG2-1:0]);

    assign empty = (wr_ptr == rd_ptr);
    assign dout  = mem[rd_ptr[DEPTH_LOG2-1:0]];

    always_ff @(posedge clk) begin
      if (clear) begin
        wr_ptr   <= '0;
        rd_ptr   <= '0;
        overflow <= 1'b0;
      end else begin
        if (wr_en) begin
            if (!full) begin
                mem[wr_ptr[DEPTH_LOG2-1:0]] <= din;
                wr_ptr <= wr_ptr + 1'b1;
            end else begin
                overflow <= 1'b1;                     // a byte was lost
            end
        end
        if (rd_en && !empty) rd_ptr <= rd_ptr + 1'b1;
      end
    end
endmodule
