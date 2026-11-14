// ================================================================================================
//  nexys4_baseline_uart_top.sv  --  test the baseline multiplier from a PC over UART
//                                   Digilent Nexys 4 DDR (xc7a100tcsg324-1)
//
//  PROTOCOL (8N1, 115200 baud by default; the USB cable is the serial link)
//    PC -> FPGA   2 bytes per test:   x   w          x = FP8 E4M3 code, w = signed INT8
//    FPGA -> PC   5 bytes per test:   y[31:24] y[23:16] y[15:8] y[7:0] flags
//                                     y = Q20.12 result, big-endian, two's complement
//                                     flags bit 0 = NaN (all other bits 0)
//    The PC may send up to 32 tests (64 bytes) back to back; replies come in the same order.
//    A half-received request (odd number of bytes) is forgotten after TIMEOUT_CYCLES of silence.
//
//  BOARD INDICATORS
//    7-segment  last result, same format as the switch version (5 integer digits . 3 fraction)
//    LED[0]     NaN flag of the last result
//    LED[1]     blinks when a byte is received          LED[2]  blinks when a byte is sent
//    LED[3]     input FIFO overflow (PC sent too much at once) - should stay off
//    LED[15:8]  number of replies sent so far (wraps at 256)
//
//  Needs: baseline_column.sv, uart_rx.sv, uart_tx.sv, byte_fifo.sv, hex8_display.sv
// ==================================================================================================
`timescale 1ns/1ps

module nexys4_baseline_uart_top #(
    parameter int CLKS_PER_BIT   = 868,          // 100 MHz / 115200 baud
    parameter int TIMEOUT_CYCLES = 10_000_000    // 100 ms of silence resets a half request
) (
    input  logic        CLK100MHZ,
    input  logic        UART_TXD_IN,             // from the USB-UART chip = FPGA RECEIVE pin
    output logic        UART_RXD_OUT,            // to the USB-UART chip   = FPGA TRANSMIT pin
    output logic [15:0] LED,
    output logic [7:0]  AN,
    output logic [6:0]  SEG,
    output logic        DP
);

    // ------------------------------------------------------------------
    //  Serial receiver -> FIFO
    // ------------------------------------------------------------------
    logic [7:0] rx_data;
    logic       rx_valid;

    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_rx (
        .clk   (CLK100MHZ),
        .rx    (UART_TXD_IN),
        .data  (rx_data),
        .valid (rx_valid)
    );

    logic [7:0] fifo_dout;
    logic       fifo_empty, fifo_ovf, fifo_rd;

    byte_fifo u_fifo (
        .clk      (CLK100MHZ),
        .wr_en    (rx_valid),
        .din      (rx_data),
        .rd_en    (fifo_rd),
        .dout     (fifo_dout),
        .empty    (fifo_empty),
        .overflow (fifo_ovf)
    );

    // ------------------------------------------------------------------
    //  Device under test
    // ------------------------------------------------------------------
    logic [7:0]  x_reg = '0;
    logic [7:0]  w_reg = '0;
    logic        calc;                           // one-cycle "start" pulse for the baseline
    wire  [31:0] y;
    wire  [0:0]  nan_f;

    baseline_column #(.ROWS(1)) u_baseline (
        .clk      (CLK100MHZ),
        .rst_n    (1'b1),
        .start    (calc),
        .w        (w_reg),
        .x_flat   (x_reg),
        .done     (),
        .y_flat   (y),
        .nan_flat (nan_f)
    );

    // ------------------------------------------------------------------
    //  Serial transmitter
    // ------------------------------------------------------------------
    logic [7:0] tx_data;
    logic       tx_valid, tx_ready;

    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_tx (
        .clk   (CLK100MHZ),
        .data  (tx_data),
        .valid (tx_valid),
        .ready (tx_ready),
        .tx    (UART_RXD_OUT)
    );

    // ------------------------------------------------------------------
    //  Controller:  get x -> get w -> compute -> send 5 bytes -> repeat
    // ------------------------------------------------------------------
    typedef enum logic [1:0] {S_X, S_W, S_CALC, S_TX} state_t;
    state_t state = S_X;

    logic [2:0] idx = '0;                                    // which reply byte is being sent (0..4)
    logic [$clog2(TIMEOUT_CYCLES+1)-1:0] idle_cnt = '0;      // silence counter while waiting for w

    always_comb begin
        fifo_rd  = ((state == S_X) || (state == S_W)) && !fifo_empty;   // take a byte from the FIFO
        calc     = (state == S_CALC);
        tx_valid = (state == S_TX);
        case (idx)
            3'd0:    tx_data = y[31:24];
            3'd1:    tx_data = y[23:16];
            3'd2:    tx_data = y[15:8];
            3'd3:    tx_data = y[7:0];
            default: tx_data = {7'd0, nan_f[0]};
        endcase
    end

    always_ff @(posedge CLK100MHZ) begin
        case (state)
            S_X: begin                                       // wait for the x byte
                idle_cnt <= '0;
                if (!fifo_empty) begin
                    x_reg <= fifo_dout;
                    state <= S_W;
                end
            end

            S_W: begin                                       // wait for the w byte
                if (!fifo_empty) begin
                    w_reg    <= fifo_dout;
                    idle_cnt <= '0;
                    state    <= S_CALC;
                end else if (idle_cnt == TIMEOUT_CYCLES) begin
                    idle_cnt <= '0;                          // w never came: forget this x
                    state    <= S_X;
                end else begin
                    idle_cnt <= idle_cnt + 1'b1;
                end
            end

            S_CALC: begin                                    // `calc` is high: the baseline registers y
                idx   <= '0;
                state <= S_TX;
            end

            S_TX: begin                                      // y is valid; send it byte by byte
                if (tx_ready) begin                          // uart_tx accepts tx_data on this edge
                    if (idx == 3'd4) state <= S_X;
                    else             idx   <= idx + 1'b1;
                end
            end
        endcase
    end

    // ------------------------------------------------------------------
    //  Indicators
    // ------------------------------------------------------------------
    logic [21:0] rx_act = '0, tx_act = '0;                   // ~42 ms "blink stretchers"
    logic [7:0]  reply_cnt = '0;

    always_ff @(posedge CLK100MHZ) begin
        if (rx_valid)                           rx_act <= '1;
        else if (rx_act != 0)                   rx_act <= rx_act - 1'b1;

        if (tx_valid && tx_ready)               tx_act <= '1;
        else if (tx_act != 0)                   tx_act <= tx_act - 1'b1;

        if (state == S_TX && tx_ready && idx == 3'd4) reply_cnt <= reply_cnt + 1'b1;
    end

    assign LED = {reply_cnt, 4'b0000, fifo_ovf, (tx_act != 0), (rx_act != 0), nan_f[0]};

    hex8_display u_display (
        .clk   (CLK100MHZ),
        .value (y),
        .AN    (AN),
        .SEG   (SEG),
        .DP    (DP)
    );

endmodule
