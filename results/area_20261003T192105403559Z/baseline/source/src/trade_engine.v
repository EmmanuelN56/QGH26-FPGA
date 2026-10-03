// One item, one accepted sample per clock. Clear takes priority over sample_valid;
// callers must clear on an earlier clock than the first sample of a session.
module trade_engine (
    input wire clk,
    input wire reset,
    input wire session_clear,
    input wire sample_valid,
    input wire [15:0] price,
    input wire warmup,
    output reg [7:0] action,
    output reg action_valid
);
    reg [15:0] prices [0:15];
    reg [3:0] write_pointer;
    reg [19:0] rolling_sum;
    reg [15:0] previous_price;
    reg [4:0] sample_count;
    wire full = sample_count == 16;
    wire [19:0] oldest = full ? {4'b0000, prices[write_pointer]} : 20'd0;
    wire [19:0] new_sum = rolling_sum - oldest + {4'b0000, price};
    wire [15:0] old_average = rolling_sum[19:4];
    wire [15:0] new_average = new_sum[19:4];
    integer i;

    always @(posedge clk) begin
        if (reset || session_clear) begin
            for (i = 0; i < 16; i = i + 1)
                prices[i] <= 0;
            write_pointer <= 0;
            rolling_sum <= 0;
            previous_price <= 0;
            sample_count <= 0;
            action <= 0;
            action_valid <= 0;
        end else begin
            action_valid <= 0;
            if (sample_valid) begin
                prices[write_pointer] <= price;
                write_pointer <= write_pointer + 1'b1;
                rolling_sum <= new_sum;
                previous_price <= price;
                if (!full)
                    sample_count <= sample_count + 1'b1;
                if (warmup || !full)
                    action <= 8'h00;
                else if (previous_price <= old_average && price > new_average)
                    action <= 8'h02;
                else if (previous_price >= old_average && price < new_average)
                    action <= 8'h01;
                // No crossing: retain action.
                action_valid <= 1;
            end
        end
    end
endmodule
