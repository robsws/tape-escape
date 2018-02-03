from enum import Enum
import pygame
import configparser
from itertools import *
from collections import defaultdict
from copy import deepcopy
from time import sleep
import re

# Windows bug https://github.com/Microsoft/vscode/issues/39149#issuecomment-347260954
import win_unicode_console
win_unicode_console.enable()

SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 600, 400
GRID_WIDTH = 30
GRID_HEIGHT = 20
SCREEN_BORDER = 4

BLACK       =   0,   0,   0
DARK_GREY   =  30,  30,  30
LIGHT_GREY  = 100, 100, 100
SILVER      = 200, 200, 200
RED         = 150,   0,   0
YELLOW      = 150, 150,   0
LIGHT_GREEN =  51, 255, 153

TILE_BORDER = 2

MAX_TAPE_LENGTH = 6

def vector_add(vec1, vec2):
    # Add two 2d tuples elementwise
    return tuple(sum(x) for x in zip(vec1, vec2))

def vector_minus(vec1, vec2):
    # Subtract two 2d tuples elementwise
    return tuple(x[0] - x[1] for x in zip(vec1, vec2))

def vector_scalar_multiply(vec, scalar):
    # Multiply 2d tuple by scalar elementwise
    return tuple(x * scalar for x in vec)

def rotate_right(vec):
    # Give the compass vector rotated 90 degrees clockwise
    return (vec[1] * -1, vec[0])

class TileType(Enum):
    SPACE  = 1
    WALL   = 2
    PLAYER = 3
    PIT = 4
    GOAL = 5

