# We use pandas to create the results DataFrame
import pandas as pd

# We use numpy for to get the mean SoC of battery at the end.
import numpy as np

# We use gurobipy to access the Gurobi solver and its status codes
import gurobipy as gp
from gurobipy import GRB  # We need GRB for checking solution status

# This function solves the MILP model using Gurobi
def solve_milp(model, time_limit=None, gap=None, verbose=True):
    # model             - comes from model_builder.py
    # time_limit=None   - By default Gurobi will work until the maximum time to find the optimal solution
    # gap=None          - used to control how close to optimal solution gurobi will stop, by default "None" means our program won't stop until 100% optimal.
    # verbose=True      - By default indicates to shows progress information

    try:
        # Set solver parameters - these control how long Gurobi will search for a solution
        if time_limit is not None:
            model.setParam('TimeLimit', time_limit)  # Maximum time in seconds for the optimization
        if gap is not None:
            model.setParam('MIPGap', gap)  # Relative MIP gap tolerance - smaller values produce more optimal solutions

        # Set output level - controls how much information Gurobi displays during optimization
        if verbose:
            model.setParam('OutputFlag', 1)  # Show detailed solver output for debugging and analysis
        else:
            model.setParam('OutputFlag', 0)  # Hide solver output for cleaner program execution

        # Optimize the model - this starts the Gurobi solver to find the optimal solution
        model.optimize()

        # Check solution status - the solver might find an optimal solution, run out of time, or encounter other issues
        if model.status == GRB.OPTIMAL:
            # Found the mathematically optimal solution for the model
            print(f"Optimal solution found with objective value: {model.objVal}")
            return True
        elif model.status == GRB.TIME_LIMIT:
            # Hit the time limit before finding the proven optimal solution
            print(f"Time limit reached with best objective value: {model.objVal}")
            return True if model.SolCount > 0 else False  # Return True only if we found at least one feasible solution
        else:
            # Other outcomes: infeasible, unbounded, or numerical issues
            print(f"Optimization failed with status code: {model.status}")
            return False

    except gp.GurobiError as e:
        # Handle specific Gurobi errors, such as license issues, parameter errors, etc.
        print(f"Gurobi error: {e}")
        return False
    except Exception as e:
        # Handle any other unexpected errors that might occur during optimization
        print(f"Error solving model: {e}")
        return False

# This function extracts and formats results from solved model
def extract_results(model, vars_dict, data, battery_params):

    # This function collects all optimization results into a structured dictionary
    # for easier analysis, visualization, and storage
    results = {}

    # Time series results - include original input data for reference and comparison
    time_steps = range(len(data['time']))  # Create a range iterator for all time periods
    results['time'] = data['time']  # Original timestamps from input data
    results['solar_production'] = data['solar_production']  # Original solar production values
    results['load_demand'] = data['load_demand']  # Original household demand values

    # Optimal power flows - extract the decision variable values from the solved model
    # For each variable, we create a list containing the value at each time step
    # The .X attribute gives us the optimal value of the Gurobi variable
    results['P_solar_household'] = [vars_dict['P_solar_household'][t].X for t in time_steps]  # Power from solar to household
    results['P_solar_battery'] = [vars_dict['P_solar_battery'][t].X for t in time_steps]    # Power from solar to battery
    results['P_solar_grid'] = [vars_dict['P_solar_grid'][t].X for t in time_steps]          # Power from solar to grid
    results['P_battery_household'] = [vars_dict['P_battery_household'][t].X for t in time_steps]  # Power from battery to household
    results['P_grid_battery'] = [vars_dict['P_grid_battery'][t].X for t in time_steps]      # Power from grid to battery
    results['P_grid_household'] = [vars_dict['P_grid_household'][t].X for t in time_steps]  # Power from grid to household
    results['SE'] = [vars_dict['SE'][t].X for t in time_steps]  # Stored energy in the battery at each time step
    results['SoC'] = [vars_dict['SE'][t].X / battery_params['capacity_kwh'] * 100 for t in time_steps]  # Battery state of charge as percentage

    # Binary variables - extract the values of charging and discharging indicators
    results['BC'] = [vars_dict['BC'][t].X for t in time_steps]  # Battery charging indicator (1 if charging at time t)
    results['BD'] = [vars_dict['BD'][t].X for t in time_steps]  # Battery discharging indicator (1 if discharging at time t)
    results['GF'] = [vars_dict['GF'][t].X for t in time_steps]  # Grid flow direction indicator (1 if FROM grid at time t)

    # Objective value - the total electricity cost from the optimal solution
    results['total_cost'] = model.objVal  # This is the minimized total cost in currency units

    return results

# This function saves results to CSV file
def save_results(results, output_file='optimization_results.csv'):

    # Convert the results dictionary to a pandas DataFrame for easy export
    df = pd.DataFrame(results)

    # Save the DataFrame to a CSV file - this makes it easy to import into other tools
    # for further analysis and visualization
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")

# This function prints a summary of the optimization results
def print_summary(results):

    # This function provides a concise overview of the key optimization results
    # for quick assessment of the system performance
    print(f"\nOptimization Summary:")
    print(f"Total Cost: ${results['total_cost']:.2f}")  # The total electricity cost (objective value)
    print(f"Average SoC: {np.mean(results['SoC']):.1f}%")  # Average battery state of charge across all time periods

    # Convert from watts to kWh for 5-minute intervals
    conversion_factor = (5/60)/1000  # 5 min to hours, then watts to kilowatts

    # Display energy values in kWh
    print(f"Total Solar Production: {sum(results['solar_production']) * conversion_factor:.2f} kWh")  # Total energy produced by solar panels
    print(f"Total Load Demand: {sum(results['load_demand']) * conversion_factor:.2f} kWh")  # Total household energy consumption
    print(f"Total Grid Purchase: {sum(results['P_grid_household']) * conversion_factor:.2f} kWh")  # Total energy purchased from the grid
    print(f"Total Solar Export: {sum(results['P_solar_grid']) * conversion_factor:.2f} kWh")  # Total excess solar energy sold to the grid
