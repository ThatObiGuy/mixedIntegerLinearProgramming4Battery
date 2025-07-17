# We use pandas to read the csv files at our specified paths & convert timestamps to datetime objects
import pandas as pd

# We use datetime to extract hours (.hour) in the get_time_of_use_rates function
from datetime import datetime

# This function will load and preprocess data from CSV files
def load_data(file_path):
    # We use pandas to save the content at the given path to a variable called df (dataframe)
    df = pd.read_csv(file_path)

    # Convert updated_time column to datetime objects
    df['updated_time'] = pd.to_datetime(df['updated_time'])

    # Extract relevant columns - here MILP only needs knowledge of the production and demand
    data = {
        'time': df['updated_time'].tolist(),
        'solar_production': df['production_power_w'].fillna(0).values,
        'load_demand': df['consumption_power_w'].fillna(0).values
    }

    # The function returns the processed data - time(with encoding)/production/load
    return data

# This function creates a dictionary mapping each time step to the appropriate rate
# This will allow us to apply the program for other electricity providers.
def get_time_of_use_rates(data, cost_params):
    # Beginning with an empty dictionary
    buy_rates = {}

    # Looks through the data and maps each time value to a rate - using t as an index
    for t in range(len(data['time'])):
        hour = data['time'][t].hour
        if 2 <= hour < 4:  # Boost: 02:00 to 04:00
            buy_rates[t] = cost_params['boost_rate']
        elif 23 <= hour or hour < 8:  # Night: 23:00 to 08:00
            buy_rates[t] = cost_params['night_rate']
        else:  # Day: all other times
            buy_rates[t] = cost_params['day_rate']

    # The function returns the populated dictionary
    return buy_rates