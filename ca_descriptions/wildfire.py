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
S_50 = 12

# Types: 0* = canyon scrubland, 1* = chaparral, 2* = dense forest, 3* = lake
# States: alive = *0, burning = *1, burnt = *2
STATES = (S_10, S_11, S_12, # canyon scrubland
          S_20, S_21, S_22, # chaparral
          S_30, S_31, S_32, # dense forest
          S_40, S_41, S_42, # lake
          S_50) # town

GRID = (500, 500)
# each timestep is 1 hour
GENERATIONS = 500

WIND = {
    "direction": "N",
    "speed": 0.999  # in [0, 1]
}

BURNING = {
    "time": [
        3, # canyon scrubland
        15, # chaparral
        200, # dense forest
        0 # lake
    ],
    "prob": {
        "max": [
            1, # canyon scrubland
            0.7, # chaparral
            0.2, # dense forest
            0 # lake
        ],
        "min": [
            0.5, # canyon scrubland
            0.3, # chaparral
            0.05, # dense forest
            0 # lake
        ]
    }
}

global burning_time
burning_time = np.zeros(GRID)

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
                            hex_to_rgb('#01AFF1'), hex_to_rgb('#891A0A'), hex_to_rgb('#00364B'), # lake
                            hex_to_rgb('#000000')] # town
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

    # ____________BURNOUT RULES____________
    # burning tick, decrement burning time
    global burning_time
    burning_time = np.maximum(burning_time - 1, 0)

    # burn out burning cells if burning time is 0
    grid[(grid % 3 == 1) & (burning_time == 0)] += 1
    # ______________________________________

    # current_alive = (grid % 3 == 0)
    # current_burning = (grid % 3 == 1)
    # current_burnt = (grid % 3 == 2)
    
    # __________WIND STUFF__________
    # TODO: wind direction, use in ignition rules
    # wind multiplier
    multi = WIND["speed"]
    # burn chance facing wind
    M = 1 + min(1, multi)
    # burn chance against wind
    m = 1 - min(1, multi)
    
    # multiplier vector for each wind direction
    # [NW, N, NE, 
    #  W,     E, 
    #  SW, S, SE]
    WIND_MULTI = {
        "N": [M, M, M,
              1,    1, 
              m, m, m],
        
        "E": [m, 1, M,
              m,    M,
              m, 1, M],
        
        "S": [m, m, m,
              1,    1,
              M, M, M],
        
        "W": [M, 1, m,
              M,    m,
              M, 1, m],
    }
    # ______________________________

    # ____________IGNITION RULES____________
    # alive cell has (min_prob + (sum(burning_neighbours_multiplier) / 8) * (max_prob - min_prob)) probability to catch fire
    # zero out non burning cells
    neighbour_contrib = neighbourstates * (neighbourstates % 3 == 1)
    # make contributions 1
    neighbour_contrib[neighbour_contrib > 0] = 1
    # wind multiplier
    neighbour_contrib = np.tensordot(neighbour_contrib, WIND_MULTI[WIND["direction"]], axes=([0], [0]))
    # normalise neighbour_contrib
    ignition_prob_mod = neighbour_contrib / 8
    for i, state in enumerate([S_10, S_20, S_30, S_40]):
        cells_to_check = grid == state
        ignition_prob = BURNING["prob"]["min"][i] + ignition_prob_mod * (BURNING["prob"]["max"][i] - BURNING["prob"]["min"][i])
        # set ignition prob to 0 if burning counts is 0
        ignition_prob[ignition_prob_mod == 0] = 0
        catch_fire = cells_to_check & (np.random.rand(*grid.shape) < ignition_prob)
        grid[catch_fire] += 1
        burning_time[catch_fire] = np.rint(BURNING["time"][i] * np.random.uniform(0.8, 1.2))
    # ______________________________________
    
    return grid

