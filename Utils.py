from enum import Enum

# Constants and utilities needed by various modules in the game.

SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 600, 400
GRID_WIDTH = 30
GRID_HEIGHT = 20
SCREEN_BORDER = 4

MAX_TAPE_LENGTH = 6

class TileType(Enum):
    SPACE  = 1
    WALL   = 2
    PLAYER = 3
    PIT = 4
    GOAL = 5

def vector_add(vec1, vec2):
    # Add two 2d tuples elementwise
    return tuple(sum(x) for x in zip(vec1, vec2))

def vector_minus(vec1, vec2):
    # Subtract two 2d tuples elementwise
    return tuple(x[0] - x[1] for x in zip(vec1, vec2))

def vector_scalar_multiply(vec, scalar):
    # Multiply 2d tuple by scalar elementwise
    return tuple(x * scalar for x in vec)

def rotate_right(vec):
    # Give the compass vector rotated 90 degrees clockwise
    return (vec[1] * -1, vec[0])

def get_tape_edge_position(tape_end_position, direction, orientation):
    # Find the position of the tape edge (the hook coming out of the end of the tape) given the tape end, direction of player and orientation of tape.
    tape_edge_offset = vector_scalar_multiply(rotate_right(direction), orientation)
    return vector_add(tape_end_position, tape_edge_offset)