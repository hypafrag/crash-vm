[![Build Status](https://drone.coons.club/api/badges/hypafrag/crash-vm/status.svg)](https://drone.coons.club/hypafrag/crash-vm)

![](doc/simple_architecture.png)

![](doc/simple_cycle.png)

![](doc/simple_instructions.png)

# Reserved interupt codes:

0. Halt
    - Should be raised by a program with `Int` instruction to stop execution
1. InvalidInstruction
    - Raised by CPU when invalid opcode fetched for execution

[comment]: <> (2. Breakpoint)

[comment]: <> (    - Raised by a program with `Int` instruction)