def create_initial_state(grid: Grid2D) -> Grid2D:
    """Create the initial state of the grid"""
    chaparral_state = S_20
    lake_state = S_40
    dense_forest_state = S_30
    canyon_scrubland_state = S_10

    # Scaling factor (50x50 to 500x500)
    scale = 10

    # Set chaparral areas (yellow background in the 50x50 grid)
    grid.grid[:, :] = chaparral_state

    # HOW [ROW:COL]

    # Set dense forest (dark green area on 50x50 grid)
    grid.grid[15*scale:20*scale, 30*scale:int(42.5*scale)] = dense_forest_state # right rectangle
    grid.grid[int(7.5*scale):10*scale, 0*scale:10*scale] = dense_forest_state # left rectangle
    grid.grid[int(7.5*scale):40*scale, 10*scale:20*scale] = dense_forest_state # middle rectangle

    # Set lake (blue area on 50x50 grid)
    grid.grid[40*scale:int(42.5*scale), 15*scale:30*scale] = lake_state # left lake
    grid.grid[int(27.5*scale):40*scale, int(42.5*scale):45*scale] = lake_state # right lake

    # Set canyon scrubland (light green area on 50x50 grid)
    grid.grid[int(22.5*scale):25*scale, 25*scale:int(42.5*scale)] = canyon_scrubland_state # left scrubland

    # Set town (black area on 50x50 grid)
    grid.grid[int(34*scale):int(36.25*scale), 24*scale:int(26.25*scale)] = S_50

    # set initial burning cells
    set_initial_burning_cells(grid, scale)

    return grid

def set_initial_burning_cells(grid: Grid2D, scale: int):
    """Set the initial burning cells in the grid"""
    
    # Set burning cells at the power plant and proposed incinerator
    grid.grid[15*scale, 5*scale] += 1
    grid.grid[0, int(49.9*scale)] += 1

    # set init burning cells time
    global burning_time
    # iter thru all burning states and set their time
    for i, state in enumerate([S_11, S_21, S_31, S_41]):
        # get cells of each land type (burning)
        burning = grid.grid == state
        burning_time[burning] = BURNING["time"][i]

def create_testing_grid(grid: Grid2D) -> Grid2D:
    """Grid for control testing"""
    # make 125x500 grid for each land type
    grid.grid[:, 0:125] = S_10
    grid.grid[:, 125:250] = S_20
    grid.grid[:, 250:375] = S_30
    grid.grid[:, 375:500] = S_40
    # create boundaries with S_40 (lake)
    grid.grid[:, 124] = S_40
    grid.grid[:, 249] = S_40
    grid.grid[:, 374] = S_40
    grid.grid[249:250, :] = S_40
    # set initial burning cells at both ends of strips
    grid.grid[0, 0 + 62] += 1
    grid.grid[499, 0 + 62] += 1
    grid.grid[0, 125 + 62] += 1
    grid.grid[499, 125 + 62] += 1
    grid.grid[0, 250 + 62] += 1
    grid.grid[499, 250 + 62] += 1
    grid.grid[0, 375 + 62] += 1
    grid.grid[499, 375 + 62] += 1
    
    # set initial burning cells time
    global burning_time
    # iter thru all burning states and set their time
    for i, state in enumerate([S_11, S_21, S_31, S_41]):
        # get cells of each land type (burning)
        burning = grid.grid == state
        burning_time[burning] = BURNING["time"][i]

    return grid


def main():
    """ Main function that sets up, runs and saves CA"""
    # Get the config object from set up
    config = setup(sys.argv[1:])

    # Create grid object using parameters from config + transition function
    grid = Grid2D(config, transition_function)
    # Create the initial state of the grid
    grid = create_testing_grid(grid)

    # Run the CA, save grid state every generation to timeline
    timeline = grid.run()

    # Save updated config to file
    config.save()
    # Save timeline to file
    utils.save(timeline, config.timeline_path)

if __name__ == "__main__":
    main()
