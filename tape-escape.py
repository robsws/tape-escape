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

TILE_BORDER = 2

class TileType(Enum):
    SPACE  = 1
    WALL   = 2
    PLAYER = 3

config_tile_type_map = {
    '.': TileType.SPACE,
    'x': TileType.WALL,
    'P': TileType.PLAYER
}

pygame.init()
config = configparser.ConfigParser()
config.read('levels.ini')

# Build the internal level grid from config
levelmap = config['Levels']['1']
lines = levelmap.splitlines()
grid_width = len(lines[0])
grid_height = len(lines)
grid = [[TileType.SPACE for y in range(grid_height)] for x in range(grid_width)]
for y, line in enumerate(levelmap.splitlines()):
    for x, tile in enumerate(line):
        grid[x][y] = config_tile_type_map[tile]

tile_width = SCREEN_WIDTH/grid_width
screen = pygame.display.set_mode(SCREEN_SIZE)

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
                screen.fill(LIGHT_GREY, [x * tile_width, y * tile_width, tile_width, tile_width], 0)
            if tiletype == TileType.PLAYER:
                pygame.draw.circle(screen, RED, (int(x * tile_width + tile_width/2), int(y * tile_width + tile_width/2)), int(tile_width/2), 0)

    pygame.display.flip()

pygame.quit()