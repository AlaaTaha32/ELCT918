// =============================================================================================
//  uart_rx.sv  --  UART receiver, 8 data bits, no parity, 1 stop bit (8N1)
//
//  A UART line idles high. A byte is sent as:
//      start bit (0) | d0 d1 d2 d3 d4 d5 d6 d7 (least-significant bit first) | stop bit (1)
//  Every bit lasts CLKS_PER_BIT clock cycles (100 MHz / 115200 baud = 868).
//
//  The receiver waits for the falling edge of the start bit, then samples every
//  bit in the MIDDLE of its time slot, where the line is most stable.
// =============================================================================================
module uart_rx #(
    parameter int CLKS_PER_BIT = 868            // clock cycles per UART bit (must be >= 4)
) (
    input  logic       clk,
    input  logic       rx,                      // serial input, idles high
    output logic [7:0] data,                    // the last byte received
    output logic       valid                    // 1-cycle pulse: `data` holds a new byte
);
    localparam int CW = $clog2(CLKS_PER_BIT) + 1;

    typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;
    state_t state = IDLE;

    // The serial line is asynchronous to our clock: pass it through two flip-flops
    (* ASYNC_REG = "TRUE" *) logic rx_meta = 1'b1;
    (* ASYNC_REG = "TRUE" *) logic rx_sync = 1'b1;

    logic [CW-1:0] clk_cnt = '0;                // counts clock cycles inside one bit
    logic [2:0]    bit_idx = '0;                // which data bit is being received
    logic [7:0]    shreg   = '0;                // bits are shifted in from the top

    assign data = shreg;

    always_ff @(posedge clk) begin
        rx_meta <= rx;
        rx_sync <= rx_meta;
        valid   <= 1'b0;

        case (state)
            IDLE: begin
                clk_cnt <= '0;
                if (!rx_sync) state <= START;            // falling edge: a start bit begins
            end

            START: begin                                 // go to the middle of the start bit
                if (clk_cnt == (CLKS_PER_BIT - 1) / 2) begin
                    clk_cnt <= '0;
                    if (!rx_sync) begin                  // still low: it is a real start bit
                        bit_idx <= '0;
                        state   <= DATA;
                    end else begin
                        state   <= IDLE;                 // a glitch, ignore it
                    end
                end else begin
                    clk_cnt <= clk_cnt + 1'b1;
                end
            end

            DATA: begin                                  // one full bit later = middle of bit 0, 1, ...
                if (clk_cnt == CLKS_PER_BIT - 1) begin
                    clk_cnt <= '0;
                    shreg   <= {rx_sync, shreg[7:1]};    // LSB arrives first, ends up at bit 0
                    if (bit_idx == 3'd7) state <= STOP;
                    else                 bit_idx <= bit_idx + 1'b1;
                end else begin
                    clk_cnt <= clk_cnt + 1'b1;
                end
            end

            STOP: begin                                  // middle of the stop bit
                if (clk_cnt == CLKS_PER_BIT - 1) begin
                    clk_cnt <= '0;
                    state   <= IDLE;
                    valid   <= rx_sync;                  // accept the byte only if the stop bit is 1
                end else begin
                    clk_cnt <= clk_cnt + 1'b1;
                end
            end
        endcase
    end
endmodule
