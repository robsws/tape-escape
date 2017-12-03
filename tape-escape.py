import pygame
pygame.init()

SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 600, 400

BLACK     =   0,   0,   0
DARK_GREY = 30, 30, 30

screen = pygame.display.set_mode(SCREEN_SIZE)

finished = False
while not finished:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: finished = True
    
    screen.fill(BLACK)

    # Draw a grid of 60 x 40 squares
    grid_width = 60
    grid_height = 40
    tile_width = SCREEN_WIDTH/grid_width
    tile_border = 3
    screen_border = 5
    for x in range(screen_border, grid_width - screen_border):
        for y in range(screen_border, grid_height - screen_border):
            pygame.draw.rect(screen, DARK_GREY, [x*tile_width + tile_border, y*tile_width + tile_border, tile_width - tile_border, tile_width - tile_border], 0)

    pygame.display.flip()

pygame.quit()