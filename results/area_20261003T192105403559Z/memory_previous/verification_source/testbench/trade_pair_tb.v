`timescale 1ns/1ps
module trade_pair_tb;
    reg clk=0,reset=1,session_clear=0,sample_valid=0,warmup=0,slot1_is_a=0;
    reg [15:0] price1,price2;
    wire [7:0] action1,action2;
    wire action_valid;
    wire [3:0] previous_pointer=dut.write_pointer-4'd1;
    reg [127:0] vectors[0:4095],states[0:4095];
    reg [63:0] request,response;
    reg [127:0] observed;
    integer count,i,cycles;
    reg [1023:0] vector_path,state_path;
    always #5 clk=~clk;
    trade_pair dut(.clk(clk),.reset(reset),.session_clear(session_clear),
        .sample_valid(sample_valid),.warmup(warmup),.slot1_is_a(slot1_is_a),
        .price1(price1),.price2(price2),.action1(action1),.action2(action2),.action_valid(action_valid));
    initial begin
        if(!$value$plusargs("COUNT=%d",count)||count<1||count>4096||
           !$value$plusargs("VECTORS=%s",vector_path)||!$value$plusargs("STATES=%s",state_path))
            $fatal(1,"Missing vectors");
        $readmemh(vector_path,vectors,0,count-1);$readmemh(state_path,states,0,count-1);
        repeat(3) @(negedge clk);reset=0;
        for(i=0;i<count;i=i+1) begin
            request=vectors[i][127:64];response=vectors[i][63:0];
            warmup=request[63:48]<16;slot1_is_a=request[47:40]==8'h11;
            price1=request[39:24];price2=request[15:0];
            if(request[63:48]==0) begin
                session_clear=1;sample_valid=1;@(negedge clk);
                if(action_valid||dut.sums[0]!==0||dut.sums[1]!==0||action1!==0||action2!==0)
                    $fatal(1,"Clear did not win %0d",i);
                session_clear=0;
            end
            sample_valid=1;@(negedge clk);sample_valid=0;
            cycles=0;
            while(!action_valid && cycles<100) begin @(negedge clk);cycles=cycles+1;end
            if(!action_valid||action1!==response[39:32]||action2!==response[23:16])
                $fatal(1,"Pair action mismatch %0d %02x/%02x expected %02x/%02x",i,action1,action2,response[39:32],response[23:16]);
            observed={4'd0,dut.sums[0],4'd0,dut.sums[1],dut.prices[{1'b0,previous_pointer}],dut.prices[{1'b1,previous_pointer}],
                4'd0,dut.write_pointer,4'd0,dut.write_pointer,3'd0,dut.sample_count,3'd0,dut.sample_count,16'd0};
            if(observed!==states[i]) $fatal(1,"Pair state mismatch %0d %032x != %032x",i,observed,states[i]);
            @(negedge clk);
            if(action_valid) $fatal(1,"Duplicate action_valid");
            if(dut.sums[0]!==observed[123:104]||dut.sums[1]!==observed[99:80]) $fatal(1,"Unsolicited update");
        end
        $display("PASS trade_pair_tb: %0d packets, both item states, clear priority, valid pulse",count);$finish;
    end
    initial begin #100000000;$fatal(1,"Pair timeout");end
endmodule
