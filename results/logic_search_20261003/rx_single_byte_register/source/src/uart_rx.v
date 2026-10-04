module uart_rx #(
    parameter integer CLOCK_FREQ = 27000000,
    parameter integer BAUD_RATE = 115200
) (
    input wire clk,
    input wire reset,
    input wire uart_rx_i,
    output reg [7:0] rx_byte,
    output reg rx_valid,
    output reg framing_error
);
    localparam integer CLKS_PER_BIT = (CLOCK_FREQ + BAUD_RATE / 2) / BAUD_RATE;
    localparam integer HALF_BIT = CLKS_PER_BIT / 2;
    localparam integer COUNT_WIDTH = (CLKS_PER_BIT > 1) ? $clog2(CLKS_PER_BIT) : 1;
    localparam [2:0] IDLE = 0, START = 1, DATA = 2, STOP = 3, WAIT_HIGH = 4;

    reg rx_meta, rx_sync, rx_previous;
    reg [2:0] state;
    reg [COUNT_WIDTH-1:0] bit_timer;
    reg [2:0] bit_index;
    // rx_byte is meaningful when rx_valid is asserted; use it as the receive shifter.

    // The pin is asynchronous to clk; only rx_sync reaches the state machine.
    always @(posedge clk) begin
        if (reset) begin
            rx_meta <= 1'b1;
            rx_sync <= 1'b1;
            rx_previous <= 1'b1;
        end else begin
            rx_meta <= uart_rx_i;
            rx_sync <= rx_meta;
            rx_previous <= rx_sync;
        end
    end

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            bit_timer <= 0;
            bit_index <= 0;
            rx_byte <= 0;
            rx_valid <= 1'b0;
            framing_error <= 1'b0;
        end else begin
            rx_valid <= 1'b0;
            framing_error <= 1'b0;
            case (state)
                IDLE: begin
                    if (rx_previous && !rx_sync) begin
                        bit_timer <= HALF_BIT - 1;
                        state <= START;
                    end
                end
                START: begin
                    if (bit_timer != 0)
                        bit_timer <= bit_timer - 1'b1;
                    else if (!rx_sync) begin
                        // Confirm the start bit halfway through, then sample bit centers.
                        bit_timer <= CLKS_PER_BIT - 1;
                        bit_index <= 0;
                        state <= DATA;
                    end else
                        state <= IDLE;
                end
                DATA: begin
                    if (bit_timer != 0)
                        bit_timer <= bit_timer - 1'b1;
                    else begin
                        rx_byte <= {rx_sync, rx_byte[7:1]};
                        bit_timer <= CLKS_PER_BIT - 1;
                        if (bit_index == 7)
                            state <= STOP;
                        else
                            bit_index <= bit_index + 1'b1;
                    end
                end
                STOP: begin
                    if (bit_timer != 0)
                        bit_timer <= bit_timer - 1'b1;
                    else if (rx_sync) begin
                        rx_valid <= 1'b1;
                        state <= IDLE;
                    end else begin
                        framing_error <= 1'b1;
                        state <= WAIT_HIGH;
                    end
                end
                WAIT_HIGH: begin
                    // A held-low line is one bad frame, not an endless stream of bytes.
                    if (rx_sync)
                        state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