class GameState:

    def __init__(self, level):
        config_tile_type_map = {
            '*': TileType.SPACE,
            '0': TileType.WALL,
            '@': TileType.PLAYER,
            '.': TileType.PIT,
            '+': TileType.GOAL
        }
        self.player_position = (0,0)
        self.player_direction = (0,-1)
        self.player_orientation = -1 # -1 for left, 1 for right
        self.tape_end_position = (0,0)
        self.circle_points = set() # TODO remove        

        # Build the internal level grid from config
        lines = level.splitlines()
        self.grid_width = len(lines[0])
        self.grid_height = len(lines)
        self.grid = [[TileType.SPACE for y in range(self.grid_height)] for x in range(self.grid_width)]
        self.blocks = defaultdict(list)
        for y, line in enumerate(lines):
            for x, tile in enumerate(line):
                # blocks with the same alphabet letter move as a unit
                # upper case signifies a space beneath, lower case signifies a pit beneath
                if re.match(r'[A-Z]', tile):
                    self.blocks[tile.lower()].append((x,y))
                    self.grid[x][y] = TileType.SPACE
                elif re.match(r'[a-z]', tile):
                    self.blocks[tile].append((x,y))
                    self.grid[x][y] = TileType.PIT
                if config_tile_type_map[tile] == TileType.PLAYER:
                    self.player_position = (x,y)
                    self.tape_end_position = (x,y)
                    self.grid[x][y] = TileType.SPACE
                elif config_tile_type_map[tile] == TileType.GOAL:
                    self.goal_position = (x,y)
                    self.grid[x][y] = TileType.SPACE
                else:
                    self.grid[x][y] = config_tile_type_map[tile]
        # Also keep a lookup from grid position -> block type to make checking squares easier
        self.update_block_grid()

    def update_block_grid(self):
        # Reset the lookup table
        self.block_grid = [['' for y in range(self.grid_height)] for x in range(self.grid_width)]
        # Loop over blocks and store key in respective positions in lookup table
        for block_key in self.blocks.keys():
            positions = self.blocks[block_key]
            for position in positions:
                self.block_grid[position[0]][position[1]] = block_key

    def is_inside_grid(self, position):
        return position[0] > 0 and position[0] < self.grid_width and position[1] > 0 and position[1] < self.grid_height

    # Methods for updating state based on input
    def extend_tape(self):
        # tape goes as far forward as possible
        # or pushes player back if already against wall
        # tape edge is where the very tip of the tape end resides, the adjacent square to the tape end position.
        #
        #           0 1 2    
        #         0   r -    
        #         1   |      
        #         2   O
        #
        # tape end position (r) = (1,0)
        # tape edge position (-) = (2,0)
        # player position (O) = (1,2)
        prev_tape_end_position = self.tape_end_position
        tape_end_position = vector_add(prev_tape_end_position, self.player_direction)
        tape_edge_offset = vector_scalar_multiply(rotate_right(self.player_direction), self.player_orientation)
        tape_edge_position = vector_add(tape_end_position, tape_edge_offset)
        prev_tape_length = abs(sum(vector_minus(prev_tape_end_position, self.player_position)))
        tape_length = prev_tape_length + 1
        if self.grid[tape_end_position[0]][tape_end_position[1]] == TileType.WALL or self.grid[tape_edge_position[0]][tape_edge_position[1]] == TileType.WALL:
            # Push player away from wall
            prev_player_position = self.player_position
            player_position = vector_add(prev_player_position, vector_scalar_multiply(self.player_direction, -1))
            while self.grid[player_position[0]][player_position[1]] != TileType.WALL and prev_tape_length != MAX_TAPE_LENGTH:
                prev_player_position = player_position
                player_position = vector_add(player_position, vector_scalar_multiply(self.player_direction, -1))
                prev_tape_length = tape_length
                tape_length = abs(sum(vector_minus(prev_tape_end_position, player_position)))
            self.player_position = prev_player_position           
        else:
            # Extend tape as far as it can go
            while self.grid[tape_end_position[0]][tape_end_position[1]] != TileType.WALL and self.grid[tape_edge_position[0]][tape_edge_position[1]] != TileType.WALL and prev_tape_length != MAX_TAPE_LENGTH:
                prev_tape_end_position = tape_end_position
                tape_end_position = vector_add(tape_end_position, self.player_direction)
                tape_edge_position = vector_add(tape_end_position, tape_edge_offset)
                prev_tape_length = tape_length
                tape_length = abs(sum(vector_minus(tape_end_position, self.player_position)))
            # we want the tape to end up inbetween us and the wall, so use prev tape end position
            self.tape_end_position = prev_tape_end_position

    def retract_tape(self):
        # tape comes back towards the player as far as possible
        # TODO then pulls player towards it if already against a wall
        prev_tape_end_position = self.tape_end_position
        tape_end_position = self.tape_end_position
        tape_edge_offset = vector_scalar_multiply(rotate_right(self.player_direction), self.player_orientation)
        tape_edge_position = vector_add(tape_end_position, tape_edge_offset)
        tape_length = abs(sum(vector_minus(tape_end_position, self.player_position)))
        if self.grid[self.tape_end_position[0]][self.tape_end_position[1]] == TileType.WALL or self.grid[tape_edge_position[0]][tape_edge_position[1]] == TileType.WALL:
            prev_player_position = self.player_position
            player_position = vector_add(prev_player_position, self.player_direction)
            prev_tape_length = tape_length
            tape_length -= 1
            while self.grid[player_position[0]][player_position[1]] != TileType.WALL and prev_tape_length != 0:
                prev_player_position = player_position
                player_position = vector_add(player_position, self.player_direction)
                prev_tape_length = tape_length
                tape_length = abs(sum(vector_minus(prev_tape_end_position, player_position)))
            # we want the tape to end up inbetween us and the wall, so use prev tape end position
            self.player_position = prev_player_position
        else:
            while self.grid[tape_end_position[0]][tape_end_position[1]] != TileType.WALL and self.grid[tape_edge_position[0]][tape_edge_position[1]] != TileType.WALL and tape_length != 0:
                tape_end_position = vector_add(tape_end_position, vector_scalar_multiply(self.player_direction, -1))
                tape_edge_position = vector_add(tape_end_position, tape_edge_offset)
                tape_length = abs(sum(vector_minus(tape_end_position, self.player_position)))
            # we want the tape to end up inbetween us and the wall, so use prev tape end position
            self.tape_end_position = tape_end_position

    def change_direction(self, direction):
        # Changes the player_direction to 'direction', provided there are no obstructions
        # Returns the list of obstruction coordinates or None if no obstructions found.
        # Skip if target direction is already the way we are facing or opposite the way we are facing (only 90 degree moves are valid)
        if self.player_direction == direction or self.player_direction == vector_scalar_multiply(direction, -1):
            return None
        # Add one to the tape length for the purposes of calculating the arc of movement.
        tape_length = abs(sum(vector_minus(self.tape_end_position, self.player_position)))
        tape_arc_radius = tape_length + 1
        # Scan across the bounding square whose sides are length t*2 where t = tape radius
        # and for each point, if it is a wall and is within the circle traced by the tape
        # it counts as an obstruction.
        # The bounding square is split into four quadrants (nw, sw, ne, se) and move will be limited
        # based on current direction and which quadrants contain an obstruction
        obstructions = defaultdict(set)
        self.circle_points = set()
        for x in range(max(0, self.player_position[0] - tape_arc_radius), min(self.player_position[0] + 1, GRID_WIDTH)):
            for y in range(max(0, self.player_position[1] - tape_arc_radius), min(self.player_position[1] + 1, GRID_HEIGHT)):
                # Check for obstructions in North West quadrant
                if self.grid[x][y] == TileType.WALL and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((-1,0),(0,-1))].add((x,y)) # west to north
                    obstructions[((0,-1),(-1,0))].add((x,y)) # north to west
            for y in range(self.player_position[1], min(self.player_position[1] + tape_arc_radius, GRID_HEIGHT)):
                # Check for obstructions in South West quadrant
                if self.grid[x][y] == TileType.WALL and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((-1,0),(0,1))].add((x,y)) # west to south
                    obstructions[((0,1),(-1,0))].add((x,y)) # south to west
        for x in range(max(0, self.player_position[0]), min(self.player_position[0] + tape_arc_radius, GRID_WIDTH)):
            for y in range(max(0, self.player_position[1] - tape_arc_radius), min(self.player_position[1] + 1, GRID_HEIGHT)):
                # Check for obstructions in North East quadrant
                if self.grid[x][y] == TileType.WALL and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((0,-1),(1,0))].add((x,y)) # north to east
                    obstructions[((1,0),(0,-1))].add((x,y)) # east to north
            for y in range(self.player_position[1], min(self.player_position[1] + tape_arc_radius, GRID_HEIGHT)):
                # Check for obstructions in South East quadrant
                if self.grid[x][y] == TileType.WALL and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((0,1),(1,0))].add((x,y)) # south to east
                    obstructions[((1,0),(0,1))].add((x,y)) # east to south

        if (self.player_direction, direction) not in obstructions:
            # Intended rotation is not obstructed, update state.
            self.player_direction = direction
            self.tape_end_position = vector_add(self.player_position, vector_scalar_multiply(self.player_direction, tape_length))
        else:
            # Intended rotation is obstructed, return a set of the obstructions.
            return obstructions[(self.player_direction, direction)]
        return None

    def switch_orientation(self):
        self.player_orientation *= -1

    def goal_reached(self):
        return self.player_position == self.tape_end_position == self.goal_position

    def fallen_off(self):
        # Player has fallen off if every square between player and tape end inclusive is a PIT square
        # Algorithm only works if tape end and player are aligned vertically or horizontally (other states should not arise from movements)
        # If they aren't, player is considered 'fallen_off' by default.
        has_fallen_off = True
        if self.player_position[0] == self.tape_end_position[0]:
            # Vertically aligned
            distance = self.tape_end_position[1] - self.player_position[1]
            step = int(distance / abs(distance)) if distance != 0 else 1
            for i in range(self.player_position[1], self.tape_end_position[1] + step, step):
                position = (self.player_position[0], i)
                if self.is_inside_grid(position) and self.grid[position[0]][position[1]] != TileType.PIT:
                    has_fallen_off = False
                    break
        elif self.player_position[1] == self.tape_end_position[1]:
            # Horizontally aligned
            distance = self.tape_end_position[0] - self.player_position[0]
            step = int(distance / abs(distance)) if distance != 0 else 1
            for i in range(self.player_position[0], self.tape_end_position[0] + step, step):
                position = (i, self.player_position[1])
                if self.is_inside_grid(position) and self.grid[position[0]][position[1]] != TileType.PIT:
                    has_fallen_off = False
                    break
        return has_fallen_off


