import pdb
from enum import Enum

# Constants and utilities needed by various modules in the game.

MAX_TAPE_LENGTH = 6
GRID_BORDER = MAX_TAPE_LENGTH + 2

class TileType(Enum):
    SPACE  = 1
    WALL   = 2
    PLAYER = 3
    PIT = 4
    GOAL = 5

sym_to_tiletype_map = {
    '*': TileType.SPACE,
    '0': TileType.WALL,
    '@': TileType.PLAYER,
    '.': TileType.PIT,
    '+': TileType.GOAL
}
tiletype_to_sym_map = {}
for k, v in sym_to_tiletype_map.items():
    tiletype_to_sym_map[v] = k

class Button:

    def __init__(self, button_type, screen, x, y, width, height, image_filename, action_func=None):
        self.button_type = button_type
        self.screen = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.image_filename = image_filename
        self.image = pygame.image.load(image_filename)
        self.action_func = action_func
        self.border_colour = GREY

    def position_inside_button(self, x, y):
        return self.x < x < self.x + self.width and self.y < y < self.y + self.height
        
    def draw(self):
        # Draw the main button border
        border_offset = int((BUTTON_BORDER_THICKNESS * self.width)/2)
        top_left = (self.x + border_offset, self.y + border_offset)
        top_right = (self.x + (self.width - border_offset), self.y + border_offset)
        bottom_left = (self.x + border_offset, self.y + (self.height - border_offset))
        bottom_right = (self.x + (self.width - border_offset), self.y + (self.height - border_offset))
        pygame.draw.line(self.screen, self.border_colour, top_left, top_right, border_offset*2)
        pygame.draw.line(self.screen, self.border_colour, top_left, bottom_left, border_offset*2)
        pygame.draw.line(self.screen, self.border_colour, bottom_left, bottom_right, border_offset*2)
        pygame.draw.line(self.screen, self.border_colour, top_right, bottom_right, border_offset*2)
        # Draw the image on the button
        scaled = pygame.transform.scale(self.image, (self.width - border_offset*6, self.height - border_offset*6))
        self.screen.blit(scaled, [self.x + border_offset*3, self.y + border_offset*3, self.width - border_offset*2, self.height - border_offset*2])

class ToggleButtonGroup:

    def __init__(self, buttons):
        self.buttons = buttons
        self.active = 0
        self.update_buttons()
    
    def update_buttons(self):
        for i, button in enumerate(self.buttons):
            if i == self.active:
                button.border_colour = LIGHTER_GREY
            else:
                button.border_colour = GREY

    def check_for_new_active(self, mouse_pos):
        for i, button in enumerate(self.buttons):
            if button.position_inside_button(mouse_pos[0], mouse_pos[1]):
                self.active = i
                self.update_buttons()
                break

    def get_active_button(self):
        return self.buttons[self.active]

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