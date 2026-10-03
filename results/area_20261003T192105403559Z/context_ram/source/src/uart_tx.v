module uart_tx #(
    parameter integer CLOCK_FREQ = 27000000,
    parameter integer BAUD_RATE = 115200
) (
    input wire clk,
    input wire reset,
    input wire [7:0] tx_byte,
    input wire tx_start,
    output reg uart_tx_o,
    output reg tx_busy,
    output reg tx_done
);
    localparam integer CLKS_PER_BIT = (CLOCK_FREQ + BAUD_RATE / 2) / BAUD_RATE;
    localparam integer COUNT_WIDTH = (CLKS_PER_BIT > 1) ? $clog2(CLKS_PER_BIT) : 1;
    reg [COUNT_WIDTH-1:0] bit_timer;
    reg [3:0] bit_index;
    reg [9:0] frame_bits;

    always @(posedge clk) begin
        if (reset) begin
            uart_tx_o <= 1'b1;
            tx_busy <= 1'b0;
            tx_done <= 1'b0;
            bit_timer <= 0;
            bit_index <= 0;
            frame_bits <= 10'h3ff;
        end else begin
            tx_done <= 1'b0;
            if (!tx_busy) begin
                if (tx_start) begin
                    // Bit 0 is start, bits 1..8 are data LSB first, bit 9 is stop.
                    frame_bits <= {1'b1, tx_byte, 1'b0};
                    uart_tx_o <= 1'b0;
                    tx_busy <= 1'b1;
                    bit_index <= 0;
                    bit_timer <= CLKS_PER_BIT - 1;
                end
            end else if (bit_timer != 0)
                bit_timer <= bit_timer - 1'b1;
            else if (bit_index == 9) begin
                // Keep busy asserted until the entire stop bit has elapsed.
                uart_tx_o <= 1'b1;
                tx_busy <= 1'b0;
                tx_done <= 1'b1;
            end else begin
                bit_index <= bit_index + 1'b1;
                uart_tx_o <= frame_bits[1];
                frame_bits <= {1'b1, frame_bits[9:1]};
                bit_timer <= CLKS_PER_BIT - 1;
            end
        end
    end
endmodule
