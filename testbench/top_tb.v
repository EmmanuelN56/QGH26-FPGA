`timescale 1ns/1ps
module top_tb;
    localparam real CLOCK_PERIOD = 1000000000.0 / 27000000.0;
    localparam real BIT_PERIOD = 1000000000.0 / 115200.0;
    localparam real TX_FRAME_PERIOD = CLOCK_PERIOD * 234 * 10;
    reg sys_clk = 0, reset_btn = 0, uart_rx_i = 1;
    wire uart_tx_o, led0_n, led1_n;
    reg [7:0] expected [0:23];
    integer received_count = 0, expected_count = 0;
    real last_start = -1000000000.0;

    always #(CLOCK_PERIOD / 2) sys_clk = ~sys_clk;
    top dut (.sys_clk(sys_clk), .reset_btn(reset_btn), .uart_rx_i(uart_rx_i),
             .uart_tx_o(uart_tx_o), .led0_n(led0_n), .led1_n(led1_n));

    task send_byte;
        input [7:0] value;
        integer bit_number;
        begin
            uart_rx_i = 0;
            #(BIT_PERIOD);
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                uart_rx_i = value[bit_number];
                #(BIT_PERIOD);
            end
            uart_rx_i = 1;
            #(BIT_PERIOD);
        end
    endtask

    task send_packet;
        input [63:0] request;
        input [63:0] response;
        reg [63:0] request_shift, response_shift;
        integer byte_number;
        begin
            request_shift = request;
            response_shift = response;
            for (byte_number = 0; byte_number < 8; byte_number = byte_number + 1) begin
                expected[expected_count] = response_shift[63:56];
                expected_count = expected_count + 1;
                response_shift = response_shift << 8;
            end
            for (byte_number = 0; byte_number < 7; byte_number = byte_number + 1) begin
                send_byte(request_shift[63:56]);
                request_shift = request_shift << 8;
            end
            #(BIT_PERIOD * 2);
            if (received_count != expected_count - 8 || uart_tx_o !== 1'b1)
                $fatal(1, "Response began before all eight request bytes");
            send_byte(request_shift[63:56]);
            wait (received_count == expected_count);
            #(BIT_PERIOD * 3);
        end
    endtask

    initial begin : serial_monitor
        reg [7:0] value;
        integer bit_number;
        forever begin
            @(negedge uart_tx_o);
            if (received_count >= expected_count)
                $fatal(1, "Unsolicited response byte");
            if ((received_count % 8) != 0 &&
                $realtime - last_start < TX_FRAME_PERIOD + 1000000)
                $fatal(1, "Missing one-millisecond response byte gap");
            last_start = $realtime;
            #(BIT_PERIOD / 2);
            if (uart_tx_o !== 1'b0)
                $fatal(1, "Invalid response start bit");
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                #(BIT_PERIOD);
                value[bit_number] = uart_tx_o;
            end
            #(BIT_PERIOD);
            if (uart_tx_o !== 1'b1 || value !== expected[received_count])
                $fatal(1, "Response byte %0d: got %02x expected %02x",
                       received_count, value, expected[received_count]);
            received_count = received_count + 1;
        end
    end

    initial begin
        #(BIT_PERIOD * 2);
        if (uart_tx_o !== 1'b1 || led0_n !== 1'b1 || led1_n !== 1'b1)
            $fatal(1, "Configuration reset did not leave UART and LEDs idle");
        send_packet(64'h123422abcd11fedc, 64'h1234220011000000);
        send_packet(64'h000011ffff220000, 64'h0000110022000000);
        send_byte(8'hff);
        send_byte(8'hee);
        @(negedge sys_clk);
        reset_btn = 1;
        repeat (5) @(negedge sys_clk);
        reset_btn = 0;
        #(BIT_PERIOD * 2);
        send_packet(64'h0001220001112345, 64'h0001220011000000);
        #(BIT_PERIOD * 20);
        if (received_count != 24)
            $fatal(1, "Wrong response count");
        $display("PASS top_tb: three packets, slot order, partial packet reset, byte gaps");
        $finish;
    end

    initial begin
        #50000000;
        $fatal(1, "top_tb timeout");
    end
endmodule
