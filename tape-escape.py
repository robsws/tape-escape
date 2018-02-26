from enum import Enum
import pygame
import configparser
from itertools import *
from collections import defaultdict
from copy import deepcopy
from time import sleep
import re
import pdb

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
BROWN       = 204, 102,   0

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

def get_tape_edge_position(tape_end_position, direction, orientation):
    # Find the position of the tape edge (the hook coming out of the end of the tape) given the tape end, direction of player and orientation of tape.
    tape_edge_offset = vector_scalar_multiply(rotate_right(direction), orientation)
    return vector_add(tape_end_position, tape_edge_offset)

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
                elif config_tile_type_map[tile] == TileType.PLAYER:
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

    def has_block_fallen_off(self, block_key):
        # Check if the given block has fallen off the game area
        # i.e. all positions are above pits
        return all([self.grid[position[0]][position[1]] == TileType.PIT for position in self.blocks[block_key]])

    def block_can_move_one(self, block_key, direction):
        # Can the given block move in the given direction without obstruction?
        # Move the positions in the block in the given direction and check if the resulting block
        # overlaps with a wall.
        # If it overlaps with another block, check that block can move too.
        other_blocks_to_check = set()
        for position in self.blocks[block_key]:
            new_position = vector_add(position, direction)
            new_pos_block_key = self.block_grid[new_position[0]][new_position[1]]
            if (
                self.grid[new_position[0]][new_position[1]] == TileType.WALL or
                self.player_position == new_position
            ):
                # There's a wall or the player in the way.
                return False
            elif new_pos_block_key != block_key and new_pos_block_key != '':
                # There's another block in our path, check that can move too.
                other_blocks_to_check.add(new_pos_block_key)
        # If we didn't find any walls in the way, check any adjacent blocks we found.
        if not all(map(lambda x: self.block_can_move_one(x, direction), list(other_blocks_to_check))):
            # At least one of the blocks couldn't move, so we can't move either.
            return False
        else:
            return True

    def move_block_one(self, block_key, direction):
        # Move given block one square in the given direction.
        # Also move any others that are adjacent to this block.
        new_block = []
        other_blocks_moved = set()
        for position in self.blocks[block_key]:
            new_position = vector_add(position, direction)
            new_pos_block_key = self.block_grid[new_position[0]][new_position[1]]
            if new_pos_block_key != block_key and new_pos_block_key != '' and new_pos_block_key not in other_blocks_moved:
                self.move_block_one(new_pos_block_key, direction)
                other_blocks_moved.add(new_pos_block_key)
            new_block.append(new_position)
        self.blocks[block_key] = new_block
        if self.has_block_fallen_off(block_key):
            del self.blocks[block_key]
        self.update_block_grid()

    def is_inside_grid(self, position):
        return position[0] > 0 and position[0] < self.grid_width and position[1] > 0 and position[1] < self.grid_height

    def is_tape_edge_inside_wall_or_block(self, tape_edge_position, direction):
        # Check if the tape edge position given with the player facing the given direction would put the tape within a wall or block (i.e. invalid state)
        tape_edge_position_offset = vector_add(tape_edge_position, direction)
        return (
            self.grid[tape_edge_position[0]][tape_edge_position[1]] == TileType.WALL and
            self.grid[tape_edge_position_offset[0]][tape_edge_position_offset[1]] == TileType.WALL
        ) or (
            self.block_grid[tape_edge_position[0]][tape_edge_position[1]] != '' and
            self.block_grid[tape_edge_position_offset[0]][tape_edge_position_offset[1]] != '' and
            self.block_grid[tape_edge_position[0]][tape_edge_position[1]] == self.block_grid[tape_edge_position_offset[0]][tape_edge_position_offset[1]]
        )

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

        # Initialise various positions
        # next_* variables represent where the position will be after moving one square.
        # respective other position variables represent where the position currently is.

        # When extending tape, tape end always moves in the direction the player is facing (If it moves at all).
        tape_end_position = self.tape_end_position
        next_tape_end_position = vector_add(tape_end_position, self.player_direction)

        # Next tape edge position is derived from next tape end position
        next_tape_edge_position = get_tape_edge_position(next_tape_end_position, self.player_direction, self.player_orientation)

        # Tape length grows by 1 for each square moved.
        tape_length = abs(sum(vector_minus(tape_end_position, self.player_position)))
        next_tape_length = tape_length + 1

        # When extending tape, player will always move in opposite direction to the one they are facing (If they move at all).
        player_position = self.player_position
        reverse_player_direction = vector_scalar_multiply(self.player_direction, -1)
        next_player_position = vector_add(player_position, reverse_player_direction)

        # Figure out if the tape end/edge is next to a block and whether that block is obstructed
        # in the direction of extension.
        tape_end_next_to_block = self.block_grid[next_tape_end_position[0]][next_tape_end_position[1]] != ''
        tape_edge_next_to_block = self.block_grid[next_tape_edge_position[0]][next_tape_edge_position[1]] != ''
        tape_end_block_is_obstructed = tape_end_next_to_block and not self.block_can_move_one(self.block_grid[next_tape_end_position[0]][next_tape_end_position[1]], self.player_direction)
        tape_edge_block_is_obstructed = tape_edge_next_to_block and not self.block_can_move_one(self.block_grid[next_tape_edge_position[0]][next_tape_edge_position[1]], self.player_direction)
        
        # Figure out if the player is next to a block and whether that block is obstructed
        player_next_to_block = self.block_grid[next_player_position[0]][next_player_position[1]] != ''
        player_block_is_obstructed = player_next_to_block and not self.block_can_move_one(self.block_grid[next_player_position[0]][next_player_position[1]], reverse_player_direction)

        # If the tape end is immediately in front of a wall or a block that cannot move, push the player away from the wall/block.
        # Otherwise, extend the tape as far as it will go.
        if ( 
            self.grid[next_tape_end_position[0]][next_tape_end_position[1]] == TileType.WALL or
            self.grid[next_tape_edge_position[0]][next_tape_edge_position[1]] == TileType.WALL or
            (tape_end_next_to_block and tape_end_block_is_obstructed) or
            (tape_edge_next_to_block and tape_edge_block_is_obstructed)
        ):
            # Push player away from wall/block.
            
            # Move player square by square until a wall, obstructed block or the max tape length is hit
            while (
                self.grid[next_player_position[0]][next_player_position[1]] != TileType.WALL and
                (not player_next_to_block or not player_block_is_obstructed) and
                tape_length != MAX_TAPE_LENGTH
            ):
                # First move any blocks the player is resting against.
                # Check if tape end is next to a block and whether it is obstructed or not.
                if (
                    player_next_to_block and not player_block_is_obstructed and
                    # Block must not be the same one that is being pushed against!
                    self.block_grid[next_player_position[0]][next_player_position[1]] != self.block_grid[next_tape_end_position[0]][next_tape_end_position[1]] and
                    self.block_grid[next_player_position[0]][next_player_position[1]] != self.block_grid[next_tape_edge_position[0]][next_tape_edge_position[1]]
                ):
                    # Move the block next to the player.
                    self.move_block_one(self.block_grid[next_player_position[0]][next_player_position[1]], reverse_player_direction)
                
                # Move the player position by one.
                player_position = next_player_position
                next_player_position = vector_add(next_player_position, reverse_player_direction)
                tape_length = next_tape_length
                next_tape_length = abs(sum(vector_minus(tape_end_position, next_player_position)))

                # Check again if any blocks in the way are obstructed.
                player_next_to_block = self.block_grid[next_player_position[0]][next_player_position[1]] != ''
                player_block_is_obstructed = player_next_to_block and not self.block_can_move_one(self.block_grid[next_player_position[0]][next_player_position[1]], reverse_player_direction)

            self.player_position = player_position

        else:
            # Extend tape as far as it can go.
            
            # Move the tape square by square until it can no longer move.
            while (
                self.grid[next_tape_end_position[0]][next_tape_end_position[1]] != TileType.WALL and
                self.grid[next_tape_edge_position[0]][next_tape_edge_position[1]] != TileType.WALL and
                (not tape_end_next_to_block or not tape_end_block_is_obstructed) and
                (not tape_edge_next_to_block or not tape_edge_block_is_obstructed) and
                tape_length != MAX_TAPE_LENGTH
            ):
                # First move any blocks the tape is resting against.

                # Check if tape end is next to a block and whether it is obstructed or not.
                if tape_end_next_to_block and not tape_end_block_is_obstructed:
                    # Move the block on the tape end.
                    self.move_block_one(self.block_grid[next_tape_end_position[0]][next_tape_end_position[1]], self.player_direction)
                
                # Check if tape edge is next to a block and whether it is obstructed or not.
                # Must be a separate block to one found on the tape end (that one has already been moved by this point)
                if (
                    self.block_grid[next_tape_end_position[0]][next_tape_end_position[1]] != self.block_grid[next_tape_edge_position[0]][next_tape_edge_position[1]] and
                    tape_edge_next_to_block and not tape_edge_block_is_obstructed
                ):
                    # Move the block on the tape edge.
                    self.move_block_one(self.block_grid[next_tape_edge_position[0]][next_tape_edge_position[1]], self.player_direction)
                
                # Move tape end forward by one.
                tape_end_position = next_tape_end_position
                next_tape_end_position = vector_add(next_tape_end_position, self.player_direction)
                next_tape_edge_position = get_tape_edge_position(next_tape_end_position, self.player_direction, self.player_orientation)
                tape_length = next_tape_length
                next_tape_length = abs(sum(vector_minus(next_tape_end_position, self.player_position)))

                # Check again if any blocks in the way are obstructed.
                tape_end_next_to_block = self.block_grid[next_tape_end_position[0]][next_tape_end_position[1]] != ''
                tape_edge_next_to_block = self.block_grid[next_tape_edge_position[0]][next_tape_edge_position[1]] != ''
                tape_end_block_is_obstructed = tape_end_next_to_block and not self.block_can_move_one(self.block_grid[next_tape_end_position[0]][next_tape_end_position[1]], self.player_direction)
                tape_edge_block_is_obstructed = tape_edge_next_to_block and not self.block_can_move_one(self.block_grid[next_tape_edge_position[0]][next_tape_edge_position[1]], self.player_direction)
                
            # we want the tape to end up inbetween us and the wall, so use current tape end position rather than next
            self.tape_end_position = tape_end_position

    def retract_tape(self):
        # tape comes back towards the player as far as possible
        # then pulls player towards it if already against a wall

        # Initialise various positions
        # next_* variables represent where the position will be after moving one square.
        # respective other position variables represent where the position currently is.

        # When retracting tape, tape end always moves in the direction opposite the direction the player is facing (If it moves at all).
        # We use current tape end position rather than next here because the actual current position is the first one we want to check for blocks.
        # This is because the tape end position is considered to be the first square towards the player from the actual tape end (which appears in-between blocks)
        current_tape_end_position = self.tape_end_position

        # Tape edge position is derived from tape end position
        current_tape_edge_position = get_tape_edge_position(current_tape_end_position, self.player_direction, self.player_orientation)
        
        # Tape length shrinks by 1 for each square moved.
        tape_length = abs(sum(vector_minus(current_tape_end_position, self.player_position)))
        next_tape_length = tape_length
        
        # Store reverse of player direction for convenience.
        reverse_player_direction = vector_scalar_multiply(self.player_direction, -1)

        # Figure out if the tape edge is next to a block and whether that block is obstructed
        # in the direction of retraction.
        # Should never be possible for block to be between player and tape end, so don't bother checking tape end or player.
        tape_edge_next_to_block = self.block_grid[current_tape_edge_position[0]][current_tape_edge_position[1]] != ''
        tape_edge_block_is_obstructed = tape_edge_next_to_block and not self.block_can_move_one(self.block_grid[current_tape_edge_position[0]][current_tape_edge_position[1]], reverse_player_direction)

        # If the tape end/edge is immediately behind a wall or a block that cannot move, pull the player towards the tape end.
        # Otherwise, retract the tape as far as it will go.
        if (
            self.grid[self.tape_end_position[0]][self.tape_end_position[1]] == TileType.WALL or
            self.grid[current_tape_edge_position[0]][current_tape_edge_position[1]] == TileType.WALL or
            (tape_edge_next_to_block and tape_edge_block_is_obstructed)
        ):
            # Pull the player towards the tape end.
            
            # Move player square by square until the tape end has been reached.
            player_position = self.player_position
            next_player_position = vector_add(player_position, self.player_direction)
            tape_length = next_tape_length
            next_tape_length -= 1
            while tape_length != 0:
                player_position = next_player_position
                next_player_position = vector_add(next_player_position, self.player_direction)
                tape_length = next_tape_length
                next_tape_length = abs(sum(vector_minus(current_tape_end_position, next_player_position)))
            self.player_position = player_position

        else:
            # Retract the tape as far as it will go.
            
            # Now retract the tape square by square as far as it will go.
            while (
                self.grid[current_tape_end_position[0]][current_tape_end_position[1]] != TileType.WALL and
                self.grid[current_tape_edge_position[0]][current_tape_edge_position[1]] != TileType.WALL and
                (not tape_edge_next_to_block or not tape_edge_block_is_obstructed) and
                next_tape_length != 0
            ):
                # If the tape edge is hooked on a moveable block that can move, move it as far as it will go.
                if tape_edge_next_to_block and not tape_edge_block_is_obstructed:
                    # Move the block on the tape edge.
                    self.move_block_one(self.block_grid[current_tape_edge_position[0]][current_tape_edge_position[1]], reverse_player_direction)

                # Move the tape end by one towards the player.
                current_tape_end_position = vector_add(current_tape_end_position, reverse_player_direction)
                current_tape_edge_position = get_tape_edge_position(current_tape_end_position, self.player_direction, self.player_orientation)
                next_tape_length = abs(sum(vector_minus(current_tape_end_position, self.player_position)))

                # Check again if the tape edge has caught on a moveable block and whether that block is obstructed.
                tape_edge_next_to_block = self.block_grid[current_tape_edge_position[0]][current_tape_edge_position[1]] != ''
                tape_edge_block_is_obstructed = tape_edge_next_to_block and not self.block_can_move_one(self.block_grid[current_tape_edge_position[0]][current_tape_edge_position[1]], reverse_player_direction)

            self.tape_end_position = current_tape_end_position

    def change_direction(self, direction):
        # Changes the player_direction to 'direction', provided there are no obstructions
        # Returns the list of obstruction coordinates or None if no obstructions found.

        # Skip if target direction is already the way we are facing or opposite the way we are facing (only 90 degree moves are valid)
        if self.player_direction == direction or self.player_direction == vector_scalar_multiply(direction, -1):
            return None

        # Add one to the tape length for the purposes of calculating the arc of movement.
        tape_length = abs(sum(vector_minus(self.tape_end_position, self.player_position)))
        tape_arc_radius = tape_length + 1

        # Restrict rotation if tape edge will end up inside a wall or inside two segments of the same block.
        future_tape_end_position = vector_add(self.player_position, vector_scalar_multiply(direction, tape_length))
        future_tape_edge_position = get_tape_edge_position(future_tape_end_position, direction, self.player_orientation)
        
        if self.is_tape_edge_inside_wall_or_block(future_tape_edge_position, direction):
            # Prevent player rotating and pass back the two positions either side of the tape edge as the obstructions.
            future_tape_edge_position_offset = vector_add(future_tape_edge_position, direction)     
            return set([future_tape_edge_position, future_tape_edge_position_offset])

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
                if (self.grid[x][y] == TileType.WALL or self.block_grid[x][y] != '') and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((-1,0),(0,-1))].add((x,y)) # west to north
                    obstructions[((0,-1),(-1,0))].add((x,y)) # north to west
            for y in range(self.player_position[1], min(self.player_position[1] + tape_arc_radius, GRID_HEIGHT)):
                # Check for obstructions in South West quadrant
                if (self.grid[x][y] == TileType.WALL or self.block_grid[x][y] != '') and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((-1,0),(0,1))].add((x,y)) # west to south
                    obstructions[((0,1),(-1,0))].add((x,y)) # south to west
        for x in range(max(0, self.player_position[0]), min(self.player_position[0] + tape_arc_radius, GRID_WIDTH)):
            for y in range(max(0, self.player_position[1] - tape_arc_radius), min(self.player_position[1] + 1, GRID_HEIGHT)):
                # Check for obstructions in North East quadrant
                if (self.grid[x][y] == TileType.WALL or self.block_grid[x][y] != '') and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((0,-1),(1,0))].add((x,y)) # north to east
                    obstructions[((1,0),(0,-1))].add((x,y)) # east to north
            for y in range(self.player_position[1], min(self.player_position[1] + tape_arc_radius, GRID_HEIGHT)):
                # Check for obstructions in South East quadrant
                if (self.grid[x][y] == TileType.WALL or self.block_grid[x][y] != '') and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((0,1),(1,0))].add((x,y)) # south to east
                    obstructions[((1,0),(0,1))].add((x,y)) # east to south

        if (self.player_direction, direction) not in obstructions:
            # Intended rotation is not obstructed, update state.
            self.player_direction = direction
            self.tape_end_position = future_tape_end_position
        else:
            # Intended rotation is obstructed, return a set of the obstructions.
            return obstructions[(self.player_direction, direction)]
        return None

    def switch_orientation(self):
        # Make sure that tape edge won't end up inside wall or block
        future_orientation = self.player_orientation * -1
        future_tape_edge_position = get_tape_edge_position(self.tape_end_position, self.player_direction, future_orientation)
        if self.is_tape_edge_inside_wall_or_block(future_tape_edge_position, self.player_direction):
            future_tape_edge_position_offset = vector_add(future_tape_edge_position, self.player_direction)     
            return set([future_tape_edge_position, future_tape_edge_position_offset])
        # Flip the orientation
        self.player_orientation = future_orientation
        return None

    def goal_reached(self):
        return self.player_position == self.tape_end_position == self.goal_position

    def player_fallen_off(self):
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

