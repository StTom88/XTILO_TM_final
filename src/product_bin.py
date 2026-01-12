from __future__ import annotations

from typing import Dict, Tuple, Set, Optional, List

from .tm import MultiTapeTM, Transition

BLANK = "#"

# Internal alphabet:
# L : left boundary marker for unary blocks and OUT workspace
# X,Y : internal markers during bin2unary conversion

ALPHABET: Set[str] = set("#01LXY")

def build_tm(stop_after: str = "D") -> MultiTapeTM:

    stop_after = stop_after.upper()
    if stop_after not in {"A", "B", "C", "D"}:
        raise ValueError("stop_after must be A/B/C/D")

    states: Set[str] = set()
    accept_states: Set[str] = {"ACCEPT_A", "ACCEPT_B", "ACCEPT_C", "ACCEPT_D"}
    reject_states: Set[str] = {"REJECT"}
    start_state = "qSTART"

    T: Dict[Tuple[str, Tuple[str, ...]], Transition] = {}

    syms = tuple(sorted(ALPHABET))
    all_reads = [(a, b, c, d, e) for a in syms for b in syms for c in syms for d in syms for e in syms]

    # Helper to add transition
    def add(state: str, read: Tuple[str, ...], next_state: str,
            write: Tuple[Optional[str], ...], move: Tuple[str, ...]) -> None:
        key = (state, read)
        if key in T:
            raise ValueError(f"Duplicate transition for {key}")
        write_full = tuple((read[i] if write[i] is None else write[i]) for i in range(5))
        T[key] = Transition(next_state, write_full, move)

    # Helper to add reject catchall for a state
    def reject_catchall(state: str) -> None:
        for r in all_reads:
            if (state, r) not in T:
                add(state, r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    
    # Emit bin2unary conversion subroutine
    def emit_bin2unary(prefix: str, done_next: str) -> None:
        local_states = {
            f"{prefix}BIT",
            f"{prefix}DOUBLE_SEEK", f"{prefix}DOUBLE_MARK", f"{prefix}DOUBLE_TO_END",
            f"{prefix}DOUBLE_APPEND", f"{prefix}DOUBLE_BACK_TO_L",
            f"{prefix}RESTORE_BACK_TO_L", f"{prefix}RESTORE",
            f"{prefix}ADD1_BACK_TO_L", f"{prefix}ADD1_TO_END", f"{prefix}ADD1_WRITE", f"{prefix}ADD1_BACK_TO_L_2",
            f"{prefix}ADVANCE_IN",
            f"{prefix}DONE",
        }
        states.update(local_states)

        # BIT
        for r in all_reads:
            a, b, c, d, e = r
            if a == "#":
                add(f"{prefix}BIT", r, f"{prefix}DONE", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            elif a in "01":
                add(f"{prefix}BIT", r, f"{prefix}DOUBLE_SEEK", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            else:
                add(f"{prefix}BIT", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # DOUBLE_SEEK: find next original 1; stop at end
        for r in all_reads:
            a, b, c, d, e = r
            if c == "L":
                add(f"{prefix}DOUBLE_SEEK", r, f"{prefix}DOUBLE_SEEK", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            elif c == "1":
                add(f"{prefix}DOUBLE_SEEK", r, f"{prefix}DOUBLE_MARK", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            elif c in {"X", "Y"}:
                add(f"{prefix}DOUBLE_SEEK", r, f"{prefix}DOUBLE_SEEK", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            elif c == "#":
                add(f"{prefix}DOUBLE_SEEK", r, f"{prefix}RESTORE_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))
            else:
                add(f"{prefix}DOUBLE_SEEK", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # DOUBLE_MARK
        for r in all_reads:
            a, b, c, d, e = r
            if c == "1":
                add(f"{prefix}DOUBLE_MARK", r, f"{prefix}DOUBLE_TO_END", (None, None, "X", None, None), ("S", "S", "R", "S", "S"))
            else:
                add(f"{prefix}DOUBLE_MARK", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # DOUBLE_TO_END
        for r in all_reads:
            a, b, c, d, e = r
            if c in {"1", "X", "Y"}:
                add(f"{prefix}DOUBLE_TO_END", r, f"{prefix}DOUBLE_TO_END", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            elif c == "#":
                add(f"{prefix}DOUBLE_TO_END", r, f"{prefix}DOUBLE_APPEND", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            else:
                add(f"{prefix}DOUBLE_TO_END", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # DOUBLE_APPEND: append Y at end
        for r in all_reads:
            a, b, c, d, e = r
            if c == "#":
                add(f"{prefix}DOUBLE_APPEND", r, f"{prefix}DOUBLE_BACK_TO_L", (None, None, "Y", None, None), ("S", "S", "L", "S", "S"))
            else:
                add(f"{prefix}DOUBLE_APPEND", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # DOUBLE_BACK_TO_L
        for r in all_reads:
            a, b, c, d, e = r
            if c == "L":
                add(f"{prefix}DOUBLE_BACK_TO_L", r, f"{prefix}DOUBLE_SEEK", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            else:
                add(f"{prefix}DOUBLE_BACK_TO_L", r, f"{prefix}DOUBLE_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))

        # RESTORE_BACK_TO_L then RESTORE X/Y -> 1
        for r in all_reads:
            a, b, c, d, e = r
            if c == "L":
                add(f"{prefix}RESTORE_BACK_TO_L", r, f"{prefix}RESTORE", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            else:
                add(f"{prefix}RESTORE_BACK_TO_L", r, f"{prefix}RESTORE_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))

        # RESTORE
        for r in all_reads:
            a, b, c, d, e = r
            if c in {"X", "Y"}:
                add(f"{prefix}RESTORE", r, f"{prefix}RESTORE", (None, None, "1", None, None), ("S", "S", "R", "S", "S"))
            elif c == "1":
                add(f"{prefix}RESTORE", r, f"{prefix}RESTORE", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            elif c == "#":
                add(f"{prefix}RESTORE", r, f"{prefix}ADD1_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))
            elif c == "L":
                add(f"{prefix}RESTORE", r, f"{prefix}RESTORE", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            else:
                add(f"{prefix}RESTORE", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # ADD1_BACK_TO_L: decide based on current input bit
        for r in all_reads:
            a, b, c, d, e = r
            if c == "L":
                if a == "1":
                    add(f"{prefix}ADD1_BACK_TO_L", r, f"{prefix}ADD1_TO_END", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
                elif a == "0":
                    add(f"{prefix}ADD1_BACK_TO_L", r, f"{prefix}ADVANCE_IN", (None, None, None, None, None), ("R", "S", "S", "S", "S"))
                else:
                    add(f"{prefix}ADD1_BACK_TO_L", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            else:
                add(f"{prefix}ADD1_BACK_TO_L", r, f"{prefix}ADD1_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))

        # ADD1_TO_END
        for r in all_reads:
            a, b, c, d, e = r
            if c == "1":
                add(f"{prefix}ADD1_TO_END", r, f"{prefix}ADD1_TO_END", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            elif c == "#":
                add(f"{prefix}ADD1_TO_END", r, f"{prefix}ADD1_WRITE", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            elif c == "L":
                add(f"{prefix}ADD1_TO_END", r, f"{prefix}ADD1_TO_END", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
            else:
                add(f"{prefix}ADD1_TO_END", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # ADD1_WRITE
        for r in all_reads:
            a, b, c, d, e = r
            if c == "#":
                add(f"{prefix}ADD1_WRITE", r, f"{prefix}ADD1_BACK_TO_L_2", (None, None, "1", None, None), ("S", "S", "L", "S", "S"))
            else:
                add(f"{prefix}ADD1_WRITE", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # ADD1_BACK_TO_L_2
        for r in all_reads:
            a, b, c, d, e = r
            if c == "L":
                add(f"{prefix}ADD1_BACK_TO_L_2", r, f"{prefix}ADVANCE_IN", (None, None, None, None, None), ("R", "S", "S", "S", "S"))
            else:
                add(f"{prefix}ADD1_BACK_TO_L_2", r, f"{prefix}ADD1_BACK_TO_L_2", (None, None, None, None, None), ("S", "S", "L", "S", "S"))

        # ADVANCE_IN
        for r in all_reads:
            a, b, c, d, e = r
            if a in "01":
                add(f"{prefix}ADVANCE_IN", r, f"{prefix}BIT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            elif a == "#":
                add(f"{prefix}ADVANCE_IN", r, f"{prefix}DONE", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            else:
                add(f"{prefix}ADVANCE_IN", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

        # DONE
        for r in all_reads:
            add(f"{prefix}DONE", r, done_next, (None, None, None, None, None), ("S", "S", "S", "S", "S"))


    # Init markers and position at first digit
    states |= {"qSTART", "qA_FIND_FIRST", "qA_DONE"}
    for r in all_reads:
        a, b, c, d, e = r
        if a != "#":
            add("qSTART", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
            continue
        w_acc = "L" if b == "#" else b
        w_fac = "L" if c == "#" else c
        w_scr = "L" if d == "#" else d
        w_out = "L" if e == "#" else e
        add("qSTART", r, "qA_FIND_FIRST", (None, w_acc, w_fac, w_scr, w_out), ("R", "S", "S", "S", "S"))

    for r in all_reads:
        a, b, c, d, e = r
        if a in "01":
            add("qA_FIND_FIRST", r, "qA_DONE" if stop_after == "A" else "qB1_BIT",
                (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qA_FIND_FIRST", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    for r in all_reads:
        add("qA_DONE", r, "ACCEPT_A", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

  
    # Convert first number to FAC
    if stop_after == "B":
        emit_bin2unary("qB1_", "ACCEPT_B")
    else:
        emit_bin2unary("qB1_", "qC_INIT_ACC_CLEAR")

    # Multiply all numbers in unary (ACC holds product)
    states |= {
        "qC_INIT_ACC_CLEAR", "qC_INIT_ACC_CLEAR_RIGHT", "qC_INIT_ACC_BACK_TO_L",
        "qC_INIT_COPY_FAC_TO_ACC", "qC_INIT_COPY_FAC_TO_ACC_DONE",
        "qC_CHECK_MORE", "qC_CHECK_MORE_2",
        "qC_CLEAR_FAC_TO_L", "qC_CLEAR_FAC_ERASE_RIGHT", "qC_CLEAR_FAC_BACK_TO_L",
        "qC_DONE",

        # multiplication
        "qM_CLEAR_SCR_RIGHT", "qM_CLEAR_SCR_BACK_TO_L",
        "qM_FAC_TO_FIRST", "qM_FAC_SEEK", "qM_FAC_MARK",
        "qM_SCR_TO_END",
        "qM_ACC_TO_FIRST", "qM_COPY_ACC_TO_SCR", "qM_ACC_BACK_TO_L",
        "qM_FAC_ADVANCE",
        "qM_RESTORE_FAC_BACK_TO_L", "qM_RESTORE_FAC",
        "qM_PREP_ACC_CLEAR", "qM_PREP_ACC_BACK",
        "qM_COPY_SCR_TO_ACC", "qM_COPY_SCR_TO_ACC_DO",
        "qM_FINISH_CLEAR_SCR", "qM_FINISH_CLEAR_SCR_RIGHT",
    }

    # Clear ACC
    for r in all_reads:
        a, b, c, d, e = r
        if b == "L":
            add("qC_INIT_ACC_CLEAR", r, "qC_INIT_ACC_CLEAR_RIGHT", (None, None, None, None, None), ("S", "R", "S", "S", "S"))
        else:
            add("qC_INIT_ACC_CLEAR", r, "qC_INIT_ACC_CLEAR", (None, None, None, None, None), ("S", "L", "S", "S", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if b == "#":
            add("qC_INIT_ACC_CLEAR_RIGHT", r, "qC_INIT_ACC_BACK_TO_L", (None, None, None, None, None), ("S", "L", "S", "S", "S"))
        else:
            add("qC_INIT_ACC_CLEAR_RIGHT", r, "qC_INIT_ACC_CLEAR_RIGHT", (None, "#", None, None, None), ("S", "R", "S", "S", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if b == "L":
            add("qC_INIT_ACC_BACK_TO_L", r, "qC_INIT_COPY_FAC_TO_ACC", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qC_INIT_ACC_BACK_TO_L", r, "qC_INIT_ACC_BACK_TO_L", (None, None, None, None, None), ("S", "L", "S", "S", "S"))

    # Copy FAC->ACC
    for r in all_reads:
        a, b, c, d, e = r
        if b == "L" and c == "L":
            add("qC_INIT_COPY_FAC_TO_ACC", r, "qC_INIT_COPY_FAC_TO_ACC", (None, None, None, None, None), ("S", "R", "R", "S", "S"))
        elif c == "1":
            add("qC_INIT_COPY_FAC_TO_ACC", r, "qC_INIT_COPY_FAC_TO_ACC", (None, "1", None, None, None), ("S", "R", "R", "S", "S"))
        elif c == "#":
            add("qC_INIT_COPY_FAC_TO_ACC", r, "qC_INIT_COPY_FAC_TO_ACC_DONE", (None, None, None, None, None), ("S", "L", "L", "S", "S"))
        else:
            add("qC_INIT_COPY_FAC_TO_ACC", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if b == "L" and c == "L":
            add("qC_INIT_COPY_FAC_TO_ACC_DONE", r, "qC_CHECK_MORE", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qC_INIT_COPY_FAC_TO_ACC_DONE", r, "qC_INIT_COPY_FAC_TO_ACC_DONE", (None, None, None, None, None), ("S", "L", "L", "S", "S"))

    # Check for more numbers: IN at '#'
    for r in all_reads:
        a, b, c, d, e = r
        if a == "#":
            add("qC_CHECK_MORE", r, "qC_CHECK_MORE_2", (None, None, None, None, None), ("R", "S", "S", "S", "S"))
        else:
            add("qC_CHECK_MORE", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    for r in all_reads:
        a, b, c, d, e = r
        if a == "#":
            add("qC_CHECK_MORE_2", r, "qC_DONE", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        elif a in "01":
            add("qC_CHECK_MORE_2", r, "qC_CLEAR_FAC_TO_L", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qC_CHECK_MORE_2", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    # Clear FAC for next number
    for r in all_reads:
        a, b, c, d, e = r
        if c == "L":
            add("qC_CLEAR_FAC_TO_L", r, "qC_CLEAR_FAC_ERASE_RIGHT", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
        else:
            add("qC_CLEAR_FAC_TO_L", r, "qC_CLEAR_FAC_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if c == "#":
            add("qC_CLEAR_FAC_ERASE_RIGHT", r, "qC_CLEAR_FAC_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))
        else:
            add("qC_CLEAR_FAC_ERASE_RIGHT", r, "qC_CLEAR_FAC_ERASE_RIGHT", (None, None, "#", None, None), ("S", "S", "R", "S", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if c == "L":
            add("qC_CLEAR_FAC_BACK_TO_L", r, "qB2_BIT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qC_CLEAR_FAC_BACK_TO_L", r, "qC_CLEAR_FAC_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))

    # Convert next factor into FAC, then multiply
    emit_bin2unary("qB2_", "qM_CLEAR_SCR_RIGHT")

    # Clear SCR
    for r in all_reads:
        a, b, c, d, e = r
        if d == "L":
            add("qM_CLEAR_SCR_RIGHT", r, "qM_CLEAR_SCR_RIGHT", (None, None, None, None, None), ("S", "S", "S", "R", "S"))
        elif d == "#":
            add("qM_CLEAR_SCR_RIGHT", r, "qM_CLEAR_SCR_BACK_TO_L", (None, None, None, None, None), ("S", "S", "S", "L", "S"))
        else:
            add("qM_CLEAR_SCR_RIGHT", r, "qM_CLEAR_SCR_RIGHT", (None, None, None, "#", None), ("S", "S", "S", "R", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if d == "L":
            add("qM_CLEAR_SCR_BACK_TO_L", r, "qM_FAC_TO_FIRST", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qM_CLEAR_SCR_BACK_TO_L", r, "qM_CLEAR_SCR_BACK_TO_L", (None, None, None, None, None), ("S", "S", "S", "L", "S"))

    # FAC to first
    for r in all_reads:
        a, b, c, d, e = r
        if c == "L":
            add("qM_FAC_TO_FIRST", r, "qM_FAC_SEEK", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
        else:
            add("qM_FAC_TO_FIRST", r, "qM_FAC_TO_FIRST", (None, None, None, None, None), ("S", "S", "L", "S", "S"))

    # seek unmarked 1 in FAC
    for r in all_reads:
        a, b, c, d, e = r
        if c == "1":
            add("qM_FAC_SEEK", r, "qM_FAC_MARK", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        elif c == "X":
            add("qM_FAC_SEEK", r, "qM_FAC_SEEK", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
        elif c == "#":
            add("qM_FAC_SEEK", r, "qM_RESTORE_FAC_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))
        else:
            add("qM_FAC_SEEK", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    # mark 1 -> X
    for r in all_reads:
        a, b, c, d, e = r
        if c == "1":
            add("qM_FAC_MARK", r, "qM_SCR_TO_END", (None, None, "X", None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qM_FAC_MARK", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    # SCR to end
    for r in all_reads:
        a, b, c, d, e = r
        if d in {"L", "1"}:
            add("qM_SCR_TO_END", r, "qM_SCR_TO_END", (None, None, None, None, None), ("S", "S", "S", "R", "S"))
        elif d == "#":
            add("qM_SCR_TO_END", r, "qM_ACC_TO_FIRST", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qM_SCR_TO_END", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    # ACC to first
    for r in all_reads:
        a, b, c, d, e = r
        if b == "L":
            add("qM_ACC_TO_FIRST", r, "qM_COPY_ACC_TO_SCR", (None, None, None, None, None), ("S", "R", "S", "S", "S"))
        else:
            add("qM_ACC_TO_FIRST", r, "qM_ACC_TO_FIRST", (None, None, None, None, None), ("S", "L", "S", "S", "S"))

    # copy ACC to SCR (append)
    for r in all_reads:
        a, b, c, d, e = r
        if b == "1" and d == "#":
            add("qM_COPY_ACC_TO_SCR", r, "qM_COPY_ACC_TO_SCR", (None, None, None, "1", None), ("S", "R", "S", "R", "S"))
        elif b == "1" and d == "1":
            add("qM_COPY_ACC_TO_SCR", r, "qM_COPY_ACC_TO_SCR", (None, None, None, None, None), ("S", "R", "S", "R", "S"))
        elif b == "#":
            add("qM_COPY_ACC_TO_SCR", r, "qM_ACC_BACK_TO_L", (None, None, None, None, None), ("S", "L", "S", "S", "S"))
        elif b == "L":
            add("qM_COPY_ACC_TO_SCR", r, "qM_COPY_ACC_TO_SCR", (None, None, None, None, None), ("S", "R", "S", "S", "S"))
        else:
            add("qM_COPY_ACC_TO_SCR", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    # ACC back to L
    for r in all_reads:
        a, b, c, d, e = r
        if b == "L":
            add("qM_ACC_BACK_TO_L", r, "qM_FAC_ADVANCE", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qM_ACC_BACK_TO_L", r, "qM_ACC_BACK_TO_L", (None, None, None, None, None), ("S", "L", "S", "S", "S"))

    # advance FAC head
    for r in all_reads:
        add("qM_FAC_ADVANCE", r, "qM_FAC_SEEK", (None, None, None, None, None), ("S", "S", "R", "S", "S"))

    # restore FAC markers back to 1
    for r in all_reads:
        a, b, c, d, e = r
        if c == "L":
            add("qM_RESTORE_FAC_BACK_TO_L", r, "qM_RESTORE_FAC", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
        else:
            add("qM_RESTORE_FAC_BACK_TO_L", r, "qM_RESTORE_FAC_BACK_TO_L", (None, None, None, None, None), ("S", "S", "L", "S", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if c == "X":
            add("qM_RESTORE_FAC", r, "qM_RESTORE_FAC", (None, None, "1", None, None), ("S", "S", "R", "S", "S"))
        elif c == "1":
            add("qM_RESTORE_FAC", r, "qM_RESTORE_FAC", (None, None, None, None, None), ("S", "S", "R", "S", "S"))
        elif c == "#":
            add("qM_RESTORE_FAC", r, "qM_PREP_ACC_CLEAR", (None, None, None, None, None), ("S", "S", "S", "S", "S"))
        else:
            add("qM_RESTORE_FAC", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    # clear ACC
    for r in all_reads:
        a, b, c, d, e = r
        if b == "L":
            add("qM_PREP_ACC_CLEAR", r, "qM_PREP_ACC_CLEAR", (None, None, None, None, None), ("S", "R", "S", "S", "S"))
        elif b == "#":
            add("qM_PREP_ACC_CLEAR", r, "qM_PREP_ACC_BACK", (None, None, None, None, None), ("S", "L", "S", "S", "S"))
        else:
            add("qM_PREP_ACC_CLEAR", r, "qM_PREP_ACC_CLEAR", (None, "#", None, None, None), ("S", "R", "S", "S", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if b == "L":
            add("qM_PREP_ACC_BACK", r, "qM_COPY_SCR_TO_ACC", (None, None, None, None, None), ("S", "R", "S", "S", "S"))
        else:
            add("qM_PREP_ACC_BACK", r, "qM_PREP_ACC_BACK", (None, None, None, None, None), ("S", "L", "S", "S", "S"))

    # copy SCR->ACC
    for r in all_reads:
        a, b, c, d, e = r
        if d == "L":
            add("qM_COPY_SCR_TO_ACC", r, "qM_COPY_SCR_TO_ACC_DO", (None, None, None, None, None), ("S", "S", "S", "R", "S"))
        else:
            add("qM_COPY_SCR_TO_ACC", r, "qM_COPY_SCR_TO_ACC", (None, None, None, None, None), ("S", "S", "S", "L", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if d == "1":
            add("qM_COPY_SCR_TO_ACC_DO", r, "qM_COPY_SCR_TO_ACC_DO", (None, "1", None, None, None), ("S", "R", "S", "R", "S"))
        elif d == "#":
            add("qM_COPY_SCR_TO_ACC_DO", r, "qM_FINISH_CLEAR_SCR", (None, None, None, None, None), ("S", "L", "S", "L", "S"))
        else:
            add("qM_COPY_SCR_TO_ACC_DO", r, "REJECT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))

    # clear SCR after copy
    for r in all_reads:
        a, b, c, d, e = r
        if b != "L":
            add("qM_FINISH_CLEAR_SCR", r, "qM_FINISH_CLEAR_SCR", (None, None, None, None, None), ("S", "L", "S", "S", "S"))
        elif d == "L":
            add("qM_FINISH_CLEAR_SCR", r, "qM_FINISH_CLEAR_SCR_RIGHT", (None, None, None, None, None), ("S", "S", "S", "R", "S"))
        else:
            add("qM_FINISH_CLEAR_SCR", r, "qM_FINISH_CLEAR_SCR", (None, None, None, None, None), ("S", "S", "S", "L", "S"))
    for r in all_reads:
        a, b, c, d, e = r
        if d == "#":
            add("qM_FINISH_CLEAR_SCR_RIGHT", r, "qC_CHECK_MORE", (None, None, None, None, None), ("S", "S", "S", "L", "S"))
        else:
            add("qM_FINISH_CLEAR_SCR_RIGHT", r, "qM_FINISH_CLEAR_SCR_RIGHT", (None, None, None, "#", None), ("S", "S", "S", "R", "S"))

    # Done with multiplication, go to DONE or next number
    for r in all_reads:
        add("qC_DONE", r, "ACCEPT_C" if stop_after == "C" else "qD_INIT", (None, None, None, None, None), ("S", "S", "S", "S", "S"))


    # Unary ACC -> binary OUT (MSB first)
    states |= {
        "qD_INIT",
        "qD_OUT_TO_END",
        "qD_ACC_TO_L", "qD_ACC_CHECK_EMPTY",
        "qD_OUT_CHECK_EMPTY_LEFT",
        "qD_WRITE_ZERO_AND_FINISH",

        # one division round
        "qD_CLEAR_FAC_TO_L", "qD_CLEAR_FAC_ERASE_RIGHT", "qD_CLEAR_FAC_BACK_TO_L",
        "qD_SCAN_FIRST", "qD_SCAN_SECOND",
        "qD_FAC_APPEND_TO_L", "qD_FAC_APPEND_TO_END", "qD_FAC_APPEND_WRITE", "qD_FAC_APPEND_BACK_TO_L",
        "qD_WRITE_REM0", "qD_WRITE_REM1",
        "qD_CLEAR_ACC_TO_L", "qD_CLEAR_ACC_ERASE_RIGHT", "qD_CLEAR_ACC_BACK_TO_L",
        "qD_COPY_FAC_TO_ACC_START", "qD_COPY_FAC_TO_ACC", "qD_COPY_FAC_TO_ACC_DONE",
        "qD_CLEAR_FAC2_TO_L", "qD_CLEAR_FAC2_ERASE_RIGHT", "qD_CLEAR_FAC2_BACK_TO_L",
        "qD_NEXT_ROUND",

        # reverse LSB->MSB using SCR
        "qD_REV_CLEAR_SCR_TO_L", "qD_REV_CLEAR_SCR_ERASE_RIGHT", "qD_REV_CLEAR_SCR_BACK_TO_L",
        "qD_REV_OUT_TO_LASTBIT",
        "qD_REV_LOOP",
        "qD_REV_SCR_TO_L",
        "qD_REV_OUT_TO_START",
        "qD_REV_COPYBACK",
        "qD_ERASE_OUT_L",
    }

    # qD_INIT: ensure OUT head at L then go to end (first blank after bits)
    for r in all_reads:
        a,b,c,d,e = r
        if e == "L":
            add("qD_INIT", r, "qD_OUT_TO_END", (None,None,None,None,None), ("S","S","S","S","R"))
        else:
            add("qD_INIT", r, "qD_INIT", (None,None,None,None,None), ("S","S","S","S","L"))
    for r in all_reads:
        a,b,c,d,e = r
        if e in {"0","1"}:
            add("qD_OUT_TO_END", r, "qD_OUT_TO_END", (None,None,None,None,None), ("S","S","S","S","R"))
        elif e == "#":
            add("qD_OUT_TO_END", r, "qD_ACC_TO_L", (None,None,None,None,None), ("S","S","S","S","S"))
        elif e == "L":
            add("qD_OUT_TO_END", r, "qD_OUT_TO_END", (None,None,None,None,None), ("S","S","S","S","R"))
        else:
            add("qD_OUT_TO_END", r, "REJECT", (None,None,None,None,None), ("S","S","S","S","S"))

    # Move ACC to L and check empty
    for r in all_reads:
        a,b,c,d,e = r
        if b == "L":
            add("qD_ACC_TO_L", r, "qD_ACC_CHECK_EMPTY", (None,None,None,None,None), ("S","R","S","S","S"))
        else:
            add("qD_ACC_TO_L", r, "qD_ACC_TO_L", (None,None,None,None,None), ("S","L","S","S","S"))
    # Check if ACC is empty
    for r in all_reads:
        a,b,c,d,e = r
        if b == "#":
            add("qD_ACC_CHECK_EMPTY", r, "qD_OUT_CHECK_EMPTY_LEFT", (None,None,None,None,None), ("S","S","S","S","L"))
        else:
            add("qD_ACC_CHECK_EMPTY", r, "qD_CLEAR_FAC_TO_L", (None,None,None,None,None), ("S","S","S","S","S"))

    # Check if OUT is empty (head at first cell after L)
    for r in all_reads:
        a,b,c,d,e = r
        if e == "L" or e == "#":
            # OUT is empty; write 0 and finish
            add("qD_OUT_CHECK_EMPTY_LEFT", r, "qD_WRITE_ZERO_AND_FINISH", (None,None,None,None,None), ("S","S","S","S","R"))
        else:
            # Not empty, go back to ACC clearing
            add("qD_OUT_CHECK_EMPTY_LEFT", r, "qD_REV_CLEAR_SCR_TO_L", (None,None,None,None,None), ("S","S","S","S","R"))

    # Write 0 to OUT if empty and finish with erase marker.
    for r in all_reads:
        a,b,c,d,e = r
        if e == "#":
            add("qD_WRITE_ZERO_AND_FINISH", r, "qD_REV_CLEAR_SCR_TO_L", (None,None,None,None,"0"), ("S","S","S","S","R"))
        else:
            add("qD_WRITE_ZERO_AND_FINISH", r, "qD_WRITE_ZERO_AND_FINISH", (None,None,None,None,None), ("S","S","S","S","R"))

    # Division round: clear FAC for next quotient digit
    for r in all_reads:
        a,b,c,d,e = r
        if c == "L":
            add("qD_CLEAR_FAC_TO_L", r, "qD_CLEAR_FAC_ERASE_RIGHT", (None,None,None,None,None), ("S","S","R","S","S"))
        else:
            add("qD_CLEAR_FAC_TO_L", r, "qD_CLEAR_FAC_TO_L", (None,None,None,None,None), ("S","S","L","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if c == "#":
            add("qD_CLEAR_FAC_ERASE_RIGHT", r, "qD_CLEAR_FAC_BACK_TO_L", (None,None,None,None,None), ("S","S","L","S","S"))
        else:
            add("qD_CLEAR_FAC_ERASE_RIGHT", r, "qD_CLEAR_FAC_ERASE_RIGHT", (None,None,"#",None,None), ("S","S","R","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if c == "L":
            add("qD_CLEAR_FAC_BACK_TO_L", r, "qD_SCAN_FIRST", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            add("qD_CLEAR_FAC_BACK_TO_L", r, "qD_CLEAR_FAC_BACK_TO_L", (None,None,None,None,None), ("S","S","L","S","S"))


    # qD_SCAN_FIRST: find first 1; if found mark and go to second scan; if end => remainder 0
    for r in all_reads:
        a,b,c,d,e = r
        if b == "1":
            add("qD_SCAN_FIRST", r, "qD_SCAN_SECOND", (None,"X",None,None,None), ("S","R","S","S","S"))
        elif b == "X":
            add("qD_SCAN_FIRST", r, "qD_SCAN_FIRST", (None,None,None,None,None), ("S","R","S","S","S"))
        elif b == "#":
            add("qD_SCAN_FIRST", r, "qD_WRITE_REM0", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            add("qD_SCAN_FIRST", r, "REJECT", (None,None,None,None,None), ("S","S","S","S","S"))

    # qD_SCAN_SECOND: find second 1; if found mark and append 1 to FAC; if end => remainder 1
    for r in all_reads:
        a,b,c,d,e = r
        if b == "1":
            add("qD_SCAN_SECOND", r, "qD_FAC_APPEND_TO_L", (None,"X",None,None,None), ("S","S","S","S","S"))
        elif b == "X":
            add("qD_SCAN_SECOND", r, "qD_SCAN_SECOND", (None,None,None,None,None), ("S","R","S","S","S"))
        elif b == "#":
            add("qD_SCAN_SECOND", r, "qD_WRITE_REM1", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            add("qD_SCAN_SECOND", r, "REJECT", (None,None,None,None,None), ("S","S","S","S","S"))

    # Append to FAC
    for r in all_reads:
        a,b,c,d,e = r
        if c == "L":
            add("qD_FAC_APPEND_TO_L", r, "qD_FAC_APPEND_TO_END", (None,None,None,None,None), ("S","S","R","S","S"))
        else:
            add("qD_FAC_APPEND_TO_L", r, "qD_FAC_APPEND_TO_L", (None,None,None,None,None), ("S","S","L","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if c == "#":
            add("qD_FAC_APPEND_TO_END", r, "qD_FAC_APPEND_WRITE", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            add("qD_FAC_APPEND_TO_END", r, "qD_FAC_APPEND_TO_END", (None,None,None,None,None), ("S","S","R","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if c == "#":
            add("qD_FAC_APPEND_WRITE", r, "qD_FAC_APPEND_BACK_TO_L", (None,None,"1",None,None), ("S","S","L","S","S"))
        else:
            add("qD_FAC_APPEND_WRITE", r, "REJECT", (None,None,None,None,None), ("S","S","S","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if c == "L":
            add("qD_FAC_APPEND_BACK_TO_L", r, "qD_SCAN_FIRST", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            add("qD_FAC_APPEND_BACK_TO_L", r, "qD_FAC_APPEND_BACK_TO_L", (None,None,None,None,None), ("S","S","L","S","S"))

    # Write remainder bit to OUT at end blank, then clear ACC and replace with FAC quotient
    for bit, st in [("0","qD_WRITE_REM0"), ("1","qD_WRITE_REM1")]:
        for r in all_reads:
            a,b,c,d,e = r
            if e == "#":
                add(st, r, "qD_CLEAR_ACC_TO_L", (None,None,None,None,bit), ("S","S","S","S","R"))
            else:
                add(st, r, st, (None,None,None,None,None), ("S","S","S","S","R"))

    # Clear ACC to L then erase right
    for r in all_reads:
        a,b,c,d,e = r
        if b == "L":
            add("qD_CLEAR_ACC_TO_L", r, "qD_CLEAR_ACC_ERASE_RIGHT", (None,None,None,None,None), ("S","R","S","S","S"))
        else:
            add("qD_CLEAR_ACC_TO_L", r, "qD_CLEAR_ACC_TO_L", (None,None,None,None,None), ("S","L","S","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if b == "#":
            add("qD_CLEAR_ACC_ERASE_RIGHT", r, "qD_CLEAR_ACC_BACK_TO_L", (None,None,None,None,None), ("S","L","S","S","S"))
        else:
            add("qD_CLEAR_ACC_ERASE_RIGHT", r, "qD_CLEAR_ACC_ERASE_RIGHT", (None,"#",None,None,None), ("S","R","S","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if b == "L":
            add("qD_CLEAR_ACC_BACK_TO_L", r, "qD_COPY_FAC_TO_ACC_START", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            add("qD_CLEAR_ACC_BACK_TO_L", r, "qD_CLEAR_ACC_BACK_TO_L", (None,None,None,None,None), ("S","L","S","S","S"))

    # Copy FAC->ACC
    for r in all_reads:
        a,b,c,d,e = r
        if b == "L" and c == "L":
            add("qD_COPY_FAC_TO_ACC_START", r, "qD_COPY_FAC_TO_ACC", (None,None,None,None,None), ("S","R","R","S","S"))
        else:
            add("qD_COPY_FAC_TO_ACC_START", r, "qD_COPY_FAC_TO_ACC_START", (None,None,None,None,None), ("S","L","L","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if c == "1":
            add("qD_COPY_FAC_TO_ACC", r, "qD_COPY_FAC_TO_ACC", (None,"1",None,None,None), ("S","R","R","S","S"))
        elif c == "#":
            add("qD_COPY_FAC_TO_ACC", r, "qD_COPY_FAC_TO_ACC_DONE", (None,None,None,None,None), ("S","L","L","S","S"))
        else:
            add("qD_COPY_FAC_TO_ACC", r, "REJECT", (None,None,None,None,None), ("S","S","S","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if b == "L" and c == "L":
            add("qD_COPY_FAC_TO_ACC_DONE", r, "qD_CLEAR_FAC2_TO_L", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            add("qD_COPY_FAC_TO_ACC_DONE", r, "qD_COPY_FAC_TO_ACC_DONE", (None,None,None,None,None), ("S","L","L","S","S"))

    # Clear FAC (ready next round)
    for r in all_reads:
        a,b,c,d,e = r
        if c == "L":
            add("qD_CLEAR_FAC2_TO_L", r, "qD_CLEAR_FAC2_ERASE_RIGHT", (None,None,None,None,None), ("S","S","R","S","S"))
        else:
            add("qD_CLEAR_FAC2_TO_L", r, "qD_CLEAR_FAC2_TO_L", (None,None,None,None,None), ("S","S","L","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if c == "#":
            add("qD_CLEAR_FAC2_ERASE_RIGHT", r, "qD_CLEAR_FAC2_BACK_TO_L", (None,None,None,None,None), ("S","S","L","S","S"))
        else:
            add("qD_CLEAR_FAC2_ERASE_RIGHT", r, "qD_CLEAR_FAC2_ERASE_RIGHT", (None,None,"#",None,None), ("S","S","R","S","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if c == "L":
            # Clear FAC2 back to L
            add("qD_CLEAR_FAC2_BACK_TO_L", r, "qD_OUT_TO_END", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            # continue moving L
            add("qD_CLEAR_FAC2_BACK_TO_L", r, "qD_CLEAR_FAC2_BACK_TO_L", (None,None,None,None,None), ("S","S","L","S","S"))


    # Reverse OUT bits using SCR for temporary storage
    # Clear SCR right of L
    for r in all_reads:
        a,b,c,d,e = r
        if d == "L":
            add("qD_REV_CLEAR_SCR_TO_L", r, "qD_REV_CLEAR_SCR_ERASE_RIGHT", (None,None,None,None,None), ("S","S","S","R","S"))
        else:
            add("qD_REV_CLEAR_SCR_TO_L", r, "qD_REV_CLEAR_SCR_TO_L", (None,None,None,None,None), ("S","S","S","L","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if d == "#":
            add("qD_REV_CLEAR_SCR_ERASE_RIGHT", r, "qD_REV_CLEAR_SCR_BACK_TO_L", (None,None,None,None,None), ("S","S","S","L","S"))
        else:
            add("qD_REV_CLEAR_SCR_ERASE_RIGHT", r, "qD_REV_CLEAR_SCR_ERASE_RIGHT", (None,None,None,"#",None), ("S","S","S","R","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if d == "L":
            add("qD_REV_CLEAR_SCR_BACK_TO_L", r, "qD_REV_OUT_TO_LASTBIT", (None,None,None,None,None), ("S","S","S","R","S"))
        else:
            add("qD_REV_CLEAR_SCR_BACK_TO_L", r, "qD_REV_CLEAR_SCR_BACK_TO_L", (None,None,None,None,None), ("S","S","S","L","S"))


    # Move left until hit 0/1 or L (OUT head starts at end blank)
    for r in all_reads:
        a,b,c,d,e = r
        if e in {"0","1"}:
            add("qD_REV_OUT_TO_LASTBIT", r, "qD_REV_LOOP", (None,None,None,None,None), ("S","S","S","S","S"))
        elif e == "L":
            add("qD_REV_OUT_TO_LASTBIT", r, "qD_REV_SCR_TO_L", (None,None,None,None,None), ("S","S","S","S","S"))
        else:
            add("qD_REV_OUT_TO_LASTBIT", r, "qD_REV_OUT_TO_LASTBIT", (None,None,None,None,None), ("S","S","S","S","L"))

    # REV_LOOP: copy OUT bit to SCR end, erase OUT, move OUT L, SCR R
    for bit in ("0","1"):
        for r in all_reads:
            a,b,c,d,e = r
            if e == bit and d == "#":
                add("qD_REV_LOOP", r, "qD_REV_LOOP", (None,None,None,bit,"#"), ("S","S","S","R","L"))
            elif e == bit and d in {"0","1"}:
                # Should not happen
                add("qD_REV_LOOP", r, "qD_REV_LOOP", (None,None,None,None,None), ("S","S","S","R","S"))
    for r in all_reads:
        a,b,c,d,e = r
        if e == "L":
            add("qD_REV_LOOP", r, "qD_REV_SCR_TO_L", (None,None,None,None,None), ("S","S","S","S","S"))

    # Move SCR to L then R to first bit
    for r in all_reads:
        a,b,c,d,e = r
        if d == "L":
            add("qD_REV_SCR_TO_L", r, "qD_REV_OUT_TO_START", (None,None,None,None,None), ("S","S","S","R","S"))
        else:
            add("qD_REV_SCR_TO_L", r, "qD_REV_SCR_TO_L", (None,None,None,None,None), ("S","S","S","L","S"))

    # Move OUT to L then R to start (first blank after L)
    for r in all_reads:
        a,b,c,d,e = r
        if e == "L":
            add("qD_REV_OUT_TO_START", r, "qD_REV_COPYBACK", (None,None,None,None,None), ("S","S","S","S","R"))
        else:
            add("qD_REV_OUT_TO_START", r, "qD_REV_OUT_TO_START", (None,None,None,None,None), ("S","S","S","S","L"))

    # Copy SCR bits to OUT, erasing SCR, moving R
    for bit in ("0","1"):
        for r in all_reads:
            a,b,c,d,e = r
            if d == bit:
                add("qD_REV_COPYBACK", r, "qD_REV_COPYBACK", (None,None,None,"#",bit), ("S","S","S","R","R"))
    for r in all_reads:
        a,b,c,d,e = r
        if d == "#":
            add("qD_REV_COPYBACK", r, "qD_ERASE_OUT_L", (None,None,None,None,None), ("S","S","S","S","L"))

    # Erase OUT marker L and accept
    for r in all_reads:
        a,b,c,d,e = r
        if e == "L":
            add("qD_ERASE_OUT_L", r, "ACCEPT_D", (None,None,None,None,"#"), ("S","S","S","S","R"))
        else:
            add("qD_ERASE_OUT_L", r, "qD_ERASE_OUT_L", (None,None,None,None,None), ("S","S","S","S","L"))

    # Deterministic reject for unspecified transitions
    for st in (states | accept_states | reject_states):
        if st not in accept_states and st not in reject_states:
            reject_catchall(st)

    return MultiTapeTM(
        num_tapes=5,
        states=states | accept_states | reject_states,
        start_state=start_state,
        accept_states=accept_states,
        reject_states=reject_states,
        alphabet=ALPHABET,
        blank=BLANK,
        transitions=T,
        tape_names=["IN", "ACC", "FAC", "SCR", "OUT"],
    )

# Utility functions for testing and demo
def unary_value(cells: Dict[int, str]) -> int:
    return sum(1 for s in cells.values() if s == "1")

# Convert tape cells dict to string
def tape_to_str(cells: Dict[int, str], blank: str = BLANK) -> str:
    if not cells:
        return ""
    lo = min(cells.keys())
    hi = max(cells.keys())
    return "".join(cells.get(i, blank) for i in range(lo, hi + 1))

# Parse input string of form '#101#11##' into list of integers
def parse_inputs(inp: str) -> List[int]:
    parts = [p for p in inp.split("#") if p != ""]
    nums = []
    for p in parts:
        if all(ch in "01" for ch in p):
            nums.append(int(p, 2))
    return nums

# Main function for command-line usage
def main() -> None:
    import argparse
    import pathlib

    parser = argparse.ArgumentParser(description="FULL 5-tape TM: milestones A+B+C+D (OUT is binary, MSB first).")
    parser.add_argument("--demo", metavar="INPUT", help="Run one input, e.g. '#101#11##'")
    parser.add_argument("--verbose", action="store_true", help="Print every step")
    parser.add_argument("--window", type=int, default=35)
    parser.add_argument("--max-steps", type=int, default=8_000_000)
    parser.add_argument("--stop-after", choices=list("ABCDabcd"), default="D")
    parser.add_argument("--encode-file", metavar="PATH", help="Write TM encoding (may be huge)")
    args = parser.parse_args()

    if not args.demo:
        tests = [
            ("#101#11##", "1111"),
            ("#10#10##", "100"),
            ("#1#111##", "111"),
            ("#0#101##", "0"),
            ("#111#11#10##", "101010"),
            ("#1##", "1"),
        ]
        stop = args.stop_after.upper()
        print("=== TM quick checks ===")
        ok = True
        for inp, expected in tests:
            tm = build_tm(stop_after=stop)
            tm.reset()
            tm.set_tape(0, inp, head_at_first_nonblank=False)
            for t in range(1, 5):
                tm.set_tape(t, BLANK, head_at_first_nonblank=False)

            final = tm.run(max_steps=args.max_steps, verbose=False, window=args.window)
            if stop == "A":
                good = (final == "ACCEPT_A")
                print(("OK(A): " if good else "FAIL(A): ") + f"{inp} -> {final}")
                ok &= good
            elif stop == "B":
                good = (final == "ACCEPT_B")
                print(("OK(B): " if good else "FAIL(B): ") + f"{inp} -> {final} unary(FAC)={unary_value(tm.tapes[2].cells)}")
                ok &= good
            elif stop == "C":
                nums = parse_inputs(inp)
                expect = 1
                for n in nums:
                    expect *= n
                got = unary_value(tm.tapes[1].cells)
                good = (final == "ACCEPT_C" and got == expect)
                print(("OK(C): " if good else "FAIL(C): ") + f"{inp} -> unary(ACC)={got}")
                ok &= good
            else:
                out = tape_to_str(tm.tapes[4].cells).strip(BLANK)
                good = (final == "ACCEPT_D" and out == expected)
                print(("OK:   " if good else "FAIL: ") + f"{inp} -> {out!r} expected {expected!r} (state={final}, steps={tm.steps})")
                ok &= good

        if not ok:
            raise SystemExit(1)
        return
    
    stop = args.stop_after.upper()
    tm = build_tm(stop_after=stop)
    tm.reset()
    tm.set_tape(0, args.demo, head_at_first_nonblank=False)
    for t in range(1, 5):
        tm.set_tape(t, BLANK, head_at_first_nonblank=False)


    # Run the TM
    final = tm.run(max_steps=args.max_steps, verbose=args.verbose, window=args.window)
    print(f"HALT: {final}")
    print(f"ACC unary value: {unary_value(tm.tapes[1].cells)}")
    print(f"FAC unary value: {unary_value(tm.tapes[2].cells)}")
    out = tape_to_str(tm.tapes[4].cells).strip(BLANK)
    print(f"OUT: {out}")
    tm.print_config(window=args.window)

    # Optionally write TM encoding to file
    if args.encode_file:
        pathlib.Path(args.encode_file).write_text(tm.encode(), encoding="utf-8")
        print(f"Encoding written to: {args.encode_file}")


if __name__ == "__main__":
    main()
