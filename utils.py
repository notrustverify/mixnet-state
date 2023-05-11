import asyncio
import datetime
import os
import traceback

import backoff
import requests
from dotenv import load_dotenv

load_dotenv()

VALIDATOR_API_BASE = "https://validator.nymtech.net/api/v1"

ENDPOINT_PACKETS_MIXED = "stats"
DEBUG = os.getenv("DEBUG",False)
UPDATE_ALL_MIXNODES = os.getenv("UPDATE_ALL_MIXNODES",False)


API_URL = os.getenv("API_URL_BASE")
NYM_VALIDATOR_API_BASE = os.getenv("NYM_VALIDATOR_API_BASE")
NYM_RPC = os.getenv("NYM_RPC")
NUM_LAYER = 3
NYM_EPOCH_UPDATE = float(os.getenv("NYM_EPOCH_UPDATE",60))

UPDATE_MINUTES_STATE = float(os.getenv("UPDATE_MINUTES_STATE", 3))
UPDATE_MINUTES_CHECK_SET = float(os.getenv("UPDATE_MINUTES_CHECK_SET", 10))
UPDATE_SECONDS_ACTIVE_SET = os.getenv("UPDATE_SECONDS_ACTIVE_SET", 30)
UPDATE_SECONDS_PACKET_MIXED = os.getenv("UPDATE_SECONDS_PACKET_MIXED",30)
UPDATE_SECONDS_PACKETS = os.getenv("UPDATE_SECONDS_PACKETS",30)

SPHINX_PACKET_SIZE_BYTES = float(os.getenv("SPHINX_PACKET_SIZE_BYTES",2145))
SPHINX_PACKET_PAYLOAD_BYTES = float(os.getenv("SPHINX_PACKET_PAYLOAD_BYTES",2048))

DB_USER=os.getenv("DB_USER")
DB_PASSWORD=os.getenv("DB_PASSWORD")
DB_NAME=os.getenv("DB_NAME","mixnetstate")
DB_HOST=os.getenv("DB_HOST")
def format_bytes(size):
    power = 2 ** 10
    n = 0
    power_labels = {0: '', 1: 'k', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size} {power_labels[n] + 'B'}"


@backoff.on_exception(backoff.expo,
                          requests.exceptions.RequestException,max_time=30,max_tries=2)
def getNextEpoch(fromStart=False):
    s = requests.Session()
    currentEpoch = 0
    epochLength = 0
    try:
        response = s.get(f"{NYM_VALIDATOR_API_BASE}/api/v1/epoch/current")

        if response.ok:
            epoch = response.json()
            if epoch.get('current_epoch_start'):
                currentEpoch = datetime.datetime.strptime(epoch.get('current_epoch_start'), "%Y-%m-%dT%H:%M:%SZ")
                epochLength = epoch['epoch_length'].get('secs')

                return currentEpoch.timestamp(),currentEpoch.timestamp() + epochLength
        
            return None,None
    
    except requests.RequestException as e:
        print(traceback.format_exc())
        return None,None


async def fetch(session, url,timeout=30):
    async with session.get(url, allow_redirects=True, timeout=timeout) as resp:
        try:
            return await resp.json() if resp.ok else None
        except (requests.RequestException, asyncio.TimeoutError) as e:
            print(traceback.format_exc())
            print(e)
