module packet_controller #(parameter integer TX_GAP_CYCLES=27000)(
    input wire clk,reset,
    input wire [7:0] rx_byte,
    input wire rx_valid,framing_error,
    output reg [7:0] tx_byte,
    output reg tx_start,
    input wire tx_busy,tx_done
);
    localparam [2:0] RECEIVE=0,PREPARE=1,SAMPLE=2,BUILD=3,SEND=4,WAIT_DONE=5,GAP=6;
    localparam integer GAP_WIDTH=TX_GAP_CYCLES>1 ? $clog2(TX_GAP_CYCLES) : 1;
    reg [2:0] state,rx_count,tx_count;
    reg [15:0] index,price1,price2;
    reg slot1_is_a;
    reg [GAP_WIDTH-1:0] gap_timer;
    wire [7:0] action1,action2;
    wire pair_valid;
    trade_pair strategy(.clk(clk),.reset(reset),.session_clear(state==PREPARE && index==0),
        .sample_valid(state==SAMPLE),.warmup(index<16),.slot1_is_a(slot1_is_a),
        .price1(price1),.price2(price2),.action1(action1),.action2(action2),.action_valid(pair_valid));
    // The organizer guarantees one of each fixed item ID. Each variable field
    // is overwritten by the complete request before it can be read.
    always @* begin
        case(tx_count)
            0:tx_byte=index[15:8];
            1:tx_byte=index[7:0];
            2:tx_byte=slot1_is_a ? 8'h11 : 8'h22;
            3:tx_byte=action1;
            4:tx_byte=slot1_is_a ? 8'h22 : 8'h11;
            5:tx_byte=action2;
            default:tx_byte=0;
        endcase
    end
    always @(posedge clk) begin
        if(reset) begin state<=RECEIVE;rx_count<=0;tx_count<=0;gap_timer<=0;tx_start<=0;end
        else begin
            tx_start<=0;
            case(state)
                RECEIVE:if(framing_error) rx_count<=0;
                    else if(rx_valid) begin
                        case(rx_count)
                            0,1:index<={index[7:0],rx_byte};
                            2:slot1_is_a<=rx_byte==8'h11;
                            3,4:price1<={price1[7:0],rx_byte};
                            6,7:price2<={price2[7:0],rx_byte};
                        endcase
                        if(rx_count==7) begin rx_count<=0;state<=PREPARE;end
                        else rx_count<=rx_count+1'b1;
                    end
                PREPARE:state<=SAMPLE;
                SAMPLE:state<=BUILD;
                BUILD:if(pair_valid) begin tx_count<=0;state<=SEND;end
                SEND:if(!tx_busy) begin tx_start<=1;state<=WAIT_DONE;end
                WAIT_DONE:if(tx_done) begin
                    if(tx_count==7) state<=RECEIVE;
                    else begin
                        tx_count<=tx_count+1'b1;
                        if(TX_GAP_CYCLES==0) state<=SEND;
                        else begin gap_timer<=TX_GAP_CYCLES-1;state<=GAP;end
                    end
                end
                GAP:if(gap_timer==0) state<=SEND;else gap_timer<=gap_timer-1'b1;
                default:begin state<=RECEIVE;rx_count<=0;end
            endcase
        end
    end
endmodule
