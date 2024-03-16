import time
from datetime import datetime

import schedule

import utils
from state import State
from mixnet import Mixnet


def update():
    mixnetState = State()
    mixnet = Mixnet()

    # update check set at start
    mixnetState.getMixnodes()
    mixnet.getActiveSetNodes(firstRun=True)
    mixnetState.setStates()
    print(f"{datetime.now()} - update end")
    
    try:
        schedule.every(utils.UPDATE_MINUTES_CHECK_SET).minutes.do(mixnetState.getMixnodes)
        schedule.every(utils.UPDATE_MINUTES_STATE).minutes.do(mixnetState.setStates)
        schedule.every(utils.UPDATE_SECONDS_PACKET_MIXED).seconds.do(mixnet.getPacketsMixnode)
        schedule.every(utils.UPDATE_SECONDS_ACTIVE_SET).seconds.do(mixnet.getActiveSetNodes)
    except Exception as e:
        print(f"error on updateState.py. will exit")
        print(e)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    update()
