`timescale 1ns/1ps
module uart_rx_tb;
    localparam real CLOCK_PERIOD = 1000000000.0 / 27000000.0;
    localparam real BIT_PERIOD = 1000000000.0 / 115200.0;
    reg clk = 0;
    reg reset = 1;
    reg uart_rx_i = 1;
    wire [7:0] rx_byte;
    wire rx_valid, framing_error;
    reg [7:0] expected [0:511];
    integer expected_count = 0, received_count = 0, error_count = 0;
    integer i;
    reg previous_valid = 0, previous_error = 0;

    always #(CLOCK_PERIOD / 2.0) clk = ~clk;
    uart_rx dut (.clk(clk), .reset(reset), .uart_rx_i(uart_rx_i),
                 .rx_byte(rx_byte), .rx_valid(rx_valid), .framing_error(framing_error));

    always @(posedge clk) begin
        #1;
        if (reset) begin
            previous_valid = 0;
            previous_error = 0;
            if (rx_valid || framing_error)
                $fatal(1, "RX pulse during reset");
        end else begin
            if (rx_valid && previous_valid)
                $fatal(1, "rx_valid lasted more than one clock");
            if (framing_error && previous_error)
                $fatal(1, "framing_error lasted more than one clock");
            if (rx_valid) begin
                if (received_count >= expected_count)
                    $fatal(1, "Unsolicited RX byte");
                if (rx_byte !== expected[received_count])
                    $fatal(1, "RX byte %0d: got %02x expected %02x",
                           received_count, rx_byte, expected[received_count]);
                received_count = received_count + 1;
            end
            if (framing_error) begin
                if (rx_valid)
                    $fatal(1, "Bad stop bit also produced rx_valid");
                error_count = error_count + 1;
            end
            previous_valid = rx_valid;
            previous_error = framing_error;
        end
    end

    // This serial stimulus uses the requested baud, independently of the DUT divider.
    task send_frame;
        input [7:0] value;
        input stop_bit;
        input real bit_time;
        integer bit_number;
        begin
            uart_rx_i = 0;
            #(bit_time);
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                uart_rx_i = value[bit_number];
                #(bit_time);
            end
            uart_rx_i = stop_bit;
            #(bit_time);
        end
    endtask

    task expect_frame;
        input [7:0] value;
        input real bit_time;
        begin
            expected[expected_count] = value;
            expected_count = expected_count + 1;
            send_frame(value, 1'b1, bit_time);
        end
    endtask

    initial begin
        repeat (5) @(negedge clk);
        reset = 0;
        #(BIT_PERIOD * 2);
        uart_rx_i = 0;
        #(BIT_PERIOD / 4);
        uart_rx_i = 1;
        #(BIT_PERIOD * 2);
        if (received_count != 0 || error_count != 0)
            $fatal(1, "Short start glitch was accepted");

        for (i = 0; i < 256; i = i + 1)
            expect_frame(i[7:0], BIT_PERIOD);
        #(BIT_PERIOD * 3);
        expect_frame(8'h55, BIT_PERIOD * 0.98);
        expect_frame(8'haa, BIT_PERIOD * 1.02);

        send_frame(8'h00, 1'b0, BIT_PERIOD);
        #(BIT_PERIOD * 20);
        if (error_count != 1)
            $fatal(1, "Held-low line should produce exactly one framing error");
        uart_rx_i = 1;
        #(BIT_PERIOD * 2);
        expect_frame(8'ha5, BIT_PERIOD);

        uart_rx_i = 0;
        #(BIT_PERIOD * 2);
        @(negedge clk);
        reset = 1;
        uart_rx_i = 1;
        repeat (5) @(negedge clk);
        reset = 0;
        #(BIT_PERIOD * 2);
        expect_frame(8'h3c, BIT_PERIOD);
        #(BIT_PERIOD * 3);
        if (received_count != expected_count || error_count != 1)
            $fatal(1, "RX final counts: received %0d expected %0d errors %0d",
                   received_count, expected_count, error_count);
        $display("PASS uart_rx_tb: %0d bytes, glitch rejection, bad stop, break, reset", received_count);
        $finish;
    end

    initial begin
        #30000000;
        $fatal(1, "uart_rx_tb timeout");
    end
endmodule
