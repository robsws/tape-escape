import pygame
import argparse
import easygui
import configparser

from Utils import *
from GameState import GameState, LevelLoader
from LevelDisplay import *

TOOLBAR_THICKNESS = 0.1
TILEBAR_THICKNESS = 0.2
BUTTON_BORDER_THICKNESS = 0.1

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
pygame.font.init()
font = pygame.font.SysFont('Arial',30)

current_level = 0
states = [GameState()]

screen = pygame.display.set_mode(screen_size)
display_rect = [0, TOOLBAR_THICKNESS*screen_height, screen_width - TILEBAR_THICKNESS*screen_width, screen_height - 2*TOOLBAR_THICKNESS*screen_height]
display = LevelDisplay(screen, display_rect)
display.debug_grid = True

class ButtonType(Enum):
    BLANK = 0
    TILE_PIT  = 1
    TILE_SPACE   = 2
    TILE_WALL = 3
    TILE_PLAYER = 4
    TILE_GOAL = 5
    TILE_BLOCK_A = 6
    TILE_BLOCK_B = 7
    TILE_BLOCK_C = 8
    TILE_BLOCK_D = 9
    TILE_BLOCK_E = 10
    TILE_BLOCK_F = 11
    TILE_BLOCK_A_PIT = 12
    TILE_BLOCK_B_PIT = 13
    TILE_BLOCK_C_PIT = 14
    TILE_BLOCK_D_PIT = 15
    TILE_BLOCK_E_PIT = 16
    TILE_BLOCK_F_PIT = 17
    SAVE = 18
    LOAD = 19
    PREV_LEVEL = 20
    NEXT_LEVEL = 21
    ADD_LEVEL = 22
    
button_type_to_tile_type_map = {
    ButtonType.BLANK: tiletype_to_sym_map[TileType.PIT],
    ButtonType.TILE_PIT: tiletype_to_sym_map[TileType.PIT],
    ButtonType.TILE_SPACE: tiletype_to_sym_map[TileType.SPACE],
    ButtonType.TILE_WALL: tiletype_to_sym_map[TileType.WALL],
    ButtonType.TILE_PLAYER: tiletype_to_sym_map[TileType.PLAYER],
    ButtonType.TILE_GOAL: tiletype_to_sym_map[TileType.GOAL],
    ButtonType.TILE_BLOCK_A: 'A',
    ButtonType.TILE_BLOCK_B: 'B',
    ButtonType.TILE_BLOCK_C: 'C',
    ButtonType.TILE_BLOCK_D: 'D',
    ButtonType.TILE_BLOCK_E: 'E',
    ButtonType.TILE_BLOCK_F: 'F',
    ButtonType.TILE_BLOCK_A_PIT: 'a',
    ButtonType.TILE_BLOCK_B_PIT: 'b',
    ButtonType.TILE_BLOCK_C_PIT: 'c',
    ButtonType.TILE_BLOCK_D_PIT: 'd',
    ButtonType.TILE_BLOCK_E_PIT: 'e',
    ButtonType.TILE_BLOCK_F_PIT: 'f'
}   

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

# Set up regular action buttons
action_buttons = list()
level_names = dict()

# Save button
def save():
    global states
    config = configparser.ConfigParser()
    config.add_section('Levels')
    config.add_section('LevelNames')
    for i, state in enumerate(states):
        config.set('Levels', str(i+1), state.serialize())
        if i not in level_names:
            level_names[i] = 'Level name '+str(i+1)
        config.set('LevelNames', str(i+1), level_names[i])

    # filename = easygui.filesavebox(default='levels.ini', filetypes=['*.ini'])
    filename = 'levels.ini'
    try:
        with open(filename, 'w') as file:
            config.write(file)
            file.close()
    except (IOError, TypeError) as err:
        print("File write failed: "+str(err))
    
    
action_buttons.append(Button(ButtonType.SAVE, screen, 0, 0, int(screen_width / 10), display.y_outer_offset, "images/save_icon.png", save))

def load():
    global states
    states = []
    # filename = easygui.fileopenbox()
    filename = 'levels.ini'
    try:
        levelloader = LevelLoader(filename)
    except (IOError, TypeError) as err:
        print("File load failed: "+str(err))
    for i in range(len(levelloader.config['Levels'])):
        states.append(levelloader.load_new_level_state(i+1))
    for i in range(len(levelloader.config['LevelNames'])):
        level_names[i] = levelloader.config['LevelNames'][str(i+1)]

load()
action_buttons.append(Button(ButtonType.LOAD, screen, int(screen_width / 10), 0, int(screen_width / 10), display.y_outer_offset, "images/load_icon.png", load))

