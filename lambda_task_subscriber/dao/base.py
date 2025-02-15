from supabase.client import Client, create_client
from dotenv import load_dotenv
import os


def load_env():
    load_dotenv(verbose=True, override=True)
    load_dotenv(dotenv_path=".env.local", verbose=True, override=True)


load_env()


# Define a method to load an environmental variable and return its value
def get_env_variable(key: str, default=None):
    # Get the environment variable, returning the default value if it does not exist
    return os.getenv(key, default)


supabase_url = get_env_variable("SUPABASE_URL")
supabase_key = get_env_variable("SUPABASE_SERVICE_KEY")


def get_client():
    supabase: Client = create_client(supabase_url, supabase_key)
    return supabase


class BaseDAO:
    client: Client = get_client()
