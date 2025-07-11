# PV/Battery System Optimization with Gurobi

This project implements a Mixed Integer Linear Programming (MILP) model for optimizing the operation of a PV/Battery system. The model determines the optimal power flows between solar panels, battery, household, and grid to minimize electricity costs while satisfying constraints.

## Project Structure

The project has been divided into the following components:

1. **data_loader.py**: Handles loading and preprocessing data from CSV files
2. **model_builder.py**: Defines the MILP model using Gurobi
3. **solver.py**: Provides functions for solving the model and processing results
4. **main.py**: Main execution script that ties everything together
5. **config.py**: Handles loading environment variables and setting up Gurobi license
6. **.env**: Contains Gurobi Academic License configuration (not tracked in version control)
7. **requirements.txt**: Lists all Python package dependencies

## Requirements

- Python 3.6+
- Gurobi Optimizer (with valid academic license)
- pandas
- numpy
- python-dotenv

## Installation

1. Install Gurobi Optimizer following the instructions at: https://www.gurobi.com/downloads/
2. Install required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Configure your Gurobi Academic License:
   - Create a copy of the `.env` file from the template
   - Update the license information with your academic license details
   ```
   # Example .env file
   GUROBI_LICENSE_FILE=C:\path\to\your\gurobi.lic
   ```

## Usage

Run the main script:

```
python main.py
```

This will:
1. Load data from the specified CSV file
2. Create the MILP model
3. Solve the model using Gurobi
4. Extract and save the results
5. Print a summary of the optimization

## Model Description

The MILP model optimizes the following power flows:
- Solar to household (P_solar_household)
- Solar to battery (P_solar_battery)
- Solar to grid (P_solar_grid)
- Battery to household (P_battery_household)
- Grid to battery (P_grid_battery)
- Grid to household (P_grid_household)

Subject to constraints:
1. Solar power balance
2. Load demand satisfaction
3. Battery dynamics
4. Battery capacity limits
5. Charging/discharging rate limits
6. No simultaneous charging and discharging

The objective is to minimize the total electricity cost, considering time-of-use rates and feed-in tariffs.

## Customization

You can customize the model by modifying the following parameters in `main.py`:
- Battery parameters (capacity, efficiency, charge/discharge rates)
- Cost parameters (day rate, night rate, peak rate, sell price)
- Solver parameters (time limit, MIP gap)

## Output

The optimization results are saved to `optimization_results.csv` and include:
- Time series data
- Optimal power flows
- Battery state of charge
- Total cost
