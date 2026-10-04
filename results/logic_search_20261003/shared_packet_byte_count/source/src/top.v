module top #(
    parameter integer CLOCK_FREQ = 27000000,
    parameter integer BAUD_RATE = 115200,
    parameter integer TX_GAP_CYCLES = 0
) (
    input wire sys_clk,
    input wire reset_btn,
    input wire uart_rx_i,
    output wire uart_tx_o,
    output wire led0_n,
    output wire led1_n
);
    // Active-high KEY2 reset: assert immediately, release after two clock edges.
    // The initial value also resets the design when its configuration starts.
    reg [1:0] reset_pipe = 2'b11;
    always @(posedge sys_clk or posedge reset_btn) begin
        if (reset_btn)
            reset_pipe <= 2'b11;
        else
            reset_pipe <= {reset_pipe[0], 1'b0};
    end
    wire reset = reset_pipe[1];
    wire [7:0] rx_byte, tx_byte;
    wire rx_valid, framing_error, tx_start, tx_busy, tx_done;

    assign led0_n = 1'b1;
    assign led1_n = 1'b1;

    uart_rx #(.CLOCK_FREQ(CLOCK_FREQ), .BAUD_RATE(BAUD_RATE)) receiver (
        .clk(sys_clk), .reset(reset), .uart_rx_i(uart_rx_i),
        .rx_byte(rx_byte), .rx_valid(rx_valid), .framing_error(framing_error)
    );

    packet_controller #(.TX_GAP_CYCLES(TX_GAP_CYCLES)) packets (
        .clk(sys_clk), .reset(reset), .rx_byte(rx_byte), .rx_valid(rx_valid),
        .framing_error(framing_error), .tx_byte(tx_byte), .tx_start(tx_start),
        .tx_busy(tx_busy), .tx_done(tx_done)
    );

    uart_tx #(.CLOCK_FREQ(CLOCK_FREQ), .BAUD_RATE(BAUD_RATE)) transmitter (
        .clk(sys_clk), .reset(reset), .tx_byte(tx_byte), .tx_start(tx_start),
        .uart_tx_o(uart_tx_o), .tx_busy(tx_busy), .tx_done(tx_done)
    );
endmodule
