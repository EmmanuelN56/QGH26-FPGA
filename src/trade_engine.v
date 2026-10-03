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
    // Logical clear: no old memory entry is read until all 16 are overwritten.
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

    always @(posedge clk) begin
        if (reset || session_clear) begin
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

// Two independent item contexts, one shared arithmetic datapath.
// Caller keeps the request inputs stable until action_valid and never pipelines requests.
module trade_pair (
    input wire clk, reset, session_clear, sample_valid, warmup,
    input wire slot1_is_a,
    input wire [15:0] price1, price2,
    output reg [7:0] action1, action2,
    output reg action_valid
);
    reg [15:0] prices [0:31];
    reg [19:0] sums [0:1];
    reg [15:0] previous_prices [0:1];
    reg [1:0] held_actions [0:1];
    reg [3:0] write_pointer;
    reg window_full;
    wire [4:0] sample_count=window_full ? 5'd16 : {1'b0,write_pointer};
    reg processing, slot;
    wire item=slot ^ !slot1_is_a;
    wire full=window_full;
    wire [15:0] price=slot ? price2 : price1;
    wire [19:0] old_sum=sums[item];
    wire [19:0] oldest=full ? {4'd0,prices[{item,write_pointer}]} : 20'd0;
    wire [19:0] new_sum=old_sum-oldest+{4'd0,price};
    wire [15:0] previous=previous_prices[item];
    wire [15:0] old_average=old_sum[19:4], new_average=new_sum[19:4];
    wire [16:0] old_diff={1'b0,previous}-{1'b0,old_average};
    wire [16:0] new_diff={1'b0,price}-{1'b0,new_average};
    wire old_equal=old_diff[15:0]==0;
    wire new_equal=new_diff[15:0]==0;
    wire [1:0] next_action=(warmup || !full) ? 2'd0 :
        ((old_diff[16] || old_equal) && !new_diff[16] && !new_equal) ? 2'd2 :
        (!old_diff[16] && new_diff[16]) ? 2'd1 : held_actions[item];
    // Entries are logically invalid until all sixteen current-session prices are written.
    always @(posedge clk) begin
        if(processing && !reset && !session_clear)
            prices[{item,write_pointer}]<=price;
    end
    always @(posedge clk) begin
        if(reset || session_clear) begin
            sums[0]<=0;sums[1]<=0;previous_prices[0]<=0;previous_prices[1]<=0;
            held_actions[0]<=0;held_actions[1]<=0;write_pointer<=0;window_full<=0;
            processing<=0;slot<=0;action1<=0;action2<=0;action_valid<=0;
        end else begin
            action_valid<=0;
            if(!processing) begin
                if(sample_valid) begin processing<=1;slot<=0;end
            end else begin
                sums[item]<=new_sum;previous_prices[item]<=price;held_actions[item]<=next_action;
                if(!slot) begin action1<={6'd0,next_action};slot<=1;end
                else begin
                    action2<={6'd0,next_action};action_valid<=1;processing<=0;
                    write_pointer<=write_pointer+1'b1;
                    if(write_pointer==15) window_full<=1;
                end
            end
        end
    end
endmodule
