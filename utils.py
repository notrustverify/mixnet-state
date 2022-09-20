import os

from dotenv import load_dotenv


load_dotenv()

VALIDATOR_API_BASE = "https://validator.nymtech.net/api/v1"

ENDPOINT_PACKETS_MIXED = "stats"

API_URL = os.getenv("API_URL_BASE")
NYM_VALIDATOR_API_BASE = os.getenv("NYM_VALIDATOR_API_BASE")
NYM_RPC = os.getenv("NYM_RPC")

UPDATE_MINUTES_STATE = float(os.getenv("UPDATE_MINUTES_STATE",3))
UPDATE_MINUTES_CHECK_SET = float(os.getenv("UPDATE_MINUTES_CHECK_SET",10))