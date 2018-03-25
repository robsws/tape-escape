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

# Main game loop
finished = False
while not finished:
    print(history.to_string()+'    '+str(history.active))
    # Capture input and update game state
    obstruction_coords = None
    for event in pygame.event.get():
        # Capture button input from mouse
        if event.type == pygame.MOUSEBUTTONDOWN:
            if enter_debugger:
                pdb.set_trace()
            if event.button == 1: # left click
                state.extend_tape()
                history.add(state)
            elif event.button == 2: # middle click
                obstruction_coords = state.switch_orientation()
                history.add(state)
            elif event.button == 3: # right click
                state.retract_tape()
                history.add(state)
        # Keyboard cheats
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_n:
                # N key skips level
                state.force_win = True
                history.add(state)
            elif event.key == pygame.K_p and current_level > 0:
                # P key goes back a level
                current_level -= 1
                starting_state = level_loader.load_new_level_state(current_level)
                state = deepcopy(starting_state)
                history.add(state)
            elif event.key == pygame.K_r:
                # R key restarts level
                state = deepcopy(starting_state)
                history.add(state)
            elif event.key == pygame.K_z:
                # Z key undoes a move
                state = history.back()
            elif event.key == pygame.K_y:
                # Y key redoes a move
                state = history.forward()
            elif event.key == pygame.K_d:
                enter_debugger = True
        # Quit game if QUIT signal is detected
        elif event.type == pygame.QUIT:
            finished = True
    
    # Capture mouse hover position to determine which way to face
    mouse_position = pygame.mouse.get_pos()
    # Convert everything to window space coordinates
    mouse_window_space_x = (mouse_position[0] - display_rect[0]) / display_rect[2]
    mouse_window_space_y = (mouse_position[1] - display_rect[1]) / display_rect[3]
    player_window_space_x = state.player_position[0] / state.grid_width
    player_window_space_y = state.player_position[1] / state.grid_height
    # Make coordinates relative to the player
    mouse_player_space_x = mouse_window_space_x - player_window_space_x
    mouse_player_space_y = mouse_window_space_y - player_window_space_y
    # Calculate which quadrant the mouse position exists in
    # \ n /
    #  \ /
    # w X e
    #  / \
    # / s \
    if mouse_player_space_x > 0:
        # Mouse is East of player
        if mouse_player_space_y > mouse_player_space_x:
            # Mouse is South of player
            obstruction_coords = state.change_direction((0, 1))
        elif -mouse_player_space_y > mouse_player_space_x:
            # Mouse is North of player
            obstruction_coords = state.change_direction((0, -1))
        else:
            # Mouse is strictly East of player
            obstruction_coords = state.change_direction((1, 0))
    else:
        # Mouse is West of player
        if mouse_player_space_y > -mouse_player_space_x:
            # Mouse is South of player
            obstruction_coords = state.change_direction((0, 1))
        elif -mouse_player_space_y > -mouse_player_space_x:
            # Mouse is North of player
            obstruction_coords = state.change_direction((0, -1))
        else:
            # Mouse is strictly West of player
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