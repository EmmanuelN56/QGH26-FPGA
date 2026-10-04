module top #(
    parameter integer CLOCK_FREQ = 27000000,
    parameter integer BAUD_RATE = 115200,
    parameter integer TX_GAP_CYCLES = 0,
    parameter integer USE_SHARED_BAUD = 1
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
    localparam integer DIVIDER=(CLOCK_FREQ + BAUD_RATE / 2) / BAUD_RATE;
    localparam integer TIMER_WIDTH=DIVIDER>1 ? $clog2(DIVIDER) : 1;
    reg [TIMER_WIDTH-1:0] shared_timer;
    wire rx_reload,tx_reload;
    wire [TIMER_WIDTH-1:0] rx_reload_value,tx_reload_value;
    always @(posedge sys_clk) begin
        if(reset) shared_timer<=0;
        else if(tx_reload) shared_timer<=tx_reload_value;
        else if(rx_reload) shared_timer<=rx_reload_value;
        else if(shared_timer!=0) shared_timer<=shared_timer-1'b1;
    end

    assign led0_n = 1'b1;
    assign led1_n = 1'b1;

    uart_rx #(.CLOCK_FREQ(CLOCK_FREQ), .BAUD_RATE(BAUD_RATE), .SHARE_TIMER(USE_SHARED_BAUD)) receiver (
        .clk(sys_clk), .reset(reset), .uart_rx_i(uart_rx_i),
        .rx_byte(rx_byte), .rx_valid(rx_valid), .framing_error(framing_error),
        .shared_timer(shared_timer),.timer_pause(tx_busy),.timer_reload(rx_reload),.timer_reload_value(rx_reload_value)
    );

    packet_controller #(.TX_GAP_CYCLES(TX_GAP_CYCLES)) packets (
        .clk(sys_clk), .reset(reset), .rx_byte(rx_byte), .rx_valid(rx_valid),
        .framing_error(framing_error), .tx_byte(tx_byte), .tx_start(tx_start),
        .tx_busy(tx_busy), .tx_done(tx_done)
    );

    uart_tx #(.CLOCK_FREQ(CLOCK_FREQ), .BAUD_RATE(BAUD_RATE), .SHARE_TIMER(USE_SHARED_BAUD)) transmitter (
        .clk(sys_clk), .reset(reset), .tx_byte(tx_byte), .tx_start(tx_start),
        .uart_tx_o(uart_tx_o), .tx_busy(tx_busy), .tx_done(tx_done),
        .shared_timer(shared_timer),.timer_reload(tx_reload),.timer_reload_value(tx_reload_value)
    );
endmodule
