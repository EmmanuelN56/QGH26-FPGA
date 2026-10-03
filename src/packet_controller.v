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
    localparam [2:0] RECEIVE = 0, BUILD = 1, SEND = 2, WAIT_DONE = 3, GAP = 4;
    localparam integer GAP_WIDTH = (TX_GAP_CYCLES > 1) ? $clog2(TX_GAP_CYCLES) : 1;
    reg [2:0] state;
    reg [2:0] rx_count, tx_count;
    reg [7:0] request_bytes [0:7];
    reg [63:0] response_bytes;
    reg [GAP_WIDTH-1:0] gap_timer;

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
                            state <= BUILD;
                        end else
                            rx_count <= rx_count + 1'b1;
                    end
                end
                BUILD: begin
                    // Build on the next clock, after the last buffer write has completed.
                    // This milestone echoes fields and returns NONE; no strategy exists yet.
                    response_bytes <= {request_bytes[0], request_bytes[1],
                                       request_bytes[2], 8'h00,
                                       request_bytes[5], 8'h00, 16'h0000};
                    tx_count <= 0;
                    state <= SEND;
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
