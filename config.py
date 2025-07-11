import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Gurobi license configuration
GUROBI_LICENSE_FILE = os.getenv('GUROBI_LICENSE_FILE')

# Function to set up Gurobi environment
def setup_gurobi_env():

    if GUROBI_LICENSE_FILE:
        os.environ['GRB_LICENSE_FILE'] = GUROBI_LICENSE_FILE