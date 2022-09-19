import os

from dotenv import load_dotenv


load_dotenv()

VALIDATOR_API_BASE = "https://validator.nymtech.net/api/v1"

ENDPOINT_PACKETS_MIXED = "stats"

API_URL = os.getenv("API_URL_BASE")