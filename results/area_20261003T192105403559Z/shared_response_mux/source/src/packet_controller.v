module packet_controller #(
    parameter integer TX_GAP_CYCLES = 27000
) (
    input wire clk, reset,
    input wire [7:0] rx_byte,
    input wire rx_valid, framing_error,
    output reg [7:0] tx_byte,
    output reg tx_start,
    input wire tx_busy, tx_done
);
    localparam [2:0] RECEIVE=0, PREPARE=1, SAMPLE=2, BUILD=3,
                     SEND=4, WAIT_DONE=5, GAP=6;
    localparam integer GAP_WIDTH=(TX_GAP_CYCLES>1) ? $clog2(TX_GAP_CYCLES):1;
    reg [2:0] state, rx_count, tx_count;
    reg [63:0] packet;
    reg [GAP_WIDTH-1:0] gap_timer;
    wire [15:0] index=packet[63:48];
    wire session_clear=state==PREPARE && index==0;
    wire sample_valid=state==SAMPLE;
    wire warmup=index<16;
    wire [7:0] action1,action2;
    wire pair_valid;
    trade_pair strategy(.clk(clk),.reset(reset),.session_clear(session_clear),
        .sample_valid(sample_valid),.warmup(warmup),.slot1_is_a(packet[47:40]==8'h11),
        .price1(packet[39:24]),.price2(packet[15:0]),.action1(action1),.action2(action2),
        .action_valid(pair_valid));
    always @* begin
        case(tx_count)
            0:tx_byte=packet[63:56];
            1:tx_byte=packet[55:48];
            2:tx_byte=packet[47:40];
            3:tx_byte=action1;
            4:tx_byte=packet[23:16];
            5:tx_byte=action2;
            default:tx_byte=8'h00;
        endcase
    end
    // Eight accepted bytes overwrite the entire buffer before it is used.
    // Reuse it for the response once both item updates have completed.
    always @(posedge clk) begin
        if(reset) begin
            state<=RECEIVE;rx_count<=0;tx_count<=0;gap_timer<=0;tx_start<=0;
        end else begin
            tx_start<=0;
            case(state)
                RECEIVE: if(framing_error) rx_count<=0;
                    else if(rx_valid) begin
                        packet<={packet[55:0],rx_byte};
                        if(rx_count==7) begin rx_count<=0;state<=PREPARE;end
                        else rx_count<=rx_count+1'b1;
                    end
                PREPARE:state<=SAMPLE;
                SAMPLE:state<=BUILD;
                BUILD:if(pair_valid) begin
                    tx_count<=0;state<=SEND;
                end
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
