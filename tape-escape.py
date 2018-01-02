from enum import Enum
import pygame
import configparser

SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 600, 400
GRID_WIDTH = 30
GRID_HEIGHT = 20
SCREEN_BORDER = 4

BLACK      =   0,   0,   0
DARK_GREY  =  30,  30,  30
LIGHT_GREY = 100, 100, 100
RED        = 150,   0,   0
YELLOW     = 150, 150,   0

TILE_BORDER = 2

TAPE_LENGTH = 6

def vector_add(vec1, vec2):
    # Add two 2d tuples elementwise
    return (sum(x) for x in zip(vec1, vec2))

class TileType(Enum):
    SPACE  = 1
    WALL   = 2
    PLAYER = 3

class PlayerOrientation(Enum):
    LEFT  = 1
    RIGHT = 2

class GameState:

    def __init__(self, level):
        config_tile_type_map = {
            '.': TileType.SPACE,
            'x': TileType.WALL,
            'P': TileType.PLAYER
        }
        self.player_position = (0,0)
        self.player_direction = (0,-1)
        self.player_orientation = -1 # -1 for left, 1 for right
        self.tape_end_position = (0,0)

        # Build the internal level grid from config
        lines = level.splitlines()
        self.grid_width = len(lines[0])
        self.grid_height = len(lines)
        self.grid = [[TileType.SPACE for y in range(self.grid_height)] for x in range(self.grid_width)]
        for y, line in enumerate(lines):
            for x, tile in enumerate(line):
                self.grid[x][y] = config_tile_type_map[tile]
                if config_tile_type_map[tile] == TileType.PLAYER:
                    self.player_position = (x,y)
                    self.tape_end_position = (x,y)

    # Methods for updating state based on input
    # def extend_tape(self):
    #     # tape goes as far forward as possible, then pushes player back
    #     temp_tape_end_pos = tape_end_position
    #     while grid[tape_en]

    # def retract_tape(self):

    # def rotate_left(self):

    # def rotate_right(self):

    # def switch_orientation(self):

pygame.init()
config = configparser.ConfigParser()
config.read('levels.ini')
level = config['Levels']['1']
state = GameState(level)

tile_width = SCREEN_WIDTH/state.grid_width
screen = pygame.display.set_mode(SCREEN_SIZE)

finished = False
while not finished:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: finished = True
    
    screen.fill(BLACK)

    for x in range(state.grid_width):
        for y in range(state.grid_height):
            # Draw the grid and the objects to the pygame screen
            tiletype = state.grid[x][y]
            if tiletype == TileType.SPACE or tiletype == TileType.PLAYER:
                screen.fill(DARK_GREY, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
            elif tiletype == TileType.WALL:
                screen.fill(LIGHT_GREY, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
            if state.tape_end_position == (x,y):
                tape_end_centre = (int(x * tile_width + tile_width/2) + (state.player_direction[0] * tile_width/2), int(y * tile_width + tile_width/2) + (state.player_direction[1] * tile_width/2))
                tape_end_point = tuple(int(sum(x)) for x in zip(tape_end_centre, (state.player_orientation * state.player_direction[1] * tile_width * 0.66, state.player_orientation * state.player_direction[0] * tile_width * 0.66)))
                pygame.draw.line(screen, YELLOW, tape_end_centre, tape_end_point, 2)
            if state.player_position == (x,y):
                pygame.draw.circle(screen, RED, (int(x * tile_width + tile_width/2), int(y * tile_width + tile_width/2)), int(tile_width/2), 0)

    pygame.display.flip()

pygame.quit()