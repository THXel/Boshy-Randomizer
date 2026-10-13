.section .text.entry,"ax"
.global entry
entry:
 pushfl
 pushal
 call 1f
1:
 popl %eax
 leal (ini_entry-1b)(%eax),%edx
 addl $(context-1b),%eax
 pushl %edx
 pushl %eax
 call tick
 addl $8,%esp
 popal
 popfl
 pushl %ecx
 movl 0x459a94,%eax
 pushl $0x4365a6
 ret
ini_entry:
 movl 4(%esp),%edx
 call 2f
2:
 popl %eax
 addl $(context-2b),%eax
 pushl %edx
 pushl %eax
 call dispatch
 addl $8,%esp
 ret
.section .data.context,"aw"
.balign 4
.global context
context:
.incbin "slot_reward_context.bin"
.section .note.GNU-stack,"",@progbits
