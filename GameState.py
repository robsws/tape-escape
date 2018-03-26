import configparser
from collections import defaultdict
import re

from Utils import *

DEFAULT_WIDTH=30
DEFAULT_HEIGHT=20

class LevelLoader:
    # Wraps around a config file and generates level states from it.

    def __init__(self, levels_file):
        self.config = configparser.ConfigParser()
        self.config.read(levels_file)

    def load_new_level_state(self, level_no):
        return GameState(level=self.config['Levels'][str(level_no)])

def add_border(position):
    return (position[0] + MAX_TAPE_LENGTH, position[1] + MAX_TAPE_LENGTH)

class GameState:

    def __init__(self, level='', width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        # Border of width MAX_TAPE_LENGTH is added so that tape end cannot go out of bounds.
        self.player_position = (MAX_TAPE_LENGTH, MAX_TAPE_LENGTH)
        self.player_direction = (0,-1)
        self.player_orientation = -1 # -1 for left, 1 for right
        self.tape_end_position = (MAX_TAPE_LENGTH, MAX_TAPE_LENGTH)
        self.circle_points = set() # TODO remove        
        self.blocks = defaultdict(list)
        self.force_win = False

        if level != '':
            self.init_grid_from_serialised(level)
        else:
            self.init_blank_grid(width + 2*MAX_TAPE_LENGTH, height + 2*MAX_TAPE_LENGTH)
        

    def init_blank_grid(self, width, height):
        # Build a blank grid of the given width and height
        self.grid_width = width
        self.grid_height = height
        self.grid = [[TileType.PIT for y in range(self.grid_height)] for x in range(self.grid_width)]
        self.goal_position = (self.grid_width-1, self.grid_height-1)
        self.update_block_grid()

    def init_grid_from_serialised(self, level):
        # Build the internal level grid from string representation
        lines = level.splitlines()
        self.init_blank_grid(len(lines[0]) + 2*MAX_TAPE_LENGTH, len(lines) + 2*MAX_TAPE_LENGTH)
        for y, line in enumerate(lines):
            for x, tile in enumerate(line):
                self.update_grid_square(x + MAX_TAPE_LENGTH, y + MAX_TAPE_LENGTH, tile)

    def serialize(self):
        # Serialize the state down to a string representation (reverse of init_grid_from_serialized)
        level_string = ''
        for y in range(MAX_TAPE_LENGTH, self.grid_height - MAX_TAPE_LENGTH):
            for x in range(MAX_TAPE_LENGTH, self.grid_width - MAX_TAPE_LENGTH):
                if self.block_grid[x][y] != '':
                    if self.grid[x][y] == TileType.SPACE:
                        level_string += self.block_grid[x][y].upper()
                    else:
                        level_string += self.block_grid[x][y]
                elif self.player_position == (x,y):
                    level_string += tiletype_to_sym_map[TileType.PLAYER]
                elif self.goal_position == (x,y):
                    level_string += tiletype_to_sym_map[TileType.GOAL]
                else:
                    level_string += tiletype_to_sym_map[self.grid[x][y]]
            level_string += '\n'
        return level_string

    def update_grid_square(self, x, y, tile):
        # blocks with the same alphabet letter move as a unit
        # upper case signifies a space beneath, lower case signifies a pit beneath
        if re.match(r'[A-Z]', tile):
            self.blocks[tile.lower()].append((x,y))
            self.grid[x][y] = TileType.SPACE
            self.update_block_grid()
        elif re.match(r'[a-z]', tile):
            self.blocks[tile].append((x,y))
            self.grid[x][y] = TileType.PIT
            self.update_block_grid()
        elif sym_to_tiletype_map[tile] == TileType.PLAYER:
            if self.block_grid[x][y] != '':
                # remove block (do this for other types too)
                self.blocks[self.block_grid[x][y]].remove((x,y))
                self.update_block_grid()
            self.player_position = (x,y)
            self.tape_end_position = (x,y)
            self.grid[x][y] = TileType.SPACE
        elif sym_to_tiletype_map[tile] == TileType.GOAL:
            if self.block_grid[x][y] != '':
                # remove block (do this for other types too)
                self.blocks[self.block_grid[x][y]].remove((x,y))
                self.update_block_grid()
            self.goal_position = (x,y)
            self.grid[x][y] = TileType.SPACE
        else:
            if self.block_grid[x][y] != '':
                # remove block (do this for other types too)
                self.blocks[self.block_grid[x][y]].remove((x,y))
                self.update_block_grid()
            self.grid[x][y] = sym_to_tiletype_map[tile]

    def update_block_grid(self):
        # Reset the lookup table
        self.block_grid = [['' for y in range(self.grid_height + 2*MAX_TAPE_LENGTH)] for x in range(self.grid_width + 2*MAX_TAPE_LENGTH)]
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
                # Block must not be the same one that is being pushed against!
                (
                    self.block_grid[next_player_position[0]][next_player_position[1]] == '' or
                    (
                        self.block_grid[next_player_position[0]][next_player_position[1]] != self.block_grid[next_tape_end_position[0]][next_tape_end_position[1]] and
                        self.block_grid[next_player_position[0]][next_player_position[1]] != self.block_grid[next_tape_edge_position[0]][next_tape_edge_position[1]]
                    )
                ) and
                tape_length != MAX_TAPE_LENGTH
            ):
                # First move any blocks the player is resting against.
                # Check if tape end is next to a block and whether it is obstructed or not.
                if (
                    player_next_to_block and not player_block_is_obstructed
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
            # Check if we can change orientation of the player and rotate
            alt_tape_edge_position = get_tape_edge_position(future_tape_end_position, direction, self.player_orientation*-1)
            if self.is_tape_edge_inside_wall_or_block(alt_tape_edge_position, direction):
                # Prevent player rotating and pass back the two positions either side of the tape edge as the obstructions.
                future_tape_edge_position_offset = vector_add(future_tape_edge_position, direction)     
                return set([future_tape_edge_position, future_tape_edge_position_offset])
            else:
                # Change player's orientation so they can rotate
                self.player_orientation *= -1

        # Scan across the bounding square whose sides are length t*2 where t = tape radius
        # and for each point, if it is a wall and is within the circle traced by the tape
        # it counts as an obstruction.
        # The bounding square is split into four quadrants (nw, sw, ne, se) and move will be limited
        # based on current direction and which quadrants contain an obstruction
        obstructions = defaultdict(set)
        self.circle_points = set()
        for x in range(max(0, self.player_position[0] - tape_arc_radius), min(self.player_position[0] + 1, self.grid_width)):
            for y in range(max(0, self.player_position[1] - tape_arc_radius), min(self.player_position[1] + 1, self.grid_height)):
                # Check for obstructions in North West quadrant
                if (self.grid[x][y] == TileType.WALL or self.block_grid[x][y] != '') and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((-1,0),(0,-1))].add((x,y)) # west to north
                    obstructions[((0,-1),(-1,0))].add((x,y)) # north to west
            for y in range(self.player_position[1], min(self.player_position[1] + tape_arc_radius, self.grid_height)):
                # Check for obstructions in South West quadrant
                if (self.grid[x][y] == TileType.WALL or self.block_grid[x][y] != '') and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((-1,0),(0,1))].add((x,y)) # west to south
                    obstructions[((0,1),(-1,0))].add((x,y)) # south to west
        for x in range(max(0, self.player_position[0]), min(self.player_position[0] + tape_arc_radius, self.grid_width)):
            for y in range(max(0, self.player_position[1] - tape_arc_radius), min(self.player_position[1] + 1, self.grid_height)):
                # Check for obstructions in North East quadrant
                if (self.grid[x][y] == TileType.WALL or self.block_grid[x][y] != '') and (x - self.player_position[0])**2 + (y - self.player_position[1])**2 < (tape_arc_radius)**2:
                    obstructions[((0,-1),(1,0))].add((x,y)) # north to east
                    obstructions[((1,0),(0,-1))].add((x,y)) # east to north
            for y in range(self.player_position[1], min(self.player_position[1] + tape_arc_radius, self.grid_height)):
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
        force_win = self.force_win
        self.force_win = False
        return force_win or self.player_position == self.tape_end_position == self.goal_position

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