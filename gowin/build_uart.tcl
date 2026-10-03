set flow syn
if {[info exists env(UART_BUILD_FLOW)]} {
    set flow $env(UART_BUILD_FLOW)
}
if {$flow ni {syn pnr all}} {
    error "UART_BUILD_FLOW must be syn, pnr, or all"
}
set repo_root [file normalize [file join [file dirname [info script]] ..]]
set build_dir [file join $repo_root .build gowin_uart]
file mkdir $build_dir
cd $build_dir

set project_file [file join $build_dir uart_milestone uart_milestone.gprj]
if {[file exists $project_file]} {
    open_project $project_file
} else {
    create_project -name uart_milestone -dir $build_dir -pn GW2AR-LV18QN88C8/I7 -device_version C
    add_file [file join $repo_root src top.v]
    add_file [file join $repo_root src uart_rx.v]
    add_file [file join $repo_root src uart_tx.v]
    add_file [file join $repo_root src packet_controller.v]
    add_file [file join $repo_root constraints 19_tang_nano_20k.cst]
    add_file [file join $repo_root gowin uart.sdc]
}
set_device -device_version C GW2AR-LV18QN88C8/I7
set_option -top_module top
set_option -output_base_name uart_milestone
set_option -global_freq 27
run $flow
