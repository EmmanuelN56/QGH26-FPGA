module packet_controller #(parameter integer TX_GAP_CYCLES=27000)(
    input wire clk,reset,
    input wire [7:0] rx_byte,
    input wire rx_valid,framing_error,
    output reg [7:0] tx_byte,
    output reg tx_start,
    input wire tx_busy,tx_done
);
    localparam [2:0] RECEIVE=0,PROCESS=1,SEND=2,WAIT_DONE=3,GAP=4;
    localparam integer GAP_WIDTH=TX_GAP_CYCLES>1 ? $clog2(TX_GAP_CYCLES) : 1;
    reg [2:0] state,byte_count;
    reg sample_pending;
    reg index_high_nonzero,session_zero,warmup;
    reg [7:0] price_high;
    // Words zero/one hold slot prices; word two holds the echoed index.
    reg [15:0] price_memory[0:3] /* synthesis syn_ramstyle="block_ram" */;
    reg [15:0] price_word;
    wire price_read_slot;
    reg slot1_is_a;
    reg [GAP_WIDTH-1:0] gap_timer;
    wire [7:0] action1,action2;
    wire pair_valid;
    wire request_complete=state==RECEIVE && !framing_error && rx_valid && byte_count==7;
    wire price_write=state==RECEIVE && !framing_error && rx_valid && (byte_count==1 || byte_count==4 || byte_count==7);
    wire [1:0] write_address=byte_count==1 ? 2'd2 : {1'b0,byte_count==7};
    wire responding=state==SEND || state==WAIT_DONE || state==GAP;
    wire [1:0] read_address=responding ? 2'd2 : {1'b0,price_read_slot};
    // The price high byte is held until its low byte completes the word.
    always @(posedge clk) begin
        if(!reset) begin
            if(price_write) price_memory[write_address]<={price_high,rx_byte};
            else price_word<=price_memory[read_address];
        end
    end
    // Clear on completion; sample_pending pulses on the following clock.
    trade_pair strategy(.clk(clk),.reset(reset),.session_clear(request_complete && session_zero),
        .sample_valid(sample_pending),.warmup(warmup),.slot1_is_a(slot1_is_a),
        .price_word(price_word),.price_read_slot(price_read_slot),.action1(action1),.action2(action2),.action_valid(pair_valid));
    // The organizer guarantees one of each fixed item ID. Each variable field
    // is overwritten by the complete request before it can be read.
    always @* begin
        case(byte_count)
            0:tx_byte=price_word[15:8];
            1:tx_byte=price_word[7:0];
            2:tx_byte=slot1_is_a ? 8'h11 : 8'h22;
            3:tx_byte=action1;
            4:tx_byte=slot1_is_a ? 8'h22 : 8'h11;
            5:tx_byte=action2;
            default:tx_byte=0;
        endcase
    end
    always @(posedge clk) begin
        if(reset) begin state<=RECEIVE;byte_count<=0;gap_timer<=0;tx_start<=0;sample_pending<=0;end
        else begin
            tx_start<=0;
            sample_pending<=0;
            case(state)
                RECEIVE:if(framing_error) byte_count<=0;
                    else if(rx_valid) begin
                        case(byte_count)
                            0:begin price_high<=rx_byte;index_high_nonzero<=rx_byte!=0;end
                            1:begin session_zero<=!index_high_nonzero && rx_byte==0;
                                warmup<=!index_high_nonzero && rx_byte<16;end
                            2:slot1_is_a<=rx_byte==8'h11;
                            3,6:price_high<=rx_byte;
                        endcase
                        if(byte_count==7) begin byte_count<=0;state<=PROCESS;sample_pending<=1;end
                        else byte_count<=byte_count+1'b1;
                    end
                PROCESS:if(pair_valid) begin byte_count<=0;state<=SEND;end
                SEND:if(!tx_busy) begin tx_start<=1;state<=WAIT_DONE;end
                WAIT_DONE:if(tx_done) begin
                    if(byte_count==7) begin byte_count<=0;state<=RECEIVE;end
                    else begin
                        byte_count<=byte_count+1'b1;
                        if(TX_GAP_CYCLES==0) state<=SEND;
                        else begin gap_timer<=TX_GAP_CYCLES-1;state<=GAP;end
                    end
                end
                GAP:if(gap_timer==0) state<=SEND;else gap_timer<=gap_timer-1'b1;
                default:begin state<=RECEIVE;byte_count<=0;end
            endcase
        end
    end
endmodule
