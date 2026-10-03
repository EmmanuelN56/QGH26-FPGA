`timescale 1ns/1ps
module pair_checked_tb;
    reg clk=0,reset=1,session_clear=0,sample_valid=0,warmup=0,slot1_is_a=0;
    reg [15:0] price1,price2;
    wire [7:0] action1,action2;
    wire action_valid;
    reg [127:0] vectors[0:4095],states[0:4095];
    reg [63:0] request,response;
    reg [127:0] observed;
    integer count,i,cycles,max_cycles=0,min_cycles=100000,which,j,idx;
    reg [8191:0] vector_path,state_path;
    reg [15:0] shadow[0:31];
    integer filled=0,ptr=0;
    reg [19:0] total_check;
    always #5 clk=~clk;
    trade_pair dut(.clk(clk),.reset(reset),.session_clear(session_clear),
        .sample_valid(sample_valid),.warmup(warmup),.slot1_is_a(slot1_is_a),
        .price1(price1),.price2(price2),.action1(action1),.action2(action2),.action_valid(action_valid));
    function [19:0] sum_for;
        input integer item;
        integer k;
        begin
`ifdef DIGIT_MEMORY
            sum_for=0;
            for(k=0;k<(20+dut.W-1)/dut.W;k=k+1) begin
`ifdef DESCENDING_DIGITS
                sum_for=sum_for | (dut.sum_memory[item*dut.DEPTH+dut.BASE+k] << (k*dut.W));
`else
                sum_for=sum_for | (dut.sum_memory[item*dut.DEPTH+k] << (k*dut.W));
`endif
            end
`else
            sum_for=dut.memory[item*32+16];
`endif
        end
    endfunction
    function [15:0] previous_for;
        input integer item;
        integer k;
        begin
`ifdef DIGIT_MEMORY
            previous_for=0;
            for(k=0;k<16/dut.W;k=k+1) begin
`ifdef DESCENDING_DIGITS
                previous_for=previous_for | (dut.previous_memory[item*dut.DEPTH+dut.BASE+k] << (k*dut.W));
`else
                previous_for=previous_for | (dut.previous_memory[item*dut.DEPTH+k] << (k*dut.W));
`endif
            end
`else
            previous_for=dut.memory[item*32+17][15:0];
`endif
        end
    endfunction
    function [15:0] history_for;
        input integer item,sample;
        integer k;
        begin
`ifdef DIGIT_MEMORY
            history_for=0;
            for(k=0;k<16/dut.W;k=k+1) begin
`ifdef DESCENDING_DIGITS
                history_for=history_for | (dut.history_memory[(item*16+sample)*dut.DEPTH+dut.BASE+k] << (k*dut.W));
`else
                history_for=history_for | (dut.history_memory[(item*16+sample)*dut.DEPTH+k] << (k*dut.W));
`endif
            end
`else
            history_for=dut.memory[item*32+sample][15:0];
`endif
        end
    endfunction
    // Check read latency against the value present at the read edge.
    reg [19:0] captured_sum,captured_prev,captured_hist;
    reg check_sum,check_prev,check_hist;
    always @(posedge clk) begin
        check_sum=0;check_prev=0;check_hist=0;
        if(!reset && !session_clear) begin
`ifdef DIGIT_MEMORY
            check_sum=dut.state==dut.READ_OLD || dut.state==dut.READ_NEW || dut.state==dut.READ_SUB || dut.state==dut.READ_ADD || dut.state==10 || dut.state==12;
            check_prev=dut.state==dut.READ_OLD;check_hist=dut.state==dut.READ_SUB;
            if(check_sum) captured_sum=dut.sum_memory[dut.sum_address];
            if(check_prev) captured_prev=dut.previous_memory[dut.previous_address];
            if(check_hist) captured_hist=dut.history_memory[dut.history_address];
`else
            check_sum=dut.mem_read_enable;
            if(check_sum) captured_sum=dut.memory[dut.address];
            if(dut.mem_read_enable && dut.mem_write_enable) $fatal(1,"RAM read/write collision");
`endif
        end
        #1;
`ifdef DIGIT_MEMORY
        if(check_sum && dut.sum_read!==captured_sum) $fatal(1,"sum read latency");
        if(check_prev && dut.previous_read!==captured_prev) $fatal(1,"previous read latency");
        if(check_hist && dut.history_read!==captured_hist) $fatal(1,"history read latency");
`else
        if(check_sum && dut.memory_read!==captured_sum) $fatal(1,"word read latency");
`endif
    end
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
                if(action_valid || dut.sample_count!==0 || dut.write_pointer!==0 || action1!==0 || action2!==0)
                    $fatal(1,"Clear did not win %0d",i);
                session_clear=0;filled=0;ptr=0;
            end
            sample_valid=1;@(negedge clk);sample_valid=0;
            cycles=0;
            while(!action_valid && cycles<1024) begin @(negedge clk);cycles=cycles+1;end
            if(!action_valid||action1!==response[39:32]||action2!==response[23:16])
                $fatal(1,"Pair action mismatch %0d %02x/%02x expected %02x/%02x",i,action1,action2,response[39:32],response[23:16]);
            if(cycles>max_cycles) max_cycles=cycles;if(cycles<min_cycles) min_cycles=cycles;
            observed={4'd0,sum_for(0),4'd0,sum_for(1),previous_for(0),previous_for(1),
                4'd0,dut.write_pointer,4'd0,dut.write_pointer,3'd0,dut.sample_count,3'd0,dut.sample_count,16'd0};
            if(observed!==states[i]) $fatal(1,"Pair state mismatch %0d %032x != %032x",i,observed,states[i]);
            shadow[ptr]=slot1_is_a ? price1 : price2;shadow[16+ptr]=slot1_is_a ? price2 : price1;
            ptr=(ptr+1)%16;if(filled<16) filled=filled+1;
            for(which=0;which<2;which=which+1) begin
                total_check=0;
                for(j=0;j<filled;j=j+1) begin
                    if(history_for(which,j)!==shadow[which*16+j]) $fatal(1,"History mismatch packet %0d item %0d sample %0d",i,which,j);
                    total_check=total_check+shadow[which*16+j];
                end
                if(sum_for(which)!==total_check) $fatal(1,"Sum/history inconsistency %0d",i);
            end
            @(negedge clk);
            if(action_valid) $fatal(1,"Duplicate action_valid");
            if(sum_for(0)!==observed[123:104] || sum_for(1)!==observed[99:80]) $fatal(1,"Unsolicited update");
        end
        // Physical reset masks all existing RAM just like a session clear.
        reset=1;@(negedge clk);reset=0;
        if(dut.sample_count!==0 || dut.write_pointer!==0 || action_valid) $fatal(1,"Physical reset");
        $display("PASS pair_checked_tb: %0d packets, histories, sums, RAM latency, single update/pulse; cycles=%0d..%0d",count,min_cycles,max_cycles);$finish;
    end
    initial begin #1000000000;$fatal(1,"Pair timeout");end
endmodule
