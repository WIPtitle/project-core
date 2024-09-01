import json
import os


# Reads credentials from credentials file and returns them in a map.
# Credentials files path are defined in common environment variables in docker compose of main project.
def read_credentials(path):
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Postgres credentials file doesn't exist: {path}")

    with open(path, 'r') as file:
        credentials_map = json.load(file)

    return credentials_map