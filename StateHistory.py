from Utils import *
from GameState import GameState
from collections import deque
from copy import deepcopy

class StateHistory:
    # Keeps a record of previous level states so that you can navigate
    # back and forth (undoing and redoing moves)
    # Also tracks where player is in the history so that player
    # can undo a sequence of moves and branch off without losing
    # history before that point.

    def __init__(self, memory_length):
        self.memory = deque([], memory_length)
        self.active = 0

    def add(self, state):
        while self.active > 0:
            # Memory forward in time from the point we were at should be deleted
            self.memory.popleft()
            self.active -= 1
        # print(self.to_string())        
        self.memory.appendleft(deepcopy(state))

    def back(self):
        if self.active < len(self.memory) - 1:
            self.active += 1
        # print(self.to_string())
        return deepcopy(self.memory[self.active])

    def forward(self):
        if self.active > 0:
            self.active -= 1
        # print(self.to_string())        
        return deepcopy(self.memory[self.active])

    def to_string(self):
        mem_strings = map(lambda x: str(x.player_position)+','+str(x.tape_end_position), self.memory)
        return ' : '.join(mem_strings)