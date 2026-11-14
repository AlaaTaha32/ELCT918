// ====================================================================================
//  uart_tx.sv  --  UART transmitter, 8N1 (see uart_rx.sv for the frame format)
//
//  Handshake: when `ready` is 1 and `valid` is 1 on a clock edge, the byte on `data`
//  is accepted and sent. `ready` then drops until the whole frame (including its
//  stop bit) has gone out, so the caller can simply hold `valid` high with the
//  next byte and wait.
// ====================================================================================
module uart_tx #(
    parameter int CLKS_PER_BIT = 868
) (
    input  logic       clk,
    input  logic [7:0] data,
    input  logic       valid,
    output logic       ready,
    output logic       tx                           // serial output, idles high
);
    localparam int CW = $clog2(CLKS_PER_BIT) + 1;

    typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;
    state_t state = IDLE;

    logic [CW-1:0] clk_cnt = '0;
    logic [2:0]    bit_idx = '0;
    logic [7:0]    shreg   = '0;                    // bit 0 is the bit currently on the line
    logic          tx_r    = 1'b1;                  // registered output: no glitches on the wire

    assign ready = (state == IDLE);
    assign tx    = tx_r;

    always_ff @(posedge clk) begin
        case (state)
            IDLE: begin
                tx_r    <= 1'b1;
                clk_cnt <= '0;
                if (valid) begin                         // byte accepted
                    shreg <= data;
                    tx_r  <= 1'b0;                       // start bit
                    state <= START;
                end
            end

            START: begin
                if (clk_cnt == CLKS_PER_BIT - 1) begin
                    clk_cnt <= '0;
                    tx_r    <= shreg[0];                 // first data bit (LSB)
                    bit_idx <= '0;
                    state   <= DATA;
                end else begin
                    clk_cnt <= clk_cnt + 1'b1;
                end
            end

            DATA: begin
                if (clk_cnt == CLKS_PER_BIT - 1) begin
                    clk_cnt <= '0;
                    if (bit_idx == 3'd7) begin
                        tx_r  <= 1'b1;                   // stop bit
                        state <= STOP;
                    end else begin
                        shreg   <= {1'b0, shreg[7:1]};   // move to the next bit
                        tx_r    <= shreg[1];
                        bit_idx <= bit_idx + 1'b1;
                    end
                end else begin
                    clk_cnt <= clk_cnt + 1'b1;
                end
            end

            STOP: begin
                if (clk_cnt == CLKS_PER_BIT - 1) begin
                    clk_cnt <= '0;
                    state   <= IDLE;
                end else begin
                    clk_cnt <= clk_cnt + 1'b1;
                end
            end
        endcase
    end
endmodule
