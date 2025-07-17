# We use os to handle file paths in a platform-independent way
import os

# Import functions from our custom modules to handle different parts of the MILP process
from data_loader import load_data, get_time_of_use_rates
from model_builder import create_milp_model
from solver import solve_milp, extract_results, save_results, print_summary

# The main function orchestrates the entire optimization process from data loading to results output
def main():
    # Data file path - specifies location of the CSV containing time series data for solar production and load demand
    # Using os.path.join ensures correct path formatting across different operating systems
    data_file = os.path.join("..", "Data", "site1", "ComparisonDays", "2023-June-Solstice.csv")

    # Load_data - reads the CSV file and extracts relevant time series data for the optimization
    # The load_data function parses timestamps, solar production, and household demand
    print("Loading data...")
    data = load_data(data_file)
    print(f"Loaded {len(data['time'])} time steps")
    
    # Battery parameters - defines the technical specifications and constraints of the battery system
    # These parameters are based on the specific battery installation at site 1 (two B4850 batteries)
    # These values determine the battery's behavior in the optimization model
    battery_params = {
        'capacity_kwh': 4.8,    # two B4850s with total capacity of 4.8 kWh
        'min_soc': 0.11,        # 11% minimum State of Charge to prevent battery damage
        'max_soc': 1,           # 100% maximum State of Charge (fully charged)
        'initial_soc': 0.22,    # 22% initial State of Charge (should be matched to actual data for fair comparison)
        'charge_efficiency': 0.95,    # 95% efficiency when charging (accounts for energy losses)
        'discharge_efficiency': 0.95,  # 95% efficiency when discharging (accounts for energy losses)
        'max_charge_rate': 2780,    # 2780 W max charge rate - hardware limitation
        'max_discharge_rate': 2370,  # 2370 W max discharge rate - hardware limitation
    }
    
    # Cost parameters - defines the electricity pricing structure for the optimization
    # These values are based on Electric Ireland's 'Home electric + night boost' tariff rates in euros per kWh
    cost_params = {
        'day_rate': 0.3634,     # €0.3634/kWh grid purchase price during standard daytime hours
        'night_rate': 0.1792,   # €0.1792/kWh grid purchase price during night hours (cheaper)
        'boost_rate': 0.1052,    # €0.1052/kWh grid purchase price during night boost hours (cheapest)
        'sell_price': 0.195,     # €0.195/kWh feed-in tariff for selling excess solar power back to the grid
    }
    
    # Get time-of-use rates - creates a mapping between each time step and the appropriate electricity rate
    # This function assigns day/night/peak rates to each time period based on the hour of day
    # The resulting dictionary is used in the objective function to calculate accurate costs
    buy_rates = get_time_of_use_rates(data, cost_params)
    
    # Create model - builds the complete Mixed Integer Linear Programming (MILP) model using Gurobi
    # This function defines all decision variables, constraints, and the objective function
    # Returns both the model object and a dictionary containing all decision variables for later access
    print("Creating MILP model with Gurobi...")
    model, vars_dict = create_milp_model(data, battery_params, cost_params, buy_rates)
    
    # Solve model - uses Gurobi's optimization engine to find the optimal solution
    # We set a time limit of 300 seconds (5 minutes) and accept solutions within 1% of optimal (MIP gap)
    # These parameters balance solution quality with computation time
    print("Solving MILP model...")
    if solve_milp(model, time_limit=300, gap=0.01):  # 5 minutes time limit, 1% MIP gap
        print("Model solved successfully!")
        
        # Extract results - pulls the optimal values from the solved model into a structured dictionary
        # This includes all power flows, battery state of charge, and other key metrics
        results = extract_results(model, vars_dict, data, battery_params)

        # Save results - writes the optimization results to a CSV file for later analysis
        # The default output file is 'optimization_results.csv'
        save_results(results)

        # Print summary - displays key performance metrics from the optimization
        # This includes total cost, average battery state of charge, and energy flows
        print_summary(results)
        
    else:
        print("Failed to solve the model")

    # This is the standard Python idiom to ensure the main() function is only executed when
    # the script is run directly (not when imported as a module)
if __name__ == "__main__":
    main()
