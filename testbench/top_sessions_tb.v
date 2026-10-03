`timescale 1ns/1ps
module top_sessions_tb;
`ifdef BOARD_TIMING
    localparam integer CLOCK_FREQ = 27000000, BAUD_RATE = 115200, GAP_CYCLES = 27000;
`else
    // Accelerated transport for exhaustive sessions; top_tb tests board defaults.
    localparam integer CLOCK_FREQ = 1000000, BAUD_RATE = 100000, GAP_CYCLES = 10;
`endif
    localparam real CLOCK_PERIOD = 1000000000.0 / CLOCK_FREQ;
    localparam real BIT_PERIOD = 1000000000.0 / BAUD_RATE;
    localparam integer DIVIDER = (CLOCK_FREQ + BAUD_RATE / 2) / BAUD_RATE;
    localparam real FRAME_PERIOD = CLOCK_PERIOD * DIVIDER * 10;
    reg sys_clk = 0, reset_btn = 0, uart_rx_i = 1;
    wire uart_tx_o, led0_n, led1_n;
    reg [127:0] vectors [0:4095];
    reg [7:0] expected [0:32767];
    reg [63:0] request_shift, response_shift;
    integer received_count = 0, expected_count = 0, count, i, j;
    reg [1023:0] vector_path;
    real last_start = -1000000000.0;
    always #(CLOCK_PERIOD / 2) sys_clk = ~sys_clk;
    top #(.CLOCK_FREQ(CLOCK_FREQ), .BAUD_RATE(BAUD_RATE), .TX_GAP_CYCLES(GAP_CYCLES)) dut (
        .sys_clk(sys_clk), .reset_btn(reset_btn), .uart_rx_i(uart_rx_i),
        .uart_tx_o(uart_tx_o), .led0_n(led0_n), .led1_n(led1_n));

    task send_byte;
        input [7:0] value;
        integer k;
        begin
            uart_rx_i = 0;
            #(BIT_PERIOD);
            for (k = 0; k < 8; k = k + 1) begin
                uart_rx_i = value[k];
                #(BIT_PERIOD);
            end
            uart_rx_i = 1;
            #(BIT_PERIOD);
        end
    endtask

    initial begin : monitor
        reg [7:0] value;
        integer k;
        forever begin
            @(negedge uart_tx_o);
            if (received_count >= expected_count)
                $fatal(1, "Unsolicited response byte");
            if ((received_count % 8) != 0 &&
                $realtime - last_start < FRAME_PERIOD + GAP_CYCLES * CLOCK_PERIOD - 1)
                $fatal(1, "Response gap too short");
            last_start = $realtime;
            #(BIT_PERIOD / 2);
            if (uart_tx_o !== 0) $fatal(1, "Bad start bit");
            for (k = 0; k < 8; k = k + 1) begin
                #(BIT_PERIOD);
                value[k] = uart_tx_o;
            end
            #(BIT_PERIOD);
            if (uart_tx_o !== 1 || value !== expected[received_count])
                $fatal(1, "Response byte %0d got %02x expected %02x", received_count, value, expected[received_count]);
            received_count = received_count + 1;
        end
    end

    initial begin
        if (!$value$plusargs("COUNT=%d", count) || count < 1 || count > 4096 ||
            !$value$plusargs("VECTORS=%s", vector_path))
            $fatal(1, "Missing/invalid vectors or count");
        $readmemh(vector_path, vectors, 0, count-1);
        #(BIT_PERIOD * 3);
        for (i = 0; i < count; i = i + 1) begin
            request_shift = vectors[i][127:64];
            response_shift = vectors[i][63:0];
            for (j = 0; j < 8; j = j + 1) begin
                expected[expected_count] = response_shift[63:56];
                expected_count = expected_count + 1;
                response_shift = response_shift << 8;
            end
            for (j = 0; j < 7; j = j + 1) begin
                send_byte(request_shift[63:56]);
                request_shift = request_shift << 8;
            end
            #(BIT_PERIOD * 2);
            if (received_count != expected_count - 8 || uart_tx_o !== 1)
                $fatal(1, "Early response at vector %0d", i);
            send_byte(request_shift[63:56]);
            wait (received_count == expected_count);
            #(BIT_PERIOD * 3);
        end
        #(BIT_PERIOD * 20);
        if (received_count != count * 8) $fatal(1, "Extra/missing bytes");
        $display("PASS top_sessions_tb: %0d packets / %0d bytes, gaps, no early/extra replies", count, received_count);
        $finish;
    end
    initial begin
        #30000000000;
        $fatal(1, "top_sessions_tb timeout");
    end
endmodule
