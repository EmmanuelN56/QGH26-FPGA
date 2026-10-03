from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,sys
root=Path.cwd();sys.path.insert(0,str(root/'scripts'))
from capture_vector_stress import validate_inputs
summary=root/'results/release_zero_gap_20261003T180901633856Z/build_summary.json'
source=validate_inputs(root/'bitstream/trade_core.fs',summary,root)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out=root/'results'/('area_'+stamp);out.mkdir()
(root/'.build/current_area_path.txt').write_text(out.relative_to(root).as_posix(),encoding='utf-8')
for name in source:
    dest=out/'baseline/source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,dest)
shutil.copyfile(summary,out/'baseline/build_summary.json')
shutil.copyfile(root/'bitstream/trade_core.fs',out/'baseline/programmed.fs')
shutil.copytree(root/'results/regrade_20261003T183908493740Z',out/'baseline/latest_regrade',ignore=shutil.ignore_patterns('test_sources','*.py','*.log','participant_guide_text.txt','organizer_current.md','*.md'))
context={'scope':'Isolated area research; no board programming or release promotion','baseline_luts':365,'baseline_registers':296,'baseline_bsram':0,'baseline_ssram':8,'release_sha256':hashlib.sha256((root/'bitstream/trade_core.fs').read_bytes()).hexdigest(),'baseline_source_sha256':source,'native_root':'C:/Users/Lenovo/AppData/Local/GatorFPGA/area_'+stamp,'physical_validation':False,'candidate_physical_latency':None,'status':'running'}
(out/'context.json').write_text(json.dumps(context,indent=2)+'\n',encoding='utf-8',newline='\n')
print(out)
'@ | & 'C:/Users/Lenovo/AppData/Local/GatorFPGA/python_env/bin/python.exe' -B -
$areaDir = Get-Content .build/current_area_path.txt -Raw
New-Item -ItemType Directory -Path (Join-Path $areaDir prototypes) | Out-Null
@'
module packet_controller #(
    parameter integer TX_GAP_CYCLES = 27000
) (
    input wire clk, reset,
    input wire [7:0] rx_byte,
    input wire rx_valid, framing_error,
    output wire [7:0] tx_byte,
    output reg tx_start,
    input wire tx_busy, tx_done
);
    localparam [2:0] RECEIVE=0, PREPARE=1, SAMPLE=2, BUILD=3,
                     SEND=4, WAIT_DONE=5, GAP=6;
    localparam integer GAP_WIDTH=(TX_GAP_CYCLES>1)?$clog2(TX_GAP_CYCLES):1;
    reg [2:0] state, rx_count, tx_count;
    reg [63:0] packet;
    reg [GAP_WIDTH-1:0] gap_timer;
    wire [15:0] index=packet[63:48];
    wire session_clear=state==PREPARE && index==0;
    wire sample_valid=state==SAMPLE;
    wire warmup=index<16;
    wire [15:0] price_a=packet[47:40]==8'h11?packet[39:24]:packet[15:0];
    wire [15:0] price_b=packet[47:40]==8'h22?packet[39:24]:packet[15:0];
    wire [7:0] action_a,action_b;
    wire valid_a,valid_b;
    assign tx_byte=packet[63:56];
    trade_engine engine_a(.clk(clk),.reset(reset),.session_clear(session_clear),
        .sample_valid(sample_valid),.price(price_a),.warmup(warmup),
        .action(action_a),.action_valid(valid_a));
    trade_engine engine_b(.clk(clk),.reset(reset),.session_clear(session_clear),
        .sample_valid(sample_valid),.price(price_b),.warmup(warmup),
        .action(action_b),.action_valid(valid_b));
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
                BUILD:if(valid_a&&valid_b) begin
                    packet<={packet[63:40],packet[47:40]==8'h11?action_a:action_b,
                             packet[23:16],packet[23:16]==8'h11?action_a:action_b,16'h0000};
                    tx_count<=0;state<=SEND;
                end
                SEND:if(!tx_busy) begin tx_start<=1;state<=WAIT_DONE;end
                WAIT_DONE:if(tx_done) begin
                    if(tx_count==7) state<=RECEIVE;
                    else begin
                        tx_count<=tx_count+1'b1;
                        packet<={packet[55:0],8'h00};
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
