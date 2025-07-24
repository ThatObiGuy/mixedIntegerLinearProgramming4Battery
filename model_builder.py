# We use gurobipy to create and solve our MILP model for optimizing the PV/Battery system
import gurobipy as gp
from gurobipy import GRB  # We need GRB for setting objective and constraint types
from config import setup_gurobi_env  # Import the function to set up Gurobi environment

# This function creates a complete MILP model with all variables, constraints, and objective function
def create_milp_model(data, battery_params, cost_params, buy_rates):

    # Set up Gurobi environment with academic license configuration
    setup_gurobi_env()

    # Create a new Gurobi optimization model
    model = gp.Model("PV_Battery_Optimization")

    # Calculate the number of time steps from the data and create a range for iteration
    T = len(data['time'])
    time_steps = range(T)  # This will be used throughout the model to iterate over all time periods

    # Define continuous decision variables for power flows between components (all non-negative)
    P_solar_household = model.addVars(time_steps, lb=0, name="P_solar_household")  # Power from solar to household
    P_solar_battery = model.addVars(time_steps, lb=0, name="P_solar_battery")      # Power from solar to battery
    P_solar_grid = model.addVars(time_steps, lb=0, name="P_solar_grid")          # Power from solar to grid
    P_battery_household = model.addVars(time_steps, lb=0, name="P_battery_household")  # Power from battery to household
    P_grid_battery = model.addVars(time_steps, lb=0, name="P_grid_battery")      # Power from grid to battery
    P_grid_household = model.addVars(time_steps, lb=0, name="P_grid_household")  # Power from grid to household
    SE = model.addVars(time_steps, lb=0, name="SE")  # Stored energy in the battery at each time step

    # Binary variables to prevent simultaneous charging and discharging of the battery
    BC = model.addVars(time_steps, vtype=GRB.BINARY, name="BC")  # BC[t] = 1 if battery is charging at time t
    BD = model.addVars(time_steps, vtype=GRB.BINARY, name="BD")  # BD[t] = 1 if battery is discharging at time t

    # Binary variable to prevent bidirectional flow through the grid
    GF = model.addVars(time_steps, vtype=GRB.BINARY, name="GF")  # GF[t] = 1 if power is flowing FROM the grid at time t

    # Objective function: Minimize the total electricity cost over all time periods
    # Cost = (Power purchased from grid × buy rate) - (Power sold to grid × sell price)
    # Convert from watts to kWh for 5-minute intervals: multiply by (5/60)/1000 = 1/12000
    conversion_factor = (5/60)/1000  # 5 min to hours, then watts to kilowatts
    obj = gp.quicksum((P_grid_household[t] + P_grid_battery[t]) * conversion_factor * buy_rates[t]  -
                      P_solar_grid[t] * conversion_factor * cost_params['sell_price'] 
                      for t in time_steps)
    # Set the model's objective function to minimize the total cost
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # 1. Solar power balance constraints - ensures all solar production is accounted for
    for t in time_steps:
        # All solar power produced must be distributed to household, battery, or grid
        # Solar output must equal the sum of all outgoing solar power flows
        model.addConstr(
            P_solar_household[t] + P_solar_battery[t] + P_solar_grid[t] == data['solar_production'][t],
            name=f"solar_balance_{t}"
        )

    # 2. Load demand satisfaction constraints - ensures household energy needs are met
    for t in time_steps:
        # The total power supplied to the household must meet the demand
        # Power can come from solar panels, battery, or grid
        model.addConstr(
            P_solar_household[t] + P_battery_household[t] + P_grid_household[t] == data['load_demand'][t],
            name=f"load_balance_{t}"
        )

    # 3. Battery dynamics constraints - track battery state of charge over time
    # Convert from watts to kWh for 5-minute intervals
    conversion_factor = (5/60)/1000  # 5 min to hours, then watts to kilowatts

    for t in time_steps:
        if t == 0:
            # Special case for initial time step (t=0) - use the specified initial SoC
            # Initial stored energy = initial SoC + charging - discharging
            # Note: charging is multiplied by efficiency (< 1) and discharging is divided by efficiency (< 1)
            # Convert power (watts) to energy (kWh) using the conversion factor
            model.addConstr(
                SE[t] == battery_params['initial_soc'] * battery_params['capacity_kwh'] +
                (P_solar_battery[t] + P_grid_battery[t]) * conversion_factor * battery_params['charge_efficiency'] - 
                P_battery_household[t] * conversion_factor / battery_params['discharge_efficiency'],
                name=f"battery_dynamics_{t}"
            )
        else:
            # For all other time steps: current SoC = previous SoC + charging - discharging
            # Convert power (watts) to energy (kWh) using the conversion factor
            model.addConstr(
                SE[t] == SE[t-1] +
                (P_solar_battery[t] + P_grid_battery[t]) * conversion_factor * battery_params['charge_efficiency'] - 
                P_battery_household[t] * conversion_factor / battery_params['discharge_efficiency'],
                name=f"battery_dynamics_{t}"
            )

    # 4. Battery capacity limit constraints - ensure battery SoC stays within allowed range
    for t in time_steps:
        # Minimum state of charge constraint - prevents battery from discharging too low
        model.addConstr(
            SE[t] >= battery_params['min_soc'] * battery_params['capacity_kwh'],
            name=f"soc_min_{t}"
        )# TODO: Revisit this
        # Maximum state of charge constraint - prevents battery from overcharging
        model.addConstr(
            SE[t] <= battery_params['max_soc'] * battery_params['capacity_kwh'],
            name=f"soc_max_{t}"
        )

    # 5. Charging rate limit constraints - ensure battery charging doesn't exceed hardware limits
    for t in time_steps:
        # Total charging power (from solar + grid) cannot exceed the maximum charging rate
        model.addConstr(
            P_solar_battery[t] + P_grid_battery[t] <= battery_params['max_charge_rate'],
            name=f"charge_limit_{t}"
        )

    # 6. Discharging rate limit constraints - ensure battery discharging doesn't exceed hardware limits
    for t in time_steps:
        # Discharging power to household cannot exceed the maximum discharge rate
        model.addConstr(
            P_battery_household[t] <= battery_params['max_discharge_rate'],
            name=f"discharge_limit_{t}"
        )

    # 7. Binary constraints for charging/discharging - link power flows to binary variables
    for t in time_steps:
        # If charging power > 0, then BC[t] must be 1; if BC[t] = 0, then charging power must be 0
        # This constraint links the continuous charging power to the binary charging variable
        model.addConstr(
            P_solar_battery[t] + P_grid_battery[t] <= BC[t] * battery_params['max_charge_rate'],
            name=f"charge_binary_{t}"
        )
        # If discharging power > 0, then BD[t] must be 1; if BD[t] = 0, then discharging power must be 0
        # This constraint links the continuous discharging power to the binary discharging variable
        model.addConstr(
            P_battery_household[t] <= BD[t] * battery_params['max_discharge_rate'],
            name=f"discharge_binary_{t}"
        )

    # 8. No simultaneous charge/discharge constraints - prevents battery from charging and discharging at the same time
    for t in time_steps:
        # The sum of binary variables must be <= 1, meaning battery can either:
        # - Charge (BC[t] = 1, BD[t] = 0)
        # - Discharge (BC[t] = 0, BD[t] = 1)
        # - Do neither (BC[t] = 0, BD[t] = 0)
        # But never both charge and discharge simultaneously
        model.addConstr(
            BC[t] + BD[t] <= 1,
            name=f"no_simultaneous_{t}"
        )

    # 9. Grid flow direction constraints - prevents bidirectional flow through the grid
    for t in time_steps:
        # If power is flowing FROM the grid (P_grid_household or P_grid_battery > 0), then GF[t] must be 1
        # This constraint links the continuous grid power flow variables to the binary grid flow direction variable
        model.addConstr(
            P_grid_household[t] + P_grid_battery[t] <= GF[t] * (battery_params['max_charge_rate'] + max(data['load_demand'])),
            name=f"grid_flow_from_{t}"
        )

        # If power is flowing TO the grid (P_solar_grid > 0), then GF[t] must be 0
        # This constraint ensures that power can't flow TO the grid when GF[t] = 1
        model.addConstr(
            P_solar_grid[t] <= (1 - GF[t]) * max(data['solar_production']),
            name=f"grid_flow_to_{t}"
        )

    # The function returns two items:
    # 1. The complete Gurobi model ready to be solved
    # 2. A dictionary containing all decision variables for easy access after optimization
    return model, {
        'P_solar_household': P_solar_household,  # Power flow from solar to household
        'P_solar_battery': P_solar_battery,      # Power flow from solar to battery
        'P_solar_grid': P_solar_grid,            # Power flow from solar to grid
        'P_battery_household': P_battery_household,  # Power flow from battery to household
        'P_grid_battery': P_grid_battery,        # Power flow from grid to battery
        'P_grid_household': P_grid_household,    # Power flow from grid to household
        'SE': SE,                                # Battery stored energy at each time step
        'BC': BC,                                # Binary variable indicating charging
        'BD': BD,                                # Binary variable indicating discharging
        'GF': GF                                 # Binary variable indicating grid flow direction (1 if FROM grid)
    }
