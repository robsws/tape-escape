from enum import Enum
import pygame
pygame.init()

SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 600, 400
GRID_WIDTH = 60
GRID_HEIGHT = 40
SCREEN_BORDER = 5

BLACK      =   0,   0,   0
DARK_GREY  =  30,  30,  30
LIGHT_GREY = 100, 100, 100
RED        = 150,   0,   0

TILE_WIDTH = SCREEN_WIDTH/GRID_WIDTH
TILE_BORDER = 5

class TileType(Enum):
    SPACE  = 1
    WALL   = 2
    PLAYER = 3

screen = pygame.display.set_mode(SCREEN_SIZE)

finished = False
while not finished:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: finished = True
    
    screen.fill(BLACK)

    # Create and draw a grid of 60 x 40 squares
    # All grid squares are spaces to start
    grid = [[TileType.SPACE for y in range(GRID_HEIGHT)] for x in range(GRID_WIDTH)]
    for x in range(10):
        grid[20+x][20] = TileType.WALL
        grid[20][20+x] = TileType.WALL

    grid[50][20] = TileType.PLAYER

    for x in range(SCREEN_BORDER, GRID_WIDTH - SCREEN_BORDER):
        for y in range(SCREEN_BORDER, GRID_HEIGHT - SCREEN_BORDER):
            tiletype = grid[x][y]
            if tiletype == TileType.SPACE or tiletype == TileType.PLAYER:
                screen.fill(DARK_GREY, [int(x * TILE_WIDTH + TILE_BORDER/2), int(y * TILE_WIDTH + TILE_BORDER/2), int(TILE_WIDTH - TILE_BORDER/2), int(TILE_WIDTH - TILE_BORDER/2)], 0)
            elif tiletype == TileType.WALL:
                screen.fill(LIGHT_GREY, [x * TILE_WIDTH, y * TILE_WIDTH, TILE_WIDTH, TILE_WIDTH], 0)
            if tiletype == TileType.PLAYER:
                pygame.draw.circle(screen, RED, (int(x * TILE_WIDTH + TILE_WIDTH/2), int(y * TILE_WIDTH + TILE_WIDTH/2)), int(TILE_WIDTH/2), 0)

    pygame.display.flip()

pygame.quit()