enter_debugger = False

# Main game loop
finished = False
while not finished:
    # Capture input and update game state
    obstruction_coords = None
    for event in pygame.event.get():
        # Capture button input from mouse
        if event.type == pygame.MOUSEBUTTONDOWN:
            if enter_debugger:
                pdb.set_trace()
            if event.button == 1: # left click
                state.extend_tape()
            elif event.button == 2: # middle click
                obstruction_coords = state.switch_orientation()
            elif event.button == 3: # right click
                state.retract_tape()
        # Keyboard cheats
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_2:
                current_level = 2
                state = load_new_level_state(2)
            elif event.key == pygame.K_d:
                enter_debugger = True
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

    # Reset screen to black
    screen.fill(BLACK)
    # Draw the grid and the static objects to the pygame screen
    for x in range(state.grid_width):
        for y in range(state.grid_height):
            tiletype = state.grid[x][y]
            if tiletype == TileType.SPACE:
                screen.fill(DARK_GREY, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)              
            elif tiletype == TileType.WALL:
                screen.fill(LIGHT_GREY, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
                if x < state.grid_width - 1 and state.grid[x+1][y] == TileType.WALL:
                    screen.fill(LIGHT_GREY, [(x + 1) * tile_width - TILE_BORDER, y * tile_width + TILE_BORDER, TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
                if y < state.grid_height - 1 and state.grid[x][y+1] == TileType.WALL:
                    screen.fill(LIGHT_GREY, [x * tile_width + TILE_BORDER, (y + 1) * tile_width - TILE_BORDER, tile_width - TILE_BORDER*2, TILE_BORDER*2], 0)

            if (x, y) in state.circle_points:
                pygame.draw.circle(screen, BLACK, (int(x * tile_width + tile_width/2), int(y * tile_width + tile_width/2)), 4, 0)

    # Draw goal
    screen.fill(LIGHT_GREEN, [state.goal_position[0] * tile_width + TILE_BORDER, state.goal_position[1] * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)

    # Draw blocks
    for block_key in state.blocks.keys():
        for position in state.blocks[block_key]:
            screen.fill(BROWN, [position[0] * tile_width + TILE_BORDER, position[1] * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
            if position[0] < state.grid_width - 1 and state.block_grid[position[0]+1][position[1]] == block_key:
                screen.fill(BROWN, [(position[0] + 1) * tile_width - TILE_BORDER, position[1] * tile_width + TILE_BORDER, TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)
            if position[1] < state.grid_height - 1 and state.block_grid[position[0]][position[1]+1] == block_key:
                screen.fill(BROWN, [position[0] * tile_width + TILE_BORDER, (position[1] + 1) * tile_width - TILE_BORDER, tile_width - TILE_BORDER*2, TILE_BORDER*2], 0)

    # Draw rotation obstructions
    for x in range(state.grid_width):
        for y in range(state.grid_height):
            if obstruction_coords != None and (x, y) in obstruction_coords:
                screen.fill(RED, [x * tile_width + TILE_BORDER, y * tile_width + TILE_BORDER, tile_width - TILE_BORDER*2, tile_width - TILE_BORDER*2], 0)

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

    # Load next level if player has reached the goal
    if state.goal_reached():
        current_level += 1
        if current_level <= len(config['Levels']):
            starting_state = load_new_level_state(current_level)
            state = deepcopy(starting_state)
        else:
            # TODO: Something should happen when player finishes the game
            finished = True
        screen.fill(LIGHT_GREEN)
        sleep(0.1)
        pygame.display.flip()
        sleep(0.2)
    # Put player back at the beginning and flash red if the player has fallen off
    elif state.player_fallen_off():
        state = deepcopy(starting_state)
        screen.fill(RED)
        sleep(0.1)
        pygame.display.flip()
        sleep(0.2)

pygame.quit()