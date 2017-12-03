import sys
import pygame
pygame.init()

SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 320, 240
BLACK = 0, 0, 0

screen = pygame.display.set_mode(SCREEN_SIZE)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()
    
    screen.fill(BLACK)
    pygame.display.flip()