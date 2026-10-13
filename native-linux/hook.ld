ENTRY(entry)
SECTIONS { . = 0; .text : { *(.text.entry) *(.text*) } .data : { *(.data.context) *(.data*) } /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) } }
