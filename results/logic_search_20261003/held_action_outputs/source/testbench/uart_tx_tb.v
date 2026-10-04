`timescale 1ns/1ps
module uart_tx_tb;
    localparam real CLOCK_PERIOD = 1000000000.0 / 27000000.0;
    localparam integer CLKS_PER_BIT = 234;
    localparam real BIT_PERIOD = CLOCK_PERIOD * CLKS_PER_BIT;
    reg clk = 0, reset = 1, tx_start = 0;
    reg [7:0] tx_byte = 0;
    wire uart_tx_o, tx_busy, tx_done;
    reg [7:0] expected [0:255];
    integer expected_count = 0, decoded_count = 0, done_count = 0;
    integer i;
    reg previous_done = 0;

    always #(CLOCK_PERIOD / 2.0) clk = ~clk;
    uart_tx dut (.clk(clk), .reset(reset), .tx_byte(tx_byte), .tx_start(tx_start),
                 .uart_tx_o(uart_tx_o), .tx_busy(tx_busy), .tx_done(tx_done));

    always @(posedge clk) begin
        #1;
        if (reset) begin
            previous_done = 0;
            if (uart_tx_o !== 1'b1 || tx_busy || tx_done)
                $fatal(1, "TX reset did not produce idle high");
        end else begin
            if (tx_done) begin
                if (previous_done || tx_busy || uart_tx_o !== 1'b1)
                    $fatal(1, "Invalid tx_done pulse");
                done_count = done_count + 1;
            end
            previous_done = tx_done;
        end
    end

    initial begin : serial_monitor
        reg [7:0] decoded;
        integer bit_number;
        forever begin
            @(negedge uart_tx_o);
            if (!reset) begin : frame
                #(BIT_PERIOD / 2);
                if (reset) disable frame;
                if (uart_tx_o !== 1'b0 || !tx_busy)
                    $fatal(1, "Bad start bit");
                for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                    #(BIT_PERIOD);
                    if (reset) disable frame;
                    decoded[bit_number] = uart_tx_o;
                    if (!tx_busy || tx_done)
                        $fatal(1, "TX ended before data completed");
                end
                #(BIT_PERIOD);
                if (reset) disable frame;
                if (uart_tx_o !== 1'b1 || !tx_busy || tx_done)
                    $fatal(1, "Bad stop bit or early completion");
                if (decoded_count >= expected_count || decoded !== expected[decoded_count])
                    $fatal(1, "Unexpected TX byte %02x at %0d", decoded, decoded_count);
                decoded_count = decoded_count + 1;
                @(posedge tx_done or posedge reset);
            end
        end
    end

    task transmit;
        input [7:0] value;
        reg [31:0] cycles;
        begin
            expected[expected_count] = value;
            expected_count = expected_count + 1;
            @(negedge clk);
            tx_byte = value;
            tx_start = 1;
            @(negedge clk);
            tx_start = 0;
            tx_byte = ~value;
            cycles = 0;
            while (tx_busy) begin
                // A second one-clock start while busy must be ignored.
                tx_start = (cycles == CLKS_PER_BIT * 2);
                @(negedge clk);
                cycles = cycles + 1;
            end
            tx_start = 0;
            if (cycles != CLKS_PER_BIT * 10)
                $fatal(1, "TX frame length: %0d clocks expected %0d", cycles, CLKS_PER_BIT * 10);
        end
    endtask

    initial begin
        repeat (5) @(negedge clk);
        reset = 0;
        repeat (5) @(negedge clk);
        for (i = 0; i < 256; i = i + 1)
            transmit(i[7:0]);
        repeat (5) @(negedge clk);
        if (decoded_count != 256 || done_count != 256)
            $fatal(1, "TX counts: decoded %0d done %0d", decoded_count, done_count);

        tx_start = 1;
        @(negedge clk);
        tx_start = 0;
        #(BIT_PERIOD * 2);
        @(negedge clk);
        reset = 1;
        #(BIT_PERIOD * 12);
        repeat (5) @(negedge clk);
        reset = 0;
        #(BIT_PERIOD * 2);
        if (tx_busy || tx_done || uart_tx_o !== 1'b1 || done_count != 256)
            $fatal(1, "Reset failed to cancel active TX frame");
        $display("PASS uart_tx_tb: 256 bytes, exact frame length, busy rejection, reset");
        $finish;
    end

    initial begin
        #30000000;
        $fatal(1, "uart_tx_tb timeout");
    end
endmodule