pygame.init()
config = configparser.ConfigParser()
config.read('levels.ini')

def load_new_level_state(level):
    return GameState(config['Levels'][str(level)])

current_level = 1
starting_state = load_new_level_state(current_level)
state = deepcopy(starting_state)

tile_width = SCREEN_WIDTH/state.grid_width
screen = pygame.display.set_mode(SCREEN_SIZE)

# Main game loop
finished = False
while not finished:
    # Capture input and update game state
    for event in pygame.event.get():
        # Capture button input from mouse
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # left click
                state.extend_tape()
            elif event.button == 2: # middle click
                state.switch_orientation()
            elif event.button == 3: # right click
                state.retract_tape()
        # Keyboard cheats
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_2:
                current_level = 2
                state = load_new_level_state(2)
        # Quit game if QUIT signal is detected
        elif event.type == pygame.QUIT:
            finished = True
    
    # Capture mouse hover position to determine which way to face
    mouse_position = pygame.mouse.get_pos()
    # Convert everything to window space coordinates
    mouse_window_space_x = mouse_position[0] / SCREEN_WIDTH
    mouse_window_space_y = mouse_position[1] / SCREEN_HEIGHT
    player_window_space_x = state.player_position[0] / GRID_WIDTH
    player_window_space_y = state.player_position[1] / GRID_HEIGHT
    # Make coordinates relative to the player
    mouse_player_space_x = mouse_window_space_x - player_window_space_x
    mouse_player_space_y = mouse_window_space_y - player_window_space_y
    # Calculate which quadrant the mouse position exists in
    # \ n /
    #  \ /
    # w X e
    #  / \
    # / s \
    obstruction_coords = None
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

    # Load next level if player has reached the goal
    if state.goal_reached():
        current_level += 1
        if current_level <= len(config['Levels']):
            starting_state = load_new_level_state(current_level)
            state = deepcopy(starting_state)
        else:
            # TODO: Something should happen when player finishes the game
            finished = True
    # Put player back at the beginning and flash red if the player has fallen off
    if state.fallen_off():
        state = deepcopy(starting_state)
        screen.fill(RED)
        pygame.display.flip()
        sleep(0.2)

    # Reset screen to black
    screen.fill(BLACK)
    # Draw the grid and the static objects to the pygame screen
    for x in range(state.grid_width):
        for y in range(state.grid_height):
            tiletype = state.grid[x][y]
            if tiletype == TileType.SPACE:
                screen.fill(DARK_GREY, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
            elif obstruction_coords != None and (x, y) in obstruction_coords:
                screen.fill(RED, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)                
            elif tiletype == TileType.WALL:
                screen.fill(LIGHT_GREY, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
            if (x, y) in state.circle_points:
                pygame.draw.circle(screen, BLACK, (int(x * tile_width + tile_width/2), int(y * tile_width + tile_width/2)), 4, 0)

    # Draw goal
    screen.fill(LIGHT_GREEN, [state.goal_position[0] * tile_width + TILE_BORDER, state.goal_position[1] * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)

    # Draw blocks


    # Draw player
    tape_end_centre = (int(state.tape_end_position[0] * tile_width + tile_width/2) + (state.player_direction[0] * tile_width/2), int(state.tape_end_position[1] * tile_width + tile_width/2) + (state.player_direction[1] * tile_width/2))
    tape_edge_offset = vector_scalar_multiply(rotate_right(state.player_direction), state.player_orientation * tile_width * 0.66) 
    tape_edge = vector_add(tape_end_centre, tape_edge_offset)
    player_screen_position = (int(state.player_position[0] * tile_width + tile_width/2), int(state.player_position[1] * tile_width + tile_width/2))
    pygame.draw.line(screen, YELLOW, tape_end_centre, player_screen_position, 2)
    pygame.draw.line(screen, SILVER, tape_end_centre, tape_edge, 2)
    pygame.draw.circle(screen, RED, player_screen_position, int(tile_width/2), 0)
    
    # Swap the buffers
    pygame.display.flip()

pygame.quit()