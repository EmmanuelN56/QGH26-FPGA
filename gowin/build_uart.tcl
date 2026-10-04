set flow syn
if {[info exists env(UART_BUILD_FLOW)]} {
    set flow $env(UART_BUILD_FLOW)
}
if {$flow ni {syn pnr all}} {
    error "UART_BUILD_FLOW must be syn, pnr, or all"
}
set repo_root [file normalize [file join [file dirname [info script]] ..]]
set expected_inputs {}
foreach relative {
    src/top.v src/uart_rx.v src/uart_tx.v src/packet_controller.v
    src/trade_engine.v constraints/19_tang_nano_20k.cst gowin/uart.sdc
} {
    lappend expected_inputs [file normalize [file join $repo_root $relative]]
}

proc project_xml_attribute {value} {
    # Decode once: an escaped ampersand must not introduce a second entity.
    set decoded ""
    set offset 0
    while {[regexp -indices -start $offset {&[^;]*;} $value span]} {
        lassign $span first last
        append decoded [string range $value $offset [expr {$first - 1}]]
        set entity [string range $value $first $last]
        switch -- $entity {
            &amp;  {set character &}
            &quot; {set character \"}
            &apos; {set character '}
            &lt;   {set character <}
            &gt;   {set character >}
            default {
                if {[regexp {^&#x([[:xdigit:]]+);$} $entity -> digits]} {
                    scan $digits %x codepoint
                } elseif {[regexp {^&#([0-9]+);$} $entity -> digits]} {
                    scan $digits %d codepoint
                } else {
                    error "Unsupported XML entity in project attribute: $entity"
                }
                if {$codepoint < 1 || $codepoint > 0x10ffff} {
                    error "Invalid XML character reference: $entity"
                }
                set character [format %c $codepoint]
            }
        }
        append decoded $character
        set offset [expr {$last + 1}]
    }
    append decoded [string range $value $offset end]
    return $decoded
}

proc project_path_key {path} {
    set path [file normalize $path]
    if {$::tcl_platform(platform) eq "windows"} {
        set path [string tolower $path]
    }
    return $path
}

proc validate_project_inputs {project_file expected_inputs} {
    set stream [open $project_file r]
    fconfigure $stream -encoding utf-8
    set xml [read $stream]
    close $stream
    regsub -all {(?s)<!--.*?-->} $xml {} xml
    set actual {}
    foreach entry [regexp -all -inline {<File[[:space:]][^>]*>} $xml] {
        set attributes [dict create]
        foreach {match name quoted double_value single_value} [regexp -all -inline \
                {([[:alnum:]_:-]+)[[:space:]]*=[[:space:]]*("([^"]*)"|'([^']*)')} $entry] {
            if {[dict exists $attributes $name]} {
                error "Duplicate project attribute: $name"
            }
            dict set attributes $name [project_xml_attribute [string range $quoted 1 end-1]]
        }
        if {![dict exists $attributes path] || ![dict exists $attributes enable]} {
            error "Project File entry is missing path or enable"
        }
        if {[dict get $attributes enable] ne "1"} {
            error "Project contains a disabled input: [dict get $attributes path]"
        }
        lappend actual [project_path_key [file join [file dirname $project_file] \
                                        [dict get $attributes path]]]
    }
    set expected {}
    foreach path $expected_inputs {
        lappend expected [project_path_key $path]
    }
    if {[llength $actual] != [llength $expected] ||
        [llength [lsort -unique $actual]] != [llength $actual] ||
        [lsort $actual] ne [lsort $expected]} {
        error "Project input paths differ from this checkout's seven build inputs"
    }
}

set build_dir [file join $repo_root .build gowin_trade]
file mkdir $build_dir
cd $build_dir

set project_file [file join $build_dir trade_core trade_core.gprj]
if {[file exists $project_file]} {
    if {[catch {validate_project_inputs $project_file $expected_inputs} reason]} {
        error "Cached Gowin project rejected: $reason. Use a fresh native Windows directory with src/, constraints/, and gowin/; do not copy .build/. Existing caches were not deleted."
    }
    open_project $project_file
} else {
    create_project -name trade_core -dir $build_dir -pn GW2AR-LV18QN88C8/I7 -device_version C
    foreach path $expected_inputs {
        add_file $path
    }
}
set_device -device_version C GW2AR-LV18QN88C8/I7
set_option -top_module top
set_option -output_base_name trade_core
set_option -global_freq 27
run $flow
