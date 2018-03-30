import pygame
from copy import deepcopy
import pdb
import argparse

from Utils import *
from GameState import LevelLoader, GameState
from StateHistory import StateHistory
from Display import Display

# Windows bug https://github.com/Microsoft/vscode/issues/39149#issuecomment-347260954
import win_unicode_console
win_unicode_console.enable()

arg_parser = argparse.ArgumentParser(description='A game where you play as a tape measure.')
arg_parser.add_argument('-w', help='Screen width in pixels', default=600)
arg_parser.add_argument('-f', help='ini file containing levels', default='levels.ini')
args = arg_parser.parse_args()

levels_file = args.f
screen_width = int(args.w)
screen_height = int(screen_width * 0.67)
screen_size = (screen_width, screen_height)

pygame.init()

pygame.joystick.init()
AXIS_THRESHOLD_RADIUS = 0.4 # How far an analog stick must be pushed before input is registered
AXIS_THRESHOLD_RADIUS_SQUARED = AXIS_THRESHOLD_RADIUS ** 2
joysticks = []
for i in range(pygame.joystick.get_count()):
    joystick = pygame.joystick.Joystick(i)
    joystick.init()
    joysticks.append(joystick)

level_loader = LevelLoader(levels_file)

current_level = 1
starting_state = level_loader.load_new_level_state(current_level)
state = deepcopy(starting_state)

MAX_HISTORY = 50
history = StateHistory(MAX_HISTORY)
history.add(state)

screen = pygame.display.set_mode(screen_size)
display_rect = [0,0,screen_width, screen_height]
display = Display(screen, display_rect)

enter_debugger = False

# Define user actions and input mapping
finished = False
class InputMode(Enum):
    MOUSE_AND_KEYS  = 1
    GAMEPAD_AND_KEYS   = 2
input_mode = InputMode.MOUSE_AND_KEYS
if len(joysticks) > 0:
    input_mode = InputMode.GAMEPAD_AND_KEYS

def extend_tape():
    state.extend_tape()
    history.add(state)

def retract_tape():
    state.retract_tape()
    history.add(state)

def change_orientation():
    state.switch_orientation()
    history.add(state)

def toggle_input_mode():
    global input_mode
    if input_mode == InputMode.MOUSE_AND_KEYS:
        input_mode = InputMode.GAMEPAD_AND_KEYS
    else:
        input_mode = InputMode.MOUSE_AND_KEYS

def skip_level():
    state.force_win = True
    history.add(state)

def previous_level():
    global current_level, starting_state, state
    current_level -= 1
    starting_state = level_loader.load_new_level_state(current_level)
    state = deepcopy(starting_state)
    history.add(state)

def restart_level():
    global state
    state = deepcopy(starting_state)
    history.add(state)

def undo():
    global state
    state = history.back()

def redo():
    global state
    state = history.forward()

def quit_game():
    global finished
    finished = True

button_mapping = {
    (pygame.MOUSEBUTTONDOWN, 1): extend_tape,
    (pygame.MOUSEBUTTONDOWN, 2): change_orientation,
    (pygame.MOUSEBUTTONDOWN, 3): retract_tape,
    (pygame.KEYDOWN, pygame.K_m): toggle_input_mode,
    (pygame.KEYDOWN, pygame.K_n): skip_level,
    (pygame.KEYDOWN, pygame.K_p): previous_level,
    (pygame.KEYDOWN, pygame.K_r): restart_level,
    (pygame.KEYDOWN, pygame.K_z): undo,
    (pygame.KEYDOWN, pygame.K_y): redo,
    (pygame.KEYDOWN, pygame.K_q): quit_game,
    (pygame.JOYBUTTONDOWN, 5): extend_tape,
    (pygame.JOYBUTTONDOWN, 4): retract_tape,
    (pygame.JOYBUTTONDOWN, 3): restart_level,
    (pygame.JOYBUTTONDOWN, 2): undo,
    (pygame.JOYBUTTONDOWN, 1): redo,
    (pygame.JOYBUTTONDOWN, 6): quit_game,
    (pygame.JOYBUTTONDOWN, 0): change_orientation,
}

# Main game loop
axis_values = [0,0,0,0,0]
while not finished:
    # Capture input and update game state
    obstruction_coords = None
    for event in pygame.event.get():
        # Capture button input from mouse or joystick
        if (
            ( input_mode == InputMode.MOUSE_AND_KEYS and event.type == pygame.MOUSEBUTTONDOWN ) or
            ( input_mode == InputMode.GAMEPAD_AND_KEYS and event.type == pygame.JOYBUTTONDOWN )
        ):
            if (event.type, event.button) in button_mapping:
                button_mapping[(event.type, event.button)]()
        # Capture any joypad analog stick input
        elif event.type == pygame.JOYAXISMOTION:
            axis_values[event.axis] = event.value
        # Keyboard input
        elif event.type == pygame.KEYDOWN:
            if (event.type, event.key) in button_mapping:
                button_mapping[(event.type, event.key)]()
        # Quit game if QUIT signal is detected
        elif event.type == pygame.QUIT:
            finished = True
    

    if input_mode == InputMode.MOUSE_AND_KEYS:
        # Capture mouse hover position to determine which way to face
        mouse_position = pygame.mouse.get_pos()
        # Convert everything to window space coordinates
        mouse_window_space_x = (mouse_position[0] - display_rect[0]) / display_rect[2]
        mouse_window_space_y = (mouse_position[1] - display_rect[1]) / display_rect[3]
        player_window_space_x = (state.player_position[0] - GRID_BORDER) / (state.grid_width - 2*GRID_BORDER)
        player_window_space_y = (state.player_position[1] - GRID_BORDER) / (state.grid_height - 2*GRID_BORDER)
        # Make coordinates relative to the player
        axis_values[0] = mouse_window_space_x - player_window_space_x
        axis_values[1] = mouse_window_space_y - player_window_space_y
       
    # Make sure the values are outside the threshold radius for the gamepad
    if input_mode == InputMode.MOUSE_AND_KEYS or axis_values[0] ** 2 + axis_values[1] ** 2 > AXIS_THRESHOLD_RADIUS_SQUARED:
        # Calculate which quadrant the axis position/mouse position exists in
        # \ n /
        #  \ /
        # w X e
        #  / \
        # / s \
        if abs(axis_values[0]) < axis_values[1]:
            obstruction_coords = state.change_direction((0, 1))
        elif abs(axis_values[0]) < -axis_values[1]:
            obstruction_coords = state.change_direction((0, -1))
        elif axis_values[0] > abs(axis_values[1]):
            obstruction_coords = state.change_direction((1, 0))
        elif -axis_values[0] > abs(axis_values[1]):
            obstruction_coords = state.change_direction((-1, 0))

    display.obstruction_coords = obstruction_coords
    display.render_state(state)

    # Load next level if player has reached the goal
    if state.goal_reached():
        current_level += 1
        if current_level <= len(level_loader.config['Levels']):
            starting_state = level_loader.load_new_level_state(current_level)
            state = deepcopy(starting_state)
        else:
            # TODO: Something should happen when player finishes the game
            finished = True
        display.flash_green()
    # Put player back at the beginning and flash red if the player has fallen off
    elif state.player_fallen_off():
        state = deepcopy(starting_state)
        display.flash_red()

    pygame.display.flip()

pygame.quit()