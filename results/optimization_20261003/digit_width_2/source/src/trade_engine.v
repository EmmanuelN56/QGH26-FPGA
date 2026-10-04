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

// Fixed-distance word shifters, a single compile-time W-bit arithmetic cell.
module digit_cell #(parameter integer W=4)(
    input wire [W-1:0] a,b,
    input wire subtract,carry_in,partial,
    output wire [W-1:0] value,
    output wire carry_out,equal
);
    wire [W-1:0] mask;
    generate if(W==8) begin
        assign mask=partial ? 8'h0f : 8'hff;
    end else begin
        assign mask={W{1'b1}};
    end endgenerate
    wire [W:0] result={1'b0,(a&mask)}+{1'b0,((b^{W{subtract}})&mask)}+carry_in;
    assign value=result[W-1:0]&mask;
    generate if(W==8) begin
        assign carry_out=partial ? result[4] : result[8];
    end else begin
        assign carry_out=result[W];
    end endgenerate
    assign equal=(a&mask)==(b&mask);
endmodule

// Narrow synchronous memories provide each arithmetic digit directly.
// W=1,2,4 align a sixteen-bit price with sum bit four using a constant address offset.
module trade_pair #(parameter integer W=2)(
    input wire clk,reset,session_clear,sample_valid,warmup,slot1_is_a,
    input wire [15:0] price1,price2,
    output reg [7:0] action1,action2,
    output reg action_valid
);
    localparam integer SD=20/W,PD=16/W,DW=$clog2(SD),DEPTH=1<<DW,OFF=4/W;
    localparam [3:0] IDLE=8,READ_OLD=0,CMP_OLD=1,READ_SUB=2,DO_SUB=3,
        READ_ADD=4,DO_ADD=5,READ_NEW=6,CMP_NEW=7,FINISH=9;
    reg [3:0] state;
    reg [W-1:0] sum_memory[0:2*DEPTH-1] /* synthesis syn_ramstyle="block_ram" */;
    reg [W-1:0] previous_memory[0:2*DEPTH-1] /* synthesis syn_ramstyle="block_ram" */;
    reg [W-1:0] history_memory[0:32*DEPTH-1] /* synthesis syn_ramstyle="block_ram" */;
    reg [W-1:0] sum_read,previous_read,history_read;
    reg [19:0] current_shift;
    reg [3:0] write_pointer;
    reg [4:0] sample_count;
    reg [DW-1:0] digit;
    reg slot,carry,equality,old_le,old_ge;
    reg [1:0] held_actions[0:1];
    wire item=slot ^ !slot1_is_a;
    wire full=sample_count==16;
    wire empty=sample_count==0;
    wire active=!state[3];
    wire executing=state[0];
    wire [1:0] phase=state[2:1];
    wire comparing=active && (phase==0 || phase==3);
    wire [DW-1:0] sum_digit=(active && !executing && (phase==0 || phase==3)) ? digit+OFF : digit;
    wire [DW:0] sum_address={item,sum_digit};
    wire [DW:0] previous_address={item,digit};
    wire [DW+4:0] history_address={item,write_pointer,digit};
    wire [W-1:0] old_price=full ? history_read : {W{1'b0}};
    wire [W-1:0] old_sum=empty ? {W{1'b0}} : sum_read;
    wire [W-1:0] a=comparing ? (state==CMP_OLD ? (empty ? {W{1'b0}} : previous_read) : current_shift[W-1:0]) :
        (state==DO_SUB ? old_sum : sum_read);
    wire [W-1:0] b=comparing ? old_sum : (state==DO_SUB ? old_price : current_shift[W-1:0]);
    wire [W-1:0] value;
    wire carry_next,digit_equal;
    digit_cell #(.W(W)) arithmetic(.a(a),.b(b),.subtract(state!=DO_ADD),.carry_in(carry),
        .partial(1'b0),.value(value),.carry_out(carry_next),.equal(digit_equal));
    wire equal_next=equality && digit_equal;
    wire [1:0] next_action=(warmup || !full) ? 2'd0 :
        (old_le && carry_next && !equal_next) ? 2'd2 :
        (old_ge && !carry_next) ? 2'd1 : held_actions[item];
    // A write follows its read on a different cycle. Nothing relies on collision data.
    always @(posedge clk) begin
        if(!reset && !session_clear) begin
            if(active && !executing)
                sum_read<=sum_memory[sum_address];
            if(active && !executing && phase==0) previous_read<=previous_memory[previous_address];
            if(active && !executing && phase==1) history_read<=history_memory[history_address];
            if(active && executing && (phase==1 || phase==2)) sum_memory[sum_address]<=value;
            if(active && executing && phase==2) begin
                history_memory[history_address]<=current_shift[W-1:0];
                previous_memory[previous_address]<=current_shift[W-1:0];
            end
        end
    end
    always @(posedge clk) begin
        if(reset || session_clear) begin
            state<=IDLE;slot<=0;write_pointer<=0;sample_count<=0;
            held_actions[0]<=0;held_actions[1]<=0;
            action1<=0;action2<=0;action_valid<=0;
        end else begin
            action_valid<=0;
            case(state)
                IDLE:if(sample_valid) begin
                    slot<=0;current_shift<={4'd0,price1};digit<=0;carry<=1;equality<=1;state<=READ_OLD;
                end
                READ_OLD:state<=CMP_OLD;
                READ_SUB:state<=DO_SUB;
                READ_ADD:state<=DO_ADD;
                READ_NEW:state<=CMP_NEW;
                CMP_OLD,DO_SUB,DO_ADD,CMP_NEW:begin
                    digit<=digit+1'b1;carry<=carry_next;equality<=equal_next;
                    if(active && executing && phase==2) current_shift<={current_shift[W-1:0],current_shift[19:W]};
                    if(state==CMP_NEW) current_shift<=current_shift>>W;
                    case(state)
                        CMP_OLD:begin
                            state<=READ_OLD;
                            if(digit==PD-1) begin
                                old_le<=!carry_next || equal_next;old_ge<=carry_next;
                                digit<=0;carry<=1;equality<=1;state<=READ_SUB;
                            end
                        end
                        DO_SUB:begin state<=READ_SUB;if(digit==SD-1) begin digit<=0;carry<=0;equality<=1;state<=READ_ADD;end end
                        DO_ADD:begin state<=READ_ADD;if(digit==SD-1) begin digit<=0;carry<=1;equality<=1;state<=READ_NEW;end end
                        CMP_NEW:begin
                            state<=READ_NEW;
                            if(digit==PD-1) begin
                                held_actions[item]<=next_action;
                                if(!slot) action1<={6'd0,next_action};else action2<={6'd0,next_action};
                                state<=FINISH;
                            end
                        end
                    endcase
                end
                FINISH:if(!slot) begin
                    slot<=1;current_shift<={4'd0,price2};digit<=0;carry<=1;equality<=1;state<=READ_OLD;
                end else begin
                    write_pointer<=write_pointer+1'b1;
                    if(!full) sample_count<=sample_count+1'b1;
                    action_valid<=1;state<=IDLE;
                end
                default:state<=IDLE;
            endcase
        end
    end
endmodule
