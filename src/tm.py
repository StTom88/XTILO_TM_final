
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, List, Set, Optional, Iterable, Any

Move = str  # 'L', 'R', 'S'


@dataclass
class Tape:
    
    # The blank symbol
    blank: str = '#'
    cells: Dict[int, str] = None
    head: int = 0

    # Initialize cells dict if not provided
    def __post_init__(self) -> None:
        if self.cells is None:
            self.cells = {}

    # Read the symbol at the head position
    def read(self) -> str:
        return self.cells.get(self.head, self.blank)
    
    # Write a symbol at the head position
    def write(self, sym: str) -> None:
        if sym == self.blank:
            self.cells.pop(self.head, None)
        else:
            self.cells[self.head] = sym

    # Move the head
    def move(self, mv: Move) -> None:
        if mv == 'L':
            self.head -= 1
        elif mv == 'R':
            self.head += 1
        elif mv == 'S':
            return
        else:
            raise ValueError(f"Invalid move: {mv}")
        
    # Load tape content from string
    def load(self, s: str, head_at_first_nonblank: bool = False) -> None:
        self.cells.clear()
        self.head = 0
        for i, ch in enumerate(s):
            if ch != self.blank:
                self.cells[i] = ch
        if head_at_first_nonblank:
            for i, ch in enumerate(s):
                if ch != self.blank:
                    self.head = i
                    break

    # View a window around the head
    def window(self, center: Optional[int] = None, radius: int = 30) -> Tuple[str, int]:
        """
        Return a string view and index of head within that string.
        """
        c = self.head if center is None else center
        lo, hi = c - radius, c + radius
        out = []
        for i in range(lo, hi + 1):
            out.append(self.cells.get(i, self.blank))
        head_index = self.head - lo
        return ''.join(out), head_index
    
    # Get min and max occupied cell indices
    def minmax(self) -> Optional[Tuple[int,int]]:
        if not self.cells:
            return None
        return (min(self.cells.keys()), max(self.cells.keys()))
    
    # Convert tape content to string
    def content(self) -> str:
        mm = self.minmax()
        if mm is None:
            return ''
        lo, hi = mm
        return ''.join(self.cells.get(i, self.blank) for i in range(lo, hi + 1))


@dataclass(frozen=True)
class Transition:
    next_state: str
    write: Tuple[str, ...]
    move: Tuple[Move, ...]

# Multi-tape Turing Machine
class MultiTapeTM:

    def __init__(
        self,
        *,
        num_tapes: int,
        states: Set[str],
        start_state: str,
        accept_states: Set[str],
        reject_states: Optional[Set[str]] = None,
        alphabet: Optional[Set[str]] = None,
        blank: str = '#',
        transitions: Optional[Dict[Tuple[str, Tuple[str, ...]], Transition]] = None,
        tape_names: Optional[List[str]] = None,
    ) -> None:
        self.num_tapes = num_tapes
        self.blank = blank
        self.states = set(states)
        self.start_state = start_state
        self.accept_states = set(accept_states)
        self.reject_states = set(reject_states or set(['REJECT']))
        self.alphabet = set(alphabet or set())
        self.alphabet.add(blank)

        self.transitions: Dict[Tuple[str, Tuple[str, ...]], Transition] = dict(transitions or {})
        self.tapes: List[Tape] = [Tape(blank=blank) for _ in range(num_tapes)]
        self.state: str = start_state
        self.steps: int = 0
        self.tape_names = tape_names or [f"T{i+1}" for i in range(num_tapes)]
        if len(self.tape_names) != num_tapes:
            raise ValueError("tape_names must match num_tapes")

    def reset(self) -> None:
        self.tapes = [Tape(blank=self.blank) for _ in range(self.num_tapes)]
        self.state = self.start_state
        self.steps = 0

    def set_tape(self, idx: int, s: str, head_at_first_nonblank: bool = False) -> None:
        self.tapes[idx].load(s, head_at_first_nonblank=head_at_first_nonblank)

    def read_symbols(self) -> Tuple[str, ...]:
        return tuple(t.read() for t in self.tapes)

    def is_halting(self) -> bool:
        return self.state in self.accept_states or self.state in self.reject_states

    def step(self) -> None:
        if self.is_halting():
            return
        read = self.read_symbols()
        key = (self.state, read)
        tr = self.transitions.get(key)
        if tr is None:
            # deterministic reject if missing rule
            self.state = next(iter(self.reject_states))
            self.steps += 1
            return
        if len(tr.write) != self.num_tapes or len(tr.move) != self.num_tapes:
            raise ValueError("Transition arity mismatch")
        # write
        for tape, sym in zip(self.tapes, tr.write):
            if sym not in self.alphabet:
                raise ValueError(f"Symbol {sym!r} not in alphabet")
            tape.write(sym)
        # move
        for tape, mv in zip(self.tapes, tr.move):
            tape.move(mv)

        self.state = tr.next_state
        self.steps += 1


    # Main run function
    def run(self, max_steps: int = 1_000_000, *, verbose: bool = True, window: int = 35) -> str:
        if verbose:
            self.print_config(window=window)
        while not self.is_halting() and self.steps < max_steps:
            self.step()
            if verbose:
                self.print_config(window=window)
        return self.state
    
    # Utility functions for testing and demo
    def print_config(self, window: int = 35) -> None:
        print(f"[step={self.steps:06d}] state={self.state}")
        for name, tape in zip(self.tape_names, self.tapes):
            view, head_idx = tape.window(radius=window)
            pointer = ' ' * head_idx + '↑'
            print(f"  {name}: {view}")
            print(f"       {pointer} (head={tape.head})")
        print()

    def encode(self) -> str:
        
        # Produce a textual encoding of the TM
        items = []
        for (st, syms), tr in self.transitions.items():
            items.append((st, syms, tr.next_state, tr.write, tr.move))
        items.sort(key=lambda x: (x[0], x[1]))
        lines = []
        lines.append(f"num_tapes={self.num_tapes}")
        lines.append(f"blank={self.blank!r}")
        lines.append(f"start={self.start_state}")
        lines.append(f"accept={sorted(self.accept_states)}")
        lines.append(f"reject={sorted(self.reject_states)}")
        lines.append("transitions:")
        for st, syms, nst, wr, mv in items:
            lines.append(f"  ({st}, {syms}) -> ({nst}, {wr}, {mv})")
        return "\n".join(lines)
