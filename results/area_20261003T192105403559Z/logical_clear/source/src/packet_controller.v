module packet_controller #(
    parameter integer TX_GAP_CYCLES = 27000
) (
    input wire clk,
    input wire reset,
    input wire [7:0] rx_byte,
    input wire rx_valid,
    input wire framing_error,
    output reg [7:0] tx_byte,
    output reg tx_start,
    input wire tx_busy,
    input wire tx_done
);
    localparam [2:0] RECEIVE = 0, PREPARE = 1, SAMPLE = 2, BUILD = 3,
                     SEND = 4, WAIT_DONE = 5, GAP = 6;
    localparam integer GAP_WIDTH = (TX_GAP_CYCLES > 1) ? $clog2(TX_GAP_CYCLES) : 1;
    reg [2:0] state;
    reg [2:0] rx_count, tx_count;
    reg [7:0] request_bytes [0:7];
    reg [63:0] response_bytes;
    reg [GAP_WIDTH-1:0] gap_timer;
    wire [15:0] index = {request_bytes[0], request_bytes[1]};
    wire session_clear = state == PREPARE && index == 0;
    wire sample_valid = state == SAMPLE;
    wire warmup = index < 16;
    wire [15:0] price_a = request_bytes[2] == 8'h11 ?
                         {request_bytes[3], request_bytes[4]} :
                         {request_bytes[6], request_bytes[7]};
    wire [15:0] price_b = request_bytes[2] == 8'h22 ?
                         {request_bytes[3], request_bytes[4]} :
                         {request_bytes[6], request_bytes[7]};
    wire [7:0] action_a, action_b;
    wire valid_a, valid_b;
    // Official requests contain one of each item. Histories follow IDs;
    // only response construction uses the original slot placement.
    trade_engine engine_a (
        .clk(clk), .reset(reset), .session_clear(session_clear),
        .sample_valid(sample_valid), .price(price_a), .warmup(warmup),
        .action(action_a), .action_valid(valid_a)
    );
    trade_engine engine_b (
        .clk(clk), .reset(reset), .session_clear(session_clear),
        .sample_valid(sample_valid), .price(price_b), .warmup(warmup),
        .action(action_b), .action_valid(valid_b)
    );

    always @(posedge clk) begin
        if (reset) begin
            state <= RECEIVE;
            rx_count <= 0;
            tx_count <= 0;
            response_bytes <= 0;
            gap_timer <= 0;
            tx_byte <= 0;
            tx_start <= 1'b0;
        end else begin
            tx_start <= 1'b0;
            case (state)
                RECEIVE: begin
                    if (framing_error)
                        rx_count <= 0;
                    else if (rx_valid) begin
                        request_bytes[rx_count] <= rx_byte;
                        if (rx_count == 7) begin
                            rx_count <= 0;
                            state <= PREPARE;
                        end else
                            rx_count <= rx_count + 1'b1;
                    end
                end
                // The eighth buffer write is visible here. Index zero clears
                // both engines on this clock, before SAMPLE on the next clock.
                PREPARE: state <= SAMPLE;
                SAMPLE: state <= BUILD;
                BUILD: begin
                    if (valid_a && valid_b) begin
                        response_bytes <= {request_bytes[0], request_bytes[1],
                            request_bytes[2],
                            request_bytes[2] == 8'h11 ? action_a : action_b,
                            request_bytes[5],
                            request_bytes[5] == 8'h11 ? action_a : action_b,
                            16'h0000};
                        tx_count <= 0;
                        state <= SEND;
                    end
                end
                SEND: begin
                    if (!tx_busy) begin
                        tx_byte <= response_bytes[63:56];
                        tx_start <= 1'b1;
                        state <= WAIT_DONE;
                    end
                end
                WAIT_DONE: begin
                    if (tx_done) begin
                        if (tx_count == 7)
                            state <= RECEIVE;
                        else begin
                            tx_count <= tx_count + 1'b1;
                            response_bytes <= {response_bytes[55:0], 8'h00};
                            if (TX_GAP_CYCLES == 0)
                                state <= SEND;
                            else begin
                                gap_timer <= TX_GAP_CYCLES - 1;
                                state <= GAP;
                            end
                        end
                    end
                end
                GAP: begin
                    if (gap_timer == 0)
                        state <= SEND;
                    else
                        gap_timer <= gap_timer - 1'b1;
                end
                default: begin
                    state <= RECEIVE;
                    rx_count <= 0;
                end
            endcase
        end
    end
endmodule
