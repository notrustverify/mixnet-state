import asyncio
import time

from db import BaseModel
from state import State
from mixnet import Mixnet
import utils


if __name__ == '__main__':
    state = State()
    mixnet = Mixnet()
    db = BaseModel()

    #print(db.BaseModel().getLastCrashDate())
    #state.setStates()
    while True:
        mixnet.getActiveSetNodes()
        asyncio.run(mixnet.getConcurrentPacketsMixed())
        mixnet.getDiffPacketsMixed()

       # print(f'Total size {utils.format_bytes(db.getTotalMixedPackets()[0]["packets_received"]*utils.SPHINX_PACKET_PAYLOAD_BYTES)}')
       # print(f'{utils.format_bytes((db.getTotalMixedPackets()[0]["packets_received"] * utils.SPHINX_PACKET_PAYLOAD_BYTES) / 30)}/s')
        time.sleep(30)

