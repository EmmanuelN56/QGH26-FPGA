module uart_tx #(
    parameter integer CLOCK_FREQ = 27000000,
    parameter integer BAUD_RATE = 115200,
    parameter integer SHARE_TIMER = 0,
    parameter integer TIMER_WIDTH = $clog2((CLOCK_FREQ + BAUD_RATE / 2) / BAUD_RATE) > 0 ? $clog2((CLOCK_FREQ + BAUD_RATE / 2) / BAUD_RATE) : 1
) (
    input wire clk,
    input wire reset,
    input wire [7:0] tx_byte,
    input wire tx_start,
    output reg uart_tx_o,
    output reg tx_busy,
    output reg tx_done,
    input wire [TIMER_WIDTH-1:0] shared_timer,
    output wire timer_reload,
    output wire [TIMER_WIDTH-1:0] timer_reload_value
);
    localparam integer CLKS_PER_BIT = (CLOCK_FREQ + BAUD_RATE / 2) / BAUD_RATE;
    localparam integer COUNT_WIDTH = (CLKS_PER_BIT > 1) ? $clog2(CLKS_PER_BIT) : 1;
    reg [COUNT_WIDTH-1:0] local_bit_timer;
    wire [COUNT_WIDTH-1:0] bit_timer=SHARE_TIMER ? shared_timer : local_bit_timer;
    // The leading stop marker reaches zero only after all eight data bits and stop.
    reg [8:0] frame_bits;
    assign timer_reload=!reset && ((!tx_busy && tx_start) ||
        (tx_busy && bit_timer==0 && frame_bits!=0));
    assign timer_reload_value=CLKS_PER_BIT-1;

    always @(posedge clk) begin
        if (reset) begin
            uart_tx_o <= 1'b1;
            tx_busy <= 1'b0;
            tx_done <= 1'b0;
            local_bit_timer <= 0;
            frame_bits <= 0;
        end else begin
            tx_done <= 1'b0;
            if (!tx_busy) begin
                if (tx_start) begin
                    frame_bits <= {1'b1, tx_byte};
                    uart_tx_o <= 1'b0;
                    tx_busy <= 1'b1;
                    local_bit_timer <= CLKS_PER_BIT - 1;
                end
            end else if (bit_timer != 0)
                local_bit_timer <= bit_timer - 1'b1;
            else if (frame_bits == 0) begin
                // Keep busy asserted until the entire stop bit has elapsed.
                uart_tx_o <= 1'b1;
                tx_busy <= 1'b0;
                tx_done <= 1'b1;
            end else begin
                uart_tx_o <= frame_bits[0];
                frame_bits <= {1'b0, frame_bits[8:1]};
                local_bit_timer <= CLKS_PER_BIT - 1;
            end
        end
    end
endmodule
