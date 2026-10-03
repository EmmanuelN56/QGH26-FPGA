`timescale 1ns/1ps
module trade_engine_tb;
    reg clk = 0, reset = 1, session_clear = 0, sample_valid = 0;
    reg [15:0] price_a, price_b;
    reg warmup;
    wire [7:0] action_a, action_b;
    wire valid_a, valid_b;
    reg [127:0] vectors [0:4095], states [0:4095];
    reg [63:0] request, response;
    reg [127:0] observed;
    integer count, i;
    reg [1023:0] vector_path, state_path;
    always #5 clk = ~clk;
    trade_engine a (.clk(clk), .reset(reset), .session_clear(session_clear),
        .sample_valid(sample_valid), .price(price_a), .warmup(warmup),
        .action(action_a), .action_valid(valid_a));
    trade_engine b (.clk(clk), .reset(reset), .session_clear(session_clear),
        .sample_valid(sample_valid), .price(price_b), .warmup(warmup),
        .action(action_b), .action_valid(valid_b));

    initial begin
        if (!$value$plusargs("COUNT=%d", count) || count > 4096 || count < 1)
            $fatal(1, "COUNT must be 1..4096");
        if (!$value$plusargs("VECTORS=%s", vector_path) ||
            !$value$plusargs("STATES=%s", state_path))
            $fatal(1, "Missing vector paths");
        $readmemh(vector_path, vectors, 0, count-1);
        $readmemh(state_path, states, 0, count-1);
        repeat (3) @(negedge clk);
        reset = 0;
        for (i = 0; i < count; i = i + 1) begin
            request = vectors[i][127:64];
            response = vectors[i][63:0];
            warmup = request[63:48] < 16;
            price_a = request[47:40] == 8'h11 ? request[39:24] : request[15:0];
            price_b = request[47:40] == 8'h22 ? request[39:24] : request[15:0];
            if (request[63:48] == 0) begin
                session_clear = 1;
                // Clear must win even if the caller presents a sample.
                sample_valid = 1;
                @(negedge clk);
                if (valid_a || valid_b || a.rolling_sum !== 0 || b.rolling_sum !== 0 || action_a !== 0 || action_b !== 0)
                    $fatal(1, "Clear did not precede ingestion at vector %0d", i);
                session_clear = 0;
            end
            sample_valid = 1;
            @(negedge clk);
            sample_valid = 0;
            if (!valid_a || !valid_b ||
                (request[47:40] == 8'h11 ? action_a : action_b) !== response[39:32] ||
                (request[23:16] == 8'h11 ? action_a : action_b) !== response[23:16])
                $fatal(1, "Engine action mismatch at vector %0d", i);
            observed = {4'd0, a.rolling_sum, 4'd0, b.rolling_sum,
                a.previous_price, b.previous_price,
                4'd0, a.write_pointer, 4'd0, b.write_pointer,
                3'd0, a.sample_count, 3'd0, b.sample_count, 16'd0};
            if (observed !== states[i])
                $fatal(1, "State mismatch vector %0d got %032x expected %032x", i, observed, states[i]);
            @(negedge clk);
            if (valid_a || valid_b)
                $fatal(1, "action_valid was not a one-clock pulse");
            if (a.rolling_sum !== observed[123:104] || b.rolling_sum !== observed[99:80])
                $fatal(1, "State changed without a sample");
        end
        $display("PASS trade_engine_tb: %0d packets, actions and internal state", count);
        $finish;
    end
    initial begin
        #1000000;
        $fatal(1, "trade_engine_tb timeout");
    end
endmodule
