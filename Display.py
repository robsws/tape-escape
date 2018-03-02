import pygame
from time import sleep

from Utils import *
from GameState import GameState

BLACK       =   0,   0,   0
DARK_GREY   =  30,  30,  30
LIGHT_GREY  = 100, 100, 100
SILVER      = 200, 200, 200
RED         = 150,   0,   0
YELLOW      = 150, 150,   0
LIGHT_GREEN =  51, 255, 153
BROWN       = 204, 102,   0

class Display:

    def __init__(self, screen, display_rect):
        self.screen = screen
        self.x_offset, self.y_offset, self.width, self.height = display_rect

    def render_state(self, state):
        # Work out how big the tiles should be to fit on the given screen size
        tile_width = int(self.width/state.grid_width)
        tile_border = int(tile_width/8)
        # Reset screen to black
        self.screen.fill(BLACK)
        # Draw the grid and the static objects to the pygame screen
        for x in range(state.grid_width):
            for y in range(state.grid_height):
                tiletype = state.grid[x][y]
                if tiletype == TileType.SPACE:
                    self.screen.fill(DARK_GREY, [self.x_offset + x * tile_width + tile_border, self.y_offset + y * tile_width + tile_border, tile_width - tile_border*2, tile_width - tile_border*2], 0)              
                elif tiletype == TileType.WALL:
                    self.screen.fill(LIGHT_GREY, [self.x_offset + x * tile_width + tile_border, self.y_offset + y * tile_width + tile_border, tile_width - tile_border*2, tile_width - tile_border*2], 0)
                    # Filling in gaps between adjacent wall tiles.
                    if x < state.grid_width - 1 and state.grid[x+1][y] == TileType.WALL:
                        self.screen.fill(LIGHT_GREY, [self.x_offset + (x + 1) * tile_width - tile_border, self.y_offset +  y * tile_width + tile_border, tile_border*2, tile_width - tile_border*2], 0)
                    if y < state.grid_height - 1 and state.grid[x][y+1] == TileType.WALL:
                        self.screen.fill(LIGHT_GREY, [self.x_offset + x * tile_width + tile_border, self.y_offset + (y + 1) * tile_width - tile_border, tile_width - tile_border*2, tile_border*2], 0)

                if (x, y) in state.circle_points:
                    pygame.draw.circle(self.screen, BLACK, (self.x_offset + int(x * tile_width + tile_width/2), self.y_offset + int(y * tile_width + tile_width/2)), 4, 0)

        # Draw goal
        self.screen.fill(LIGHT_GREEN, [self.x_offset + state.goal_position[0] * tile_width + tile_border, self.y_offset + state.goal_position[1] * tile_width + tile_border, tile_width - tile_border*2, tile_width - tile_border*2], 0)

        # Draw blocks
        for block_key in state.blocks.keys():
            for position in state.blocks[block_key]:
                self.screen.fill(BROWN, [self.x_offset + position[0] * tile_width + tile_border, self.y_offset + position[1] * tile_width + tile_border, tile_width - tile_border*2, tile_width - tile_border*2], 0)
                if position[0] < state.grid_width - 1 and state.block_grid[position[0]+1][position[1]] == block_key:
                    self.screen.fill(BROWN, [self.x_offset + (position[0] + 1) * tile_width - tile_border, self.y_offset + position[1] * tile_width + tile_border, tile_border*2, tile_width - tile_border*2], 0)
                if position[1] < state.grid_height - 1 and state.block_grid[position[0]][position[1]+1] == block_key:
                    self.screen.fill(BROWN, [self.x_offset + position[0] * tile_width + tile_border, self.y_offset + (position[1] + 1) * tile_width - tile_border, tile_width - tile_border*2, tile_border*2], 0)

        # Draw rotation obstructions
        for x in range(state.grid_width):
            for y in range(state.grid_height):
                if self.obstruction_coords != None and (x, y) in self.obstruction_coords:
                    self.screen.fill(RED, [self.x_offset + x * tile_width + tile_border, y * tile_width + tile_border, self.y_offset + tile_width - tile_border*2, tile_width - tile_border*2], 0)

        # Draw player
        tape_end_centre = (self.x_offset + int(state.tape_end_position[0] * tile_width + tile_width/2) + (state.player_direction[0] * tile_width/2), self.y_offset + int(state.tape_end_position[1] * tile_width + tile_width/2) + (state.player_direction[1] * tile_width/2))
        tape_edge_offset = vector_scalar_multiply(rotate_right(state.player_direction), state.player_orientation * tile_width * 0.66) 
        tape_edge = vector_add(tape_end_centre, tape_edge_offset)
        player_screen_position = (self.x_offset + int(state.player_position[0] * tile_width + tile_width/2), self.y_offset + int(state.player_position[1] * tile_width + tile_width/2))
        pygame.draw.line(self.screen, YELLOW, tape_end_centre, player_screen_position, 2)
        pygame.draw.line(self.screen, SILVER, tape_end_centre, tape_edge, 2)
        pygame.draw.circle(self.screen, RED, player_screen_position, int(tile_width/2), 0)
        
        # Swap the buffers
        pygame.display.flip()

    def flash(self, colour):
        self.screen.fill(colour)
        sleep(0.1)
        pygame.display.flip()
        sleep(0.2)

    def flash_green(self):
        self.flash(LIGHT_GREEN)

    def flash_red(self):
        self.flash(RED)