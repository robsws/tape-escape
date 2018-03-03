import pygame
import argparse

from Utils import *
from GameState import GameState
from Display import Display

TOOLBAR_THICKNESS = 0.1
TILEBAR_THICKNESS = 0.2

# Windows bug https://github.com/Microsoft/vscode/issues/39149#issuecomment-347260954
import win_unicode_console
win_unicode_console.enable()

arg_parser = argparse.ArgumentParser(description='Level editor for tape-escape.')
arg_parser.add_argument('-w', help='Screen width in pixels', default=600)
args = arg_parser.parse_args()

screen_width = int(args.w)
screen_height = int(screen_width * 0.67)
screen_size = (screen_width, screen_height)

pygame.init()

current_level = 1
state = GameState()

screen = pygame.display.set_mode(screen_size)
display_rect = [0, TOOLBAR_THICKNESS*screen_height, screen_width - TILEBAR_THICKNESS*screen_width, screen_height - 2*TOOLBAR_THICKNESS*screen_height]
display = Display(screen, display_rect)

enter_debugger = False

# Main game loop
finished = False
while not finished:
    # Capture input and update game state
    for event in pygame.event.get():
        # Capture button input from mouse
        if event.type == pygame.MOUSEBUTTONDOWN:
            if enter_debugger:
                pdb.set_trace()
        # Keyboard commands
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_d:
                enter_debugger = True
        # Quit game if QUIT signal is detected
        elif event.type == pygame.QUIT:
            finished = True
    
    # Capture mouse hover position
    mouse_position = pygame.mouse.get_pos()

    display.render_state(state)

pygame.quit()