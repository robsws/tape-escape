import pygame
import argparse

from Utils import *
from GameState import GameState
from Display import *

TOOLBAR_THICKNESS = 0.1
TILEBAR_THICKNESS = 0.2
BUTTON_BORDER_THICKNESS = 0.2

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

class Button:

    def __init__(self, screen, x, y, width, height, image_filename, action_func=None):
        self.screen = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.image_filename = image_filename
        self.image = pygame.image.load(image_filename)
        self.action_func = action_func

    def draw(self):
        # Draw the main button border
        border_colour = GREY
        border_offset = int((BUTTON_BORDER_THICKNESS * self.width)/2)
        top_left = (self.x + border_offset, self.y + border_offset)
        top_right = (self.x + (self.width - border_offset), self.y + border_offset)
        bottom_left = (self.x + border_offset, self.y + (self.height - border_offset))
        bottom_right = (self.x + (self.width - border_offset), self.y + (self.height - border_offset))
        pygame.draw.line(self.screen, border_colour, top_left, top_right, border_offset*2)
        pygame.draw.line(self.screen, border_colour, top_left, bottom_left, border_offset*2)
        pygame.draw.line(self.screen, border_colour, bottom_left, bottom_right, border_offset*2)
        pygame.draw.line(self.screen, border_colour, top_right, bottom_right, border_offset*2)
        # Draw the image on the button
        self.screen.blit(self.image, [self.x + border_offset*3, self.y + border_offset*3, self.width - border_offset*2, self.height - border_offset*2])

enter_debugger = False

buttons = list()
button_images = [
    ['images/pit_icon.png', 'images/floor_icon.png', 'images/wall_icon.png'],
    ['images/player_icon.png', 'images/goal_icon.png', 'images/blank_icon.png'],
    ['images/block_a_icon.png', 'images/block_b_icon.png', 'images/block_c_icon.png'],
    ['images/block_d_icon.png', 'images/block_e_icon.png', 'images/block_f_icon.png'],
    ['images/block_a_pit_icon.png', 'images/block_b_pit_icon.png', 'images/block_c_pit_icon.png'],
    ['images/block_d_pit_icon.png', 'images/block_e_pit_icon.png', 'images/block_f_pit_icon.png'],
]
button_width = int((screen_width-display.outer_width)/3)
for x in range(len(button_images[0])):
    for y in range(len(button_images)):
        buttons.append(Button(screen, display.outer_width + button_width * x, display.y_outer_offset + button_width * y, button_width, button_width, button_images[y][x]))

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
    for button in buttons:
        button.draw()
    pygame.display.flip()

pygame.quit()