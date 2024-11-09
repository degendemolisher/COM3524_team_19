# Name: Wildfire
# Dimensions: 2

# --- Set up executable path, do not edit ---
import sys
import inspect
this_file_loc = (inspect.stack()[0][1])
main_dir_loc = this_file_loc[:this_file_loc.index('ca_descriptions')]
sys.path.append(main_dir_loc)
sys.path.append(main_dir_loc + 'capyle')
sys.path.append(main_dir_loc + 'capyle/ca')
sys.path.append(main_dir_loc + 'capyle/guicomponents')
# ---

from capyle.ca import Grid2D, Neighbourhood, randomise2d
import capyle.utils as utils
import numpy as np

S_10 = 0
S_11 = 1
S_12 = 2
S_20 = 3
S_21 = 4
S_22 = 5
S_30 = 6
S_31 = 7
S_32 = 8
S_40 = 9
S_41 = 10
S_42 = 11

# Types: 0* = canyon scrubland, 1* = chaparral, 2* = dense forest, 3* = lake
# States: alive = *0, burning = *1, burnt = *2
STATES = (S_10, S_11, S_12, # canyon scrubland
          S_20, S_21, S_22, # chaparral
          S_30, S_31, S_32, # dense forest
          S_40, S_41, S_42) # lake
GRID = (50, 50)
GENERATIONS = 100


def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16)/256 for i in (0, 2, 4))

def setup(args):
    """Set up the config object used to interact with the GUI"""
    config_path = args[0]
    config = utils.load(config_path)
    # -- THE CA MUST BE RELOADED IN THE GUI IF ANY OF THE BELOW ARE CHANGED --
    config.title = "Wildfire"
    config.dimensions = 2
    config.states = STATES
    # -------------------------------------------------------------------------

    # ---- Override the defaults below (these may be changed at anytime) ----

    config.state_colors = [hex_to_rgb('#FDFF07'), hex_to_rgb('#891A0A'), hex_to_rgb('#505001'), # canyon scrubland
                            hex_to_rgb('#BFBE02'), hex_to_rgb('#891A0A'), hex_to_rgb('#3B3B01'), # chaparral
                            hex_to_rgb('#506228'), hex_to_rgb('#891A0A'), hex_to_rgb('#191E0C'), # dense forest
                            hex_to_rgb('#01AFF1'), hex_to_rgb('#891A0A'), hex_to_rgb('#00364B')] # lake
    config.grid_dims = GRID
    config.num_generations = GENERATIONS
    config.wrap = False
    
    # ----------------------------------------------------------------------

    # the GUI calls this to pass the user defined config
    # into the main system with an extra argument
    # do not change
    if len(args) == 2:
        config.save()
        sys.exit()
    return config


def transition_function(grid, neighbourstates, neighbourcounts) -> tuple:
    """Function to apply the transition rules
    and return the new grid"""
    
    # __________WIND STUFF__________
    # wind multiplier
    multi = 0.3
    # burn chance facing wind
    M = 1 + multi
    # burn chance against wind
    m = 1 - multi
    
    # multiplier vector for each wind direction
    # [NW, N, NE, 
    #  W,     E, 
    #  SW, S, SE]
    north_multi = [M, M, M,
                   1,    1, 
                   m, m, m]
    
    east_multi  = [m, 1, M,
                   m,    M,
                   m, 1, M]
    
    south_multi = [m, m, m,
                   1,    1,
                   M, M, M]
    
    west_multi  = [M, 1, m,
                   M,    m,
                   M, 1, m]
    # ______________________________
    
    # TODO: burning mask (only check for burning cells)
    
    # no. burning neighbours
    burning_counts = neighbourcounts[S_11] + neighbourcounts[S_21] + neighbourcounts[S_31] + neighbourcounts[S_41]
    # cell has (# burning neighbours * 0.1) probability to catch fire
    # cell has to be alive
    catch_fire = (grid % 3 == 0) & (np.random.rand(*grid.shape) < burning_counts * 0.1)
    grid[catch_fire] += 1
    
    # probablity of burning cell to burn out
    burn_out = (grid % 3 == 1) & (np.random.rand(*grid.shape) < 0.1)
    grid[burn_out] += 1
    
    return grid


def main():
    """ Main function that sets up, runs and saves CA"""
    # Get the config object from set up
    config = setup(sys.argv[1:])

    # Create grid object using parameters from config + transition function
    grid = Grid2D(config, transition_function)

    # Run the CA, save grid state every generation to timeline
    timeline = grid.run()

    # Save updated config to file
    config.save()
    # Save timeline to file
    utils.save(timeline, config.timeline_path)

if __name__ == "__main__":
    main()
