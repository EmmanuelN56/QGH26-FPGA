`timescale 1ns/1ps
module top_recovery_tb #(parameter integer GAP_CYCLES = 0);
    localparam real CLOCK_PERIOD = 1000000000.0 / 27000000.0;
    localparam real BIT_PERIOD = 1000000000.0 / 115200.0;
    localparam real TX_FRAME_PERIOD = CLOCK_PERIOD * 234 * 10;
    reg sys_clk = 0, reset_btn = 0, uart_rx_i = 1;
    wire uart_tx_o, led0_n, led1_n;
    reg [7:0] expected [0:63];
    integer received_count = 0, expected_count = 0;
    reg gapped=0;
    reg was_start=0,was_done=0,was_pair=0;
    reg [7:0] held_byte;
    always @(posedge sys_clk) begin
        #1;
        if(!dut.reset) begin
            if(dut.tx_start && was_start || dut.tx_done && was_done || dut.packets.pair_valid && was_pair) $fatal(1,"Duplicate handshake pulse");
            if(dut.tx_start) held_byte=dut.tx_byte;
            if(dut.tx_busy && dut.tx_byte!==held_byte) $fatal(1,"Controller changed byte while transmitter was busy");
        end
        was_start=dut.tx_start;was_done=dut.tx_done;was_pair=dut.packets.pair_valid;
    end
    real last_start = -1000000000.0;

    always #(CLOCK_PERIOD / 2) sys_clk = ~sys_clk;
    top #(.TX_GAP_CYCLES(GAP_CYCLES)) dut (.sys_clk(sys_clk), .reset_btn(reset_btn), .uart_rx_i(uart_rx_i),
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

    task send_bad_stop;
        input [7:0] value;
        integer k;
        begin
            uart_rx_i=0;#(BIT_PERIOD);
            for(k=0;k<8;k=k+1) begin uart_rx_i=value[k];#(BIT_PERIOD);end
            uart_rx_i=0;#(BIT_PERIOD*2);
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
                if(gapped) #(BIT_PERIOD*(byte_number+1));
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
                $realtime - last_start < TX_FRAME_PERIOD + GAP_CYCLES * CLOCK_PERIOD)
                $fatal(1, "Response byte gap below configured minimum");
            if ((received_count % 8) != 0 &&
                $realtime - last_start > TX_FRAME_PERIOD + (GAP_CYCLES + 4) * CLOCK_PERIOD + 100)
                $fatal(1, "Response byte gap exceeds configured gap plus handshake");
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
        send_byte(8'h00);send_byte(8'h00);send_byte(8'h11);send_byte(8'hff);
        send_byte(8'hff);send_byte(8'h22);send_byte(8'h55);
        #(BIT_PERIOD*20);
        if(received_count!=24 || uart_tx_o!==1) $fatal(1,"Partial packet produced a reply");
        uart_rx_i=0;#(BIT_PERIOD/4);uart_rx_i=1;#(BIT_PERIOD*2);
        if(received_count!=24) $fatal(1,"Start glitch produced a reply");
        send_bad_stop(8'haa);
        uart_rx_i=1;#(BIT_PERIOD*3);
        if(received_count!=24) $fatal(1,"Invalid eighth byte produced a reply");
        send_packet(64'h000022ffaa11aaff,64'h0000220011000000);
        // Idle gaps do not discard accepted partial packets.
        gapped=1;
        send_packet(64'h00011155aa22aa55,64'h0001110022000000);
        gapped=0;
        send_byte(8'hff);send_byte(8'hff);send_byte(8'h22);
        @(negedge sys_clk);reset_btn=1;repeat(5) @(negedge sys_clk);reset_btn=0;
        #(BIT_PERIOD*3);
        send_packet(64'h000011000022ffff,64'h0000110022000000);
        #(BIT_PERIOD*20);
        if (received_count != 48)
            $fatal(1, "Wrong response count");
        $display("PASS top_recovery_tb: six packets, partial packets, invalid start/stop recovery, inter-byte gaps, physical reset, handshake pulses");
        $finish;
    end

    initial begin
        #50000000;
        $fatal(1, "top_tb timeout");
    end
endmodule
