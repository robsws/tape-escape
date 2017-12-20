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

class TileType(Enum):
    SPACE  = 1
    WALL   = 2
    PLAYER = 3

class PlayerOrientation(Enum):
    LEFT  = 1
    RIGHT = 2

config_tile_type_map = {
    '.': TileType.SPACE,
    'x': TileType.WALL,
    'P': TileType.PLAYER
}

pygame.init()
config = configparser.ConfigParser()
config.read('levels.ini')

# Variables to represent player state
player_position = (0,0)
player_direction = (0,-1)
player_orientation = -1 # -1 for left, 1 for right
tape_end_position = (0,0)

# Build the internal level grid from config
levelmap = config['Levels']['1']
lines = levelmap.splitlines()
grid_width = len(lines[0])
grid_height = len(lines)
grid = [[TileType.SPACE for y in range(grid_height)] for x in range(grid_width)]
for y, line in enumerate(levelmap.splitlines()):
    for x, tile in enumerate(line):
        grid[x][y] = config_tile_type_map[tile]
        if config_tile_type_map[tile] == TileType.PLAYER:
            player_position = (x,y)
            tape_end_position = (x,y)

tile_width = SCREEN_WIDTH/grid_width
screen = pygame.display.set_mode(SCREEN_SIZE)

# Subroutines for updating state based on input
# def extend_tape():

# def retract_tape():

# def rotate_left():

# def rotate_right():

# def switch_orientation():

finished = False
while not finished:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: finished = True
    
    screen.fill(BLACK)

    for x in range(grid_width):
        for y in range(grid_height):
            tiletype = grid[x][y]
            if tiletype == TileType.SPACE or tiletype == TileType.PLAYER:
                screen.fill(DARK_GREY, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
            elif tiletype == TileType.WALL:
                screen.fill(LIGHT_GREY, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
            if player_position == (x,y):
                pygame.draw.circle(screen, RED, (int(x * tile_width + tile_width/2), int(y * tile_width + tile_width/2)), int(tile_width/2), 0)
            if tape_end_position == (x,y):
                tape_end_centre = (int(x * tile_width + tile_width/2) + (player_direction[0] * tile_width/2), int(y * tile_width + tile_width/2) + (player_direction[1] * tile_width/2))
                tape_end_point = tuple(int(sum(x)) for x in zip(tape_end_centre, (player_orientation * player_direction[1] * tile_width * 0.66, player_orientation * player_direction[0] * tile_width * 0.66)))
                pygame.draw.line(screen, YELLOW, tape_end_centre, tape_end_point, 2)


    pygame.display.flip()

pygame.quit()