import os
import pandas as pd
import sys
from main import cost_params

def load_csv_data(file_path):
    """
    Load and process data from a CSV file
    """
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)

        # Convert time column to datetime objects
        df['time'] = pd.to_datetime(df['time'])

        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

def calculate_summary(df, cost_params):
    """
    Calculate summary metrics based on the data and specified rates
    """
    # Define time interval
    time_diff = 5/60

    # Map the MILP CSV columns to the expected columns for calculations
    # P_source_destination is the naming scheme in the MILP CSV
    # Extract relevant columns, filling NaN values with 0

    # All P_grid_x represent power from grid (purchasing power)
    purchasing_power = df['P_grid_household'].fillna(0).values + df['P_grid_battery'].fillna(0).values

    # P_solar_grid is power from solar to grid (feed in power)
    feed_in_power = df['P_solar_grid'].fillna(0).values

    # load_demand is the consumption power
    consumption_power = df['load_demand'].fillna(0).values

    # solar_production is the production power
    production_power = df['solar_production'].fillna(0).values

    # Calculate total energy purchased from grid (kWh)
    # Convert from watts to kWh by multiplying by time interval (hours) and dividing by 1000
    total_energy_purchased = sum(purchasing_power) * time_diff / 1000

    # Calculate total energy produced by the household in kWh
    total_energy_produced = sum(production_power) * time_diff / 1000

    # Calculate total energy sold to grid (kWh)
    # Convert from watts to kWh by multiplying by time interval (hours) and dividing by 1000
    total_energy_sold = sum(feed_in_power) * time_diff / 1000

    # Calculate total cost of energy purchased (euros) using time-of-use rates
    # Convert from watts to kilowatts and multiply by time interval and appropriate rate
    total_cost = 0
    for i, timestamp in enumerate(df['time']):
        hour = timestamp.hour
        # Determine the appropriate rate based on time of day
        if 17 <= hour < 19:  # Peak: 17:00 to 19:00
            rate = cost_params['peak_rate']
        elif 23 <= hour or hour < 8:  # Night: 23:00 to 08:00
            rate = cost_params['night_rate']
        else:  # Day: all other times
            rate = cost_params['day_rate']

        # Loop to make up total cost
        if i < len(purchasing_power):
            total_cost += purchasing_power[i] * (time_diff / 1000) * rate

    total_cost = round(total_cost, 2)

    # Calculate total revenue from selling energy back to the grid (euros)
    # total_energy_sold is already in kWh, so just multiply by the sell price
    total_revenue = round(total_energy_sold * cost_params['sell_price'], 2)

    # Calculate system independence from grid (percent)

    # Convert from watts to kWh
    total_consumption = sum(consumption_power) * time_diff / 1000
    # grid_consumption == total_energy_purchased

    if total_consumption > 0:
        # Calculate independence as the percentage of consumption not met by grid
        independence_percent = min(100, (1 - total_energy_purchased / total_consumption) * 100)
    else:
        independence_percent = 100  # If no consumption, system is 100% independent

    # Calculate CO2 emissions reduced
    # Formula: (consumption from grid - solar production) * GEF
    # Convert from watts to kWh
    production_power_kwh = sum(production_power) * time_diff / 1000

    # Grid Emission Factor: 0.331 kg CO2 per kWh - Irish average
    gef = 0.331
    # total_solar_utilized is already in kWh
    co2_produced = total_energy_purchased * gef

    return {
        'total_energy_consumed' : total_consumption,
        'total_energy_purchased': total_energy_purchased,
        'total_cost': total_cost,
        'total_energy_produced': total_energy_produced,
        'total_energy_sold': total_energy_sold,
        'total_revenue': total_revenue,
        'net_cost': total_cost - total_revenue,
        'independence_percent': independence_percent,
        'co2_produced': co2_produced
    }

def print_summary(summary):
    """
    Print the summary metrics in a formatted way - .2f means fixed-point number with 2 decimal places
    """
    print("\nEnergy System Summary:")
    print(f"Total energy consumed by household: {summary['total_energy_consumed']:.2f} kWh")
    print(f"Total energy purchased from the grid: {summary['total_energy_purchased']:.2f} kWh")
    print(f"Total cost of energy purchased: €{summary['total_cost']:.2f}")
    print(f"Total energy produced by household: {summary['total_energy_produced']:.2f} kWh")
    print(f"Total energy sold to the grid: {summary['total_energy_sold']:.2f} kWh")
    print(f"Total revenue from energy sold: €{summary['total_revenue']:.2f}")
    print(f"Net cost: €{summary['net_cost']:.2f}")

    print(f"System independence from the grid: {summary['independence_percent']:.2f}%")
    print(f"CO2 emissions produced: {summary['co2_produced']:.2f} kg")

def main():
    # Specify the file path directly in the code
    file_path = os.path.join("..", "Data", "site1", "Comparisons", "2023JuneALL_MILP.csv")

    # Load data
    print(f"Loading data from {file_path}...")
    df = load_csv_data(file_path)
    print(f"Loaded {len(df)} records")

    # Calculate summary using dynamic cost parameters
    print(f"Calculating summary with dynamic cost parameters:")
    print(f"  Day rate: €{cost_params['day_rate']}/kWh")
    print(f"  Night rate: €{cost_params['night_rate']}/kWh")
    print(f"  Peak rate: €{cost_params['peak_rate']}/kWh")
    print(f"  Sell price: €{cost_params['sell_price']}/kWh")
    summary = calculate_summary(df, cost_params)

    # Print summary
    print_summary(summary)

if __name__ == "__main__":
    main()