def prev_level():
    global current_level
    if current_level > 0:
        current_level -= 1

action_buttons.append(Button(ButtonType.PREV_LEVEL, screen, 0, screen_height - display.y_outer_offset, int(screen_width / 10), display.y_outer_offset, "images/arrow_left.png", prev_level))

def next_level():
    global current_level
    if current_level < len(states) - 1:
        current_level += 1

action_buttons.append(Button(ButtonType.NEXT_LEVEL, screen, int(screen_width / 10), screen_height - display.y_outer_offset, int(screen_width / 10), display.y_outer_offset, "images/arrow_right.png", next_level))

def add_level():
    global states, current_level
    states.append(GameState())
    current_level = len(states)-1

action_buttons.append(Button(ButtonType.ADD_LEVEL, screen, int(screen_width / 10)*2, screen_height - display.y_outer_offset, int(screen_width / 10), display.y_outer_offset, "images/plus_icon.png", add_level))

# Buttons for painting tiles
tile_buttons = list()
tile_button_defs = [
    [{"type":ButtonType.TILE_PIT, "image":"images/pit_icon.png"}, {"type":ButtonType.TILE_SPACE, "image":"images/floor_icon.png"}, {"type":ButtonType.TILE_WALL, "image":"images/wall_icon.png"}],
    [{"type":ButtonType.TILE_PLAYER, "image":"images/player_icon.png"}, {"type":ButtonType.TILE_GOAL, "image":"images/goal_icon.png"}, {"type":ButtonType.BLANK, "image":"images/blank_icon.png"}],
    [{"type":ButtonType.TILE_BLOCK_A, "image":"images/block_a_icon.png"}, {"type":ButtonType.TILE_BLOCK_B, "image":"images/block_b_icon.png"}, {"type":ButtonType.TILE_BLOCK_C, "image":"images/block_c_icon.png"}],
    [{"type":ButtonType.TILE_BLOCK_D, "image":"images/block_d_icon.png"}, {"type":ButtonType.TILE_BLOCK_E, "image":"images/block_e_icon.png"}, {"type":ButtonType.TILE_BLOCK_F, "image":"images/block_f_icon.png"}],
    [{"type":ButtonType.TILE_BLOCK_A_PIT, "image":"images/block_a_pit_icon.png"}, {"type":ButtonType.TILE_BLOCK_B_PIT, "image":"images/block_b_pit_icon.png"}, {"type":ButtonType.TILE_BLOCK_C_PIT, "image":"images/block_c_pit_icon.png"}],
    [{"type":ButtonType.TILE_BLOCK_D_PIT, "image":"images/block_d_pit_icon.png"}, {"type":ButtonType.TILE_BLOCK_E_PIT, "image":"images/block_e_pit_icon.png"}, {"type":ButtonType.TILE_BLOCK_F_PIT, "image":"images/block_f_pit_icon.png"}],
]
button_width = int((screen_width-display.outer_width)/3)
for x in range(len(tile_button_defs[0])):
    for y in range(len(tile_button_defs)):
        button = Button(tile_button_defs[y][x]['type'], screen, display.outer_width + button_width * x, display.y_outer_offset + button_width * y, button_width, button_width, tile_button_defs[y][x]['image'])
        tile_buttons.append(button)
tile_button_group = ToggleButtonGroup(tile_buttons)

# Main game loop
finished = False
while not finished:

    mouse_position = pygame.mouse.get_pos()
    # Capture input and update game state
    for event in pygame.event.get():
        # Capture button input from mouse
        if event.type == pygame.MOUSEBUTTONDOWN:
            for button in action_buttons:
                if button.position_inside_button(mouse_position[0], mouse_position[1]):
                    button.action_func()
            tile_button_group.check_for_new_active(mouse_position)
        grid_square = display.screen_position_to_grid_square(states[current_level], mouse_position)
        if grid_square != None and pygame.mouse.get_pressed()[0]:
            states[current_level].update_grid_square(grid_square[0], grid_square[1], button_type_to_tile_type_map[tile_button_group.get_active_button().button_type])
        # Keyboard commands
        elif event.type == pygame.KEYDOWN:
            pass
        # Quit game if QUIT signal is detected
        elif event.type == pygame.QUIT:
            finished = True

    display.render_state(states[current_level])
    for button in action_buttons + tile_buttons:
        button.draw()
    level_number_display = font.render(str(current_level+1), False, RED)
    screen.blit(level_number_display, (int(screen_width / 10)*5, screen_height - display.y_outer_offset))
    pygame.display.flip()

pygame.quit()