import json
import sys
import random
import traceback

import utils
import requests

from db import BaseModel


class State:
    EXPLORER_BASE = "https://explorer.nymtech.net/api/v1/"
    PERCENT_NODES_TEST = 10
    ACTIVE_SET_SIZE = 240
    MIN_PERCENT_NODE = 60

    def __init__(self):
        self.apiValidator = utils.VALIDATOR_API_BASE
        self.getPacketsMixedEndpoint = utils.ENDPOINT_PACKETS_MIXED
        self.db = BaseModel()
        self.numberMixnodeCheckSet = State.ACTIVE_SET_SIZE / State.PERCENT_NODES_TEST
        self.timeoutMixnode = 30
        self.timeoutValidator = 45

    def getMixnodes(self):
        s = requests.Session()
        ipsPort = dict()
        selected = dict()
        try:
            response = s.get(f"{State.EXPLORER_BASE}/mix-nodes/active-set/active")

            if response.ok:
                activeSet = response.json()

                for mixnode in activeSet:
                    if mixnode.get('mix_node'):
                        ipsPort.update({mixnode['mix_node']['host']: mixnode['mix_node']['http_api_port']})

        except requests.RequestException as e:
            print(traceback.format_exc())
            return None

        # change check set host
        if len(ipsPort) > 0:
            self.db.updateCheckSet()

            selectedHosts = random.choices(list(ipsPort.keys()), k=int(self.numberMixnodeCheckSet))

            for ip in selectedHosts:
                selected.update({ip: ipsPort[ip]})
            self.db.insertCheckSet(selected)

    def getPacketsMixed(self):
        ips = self.db.getCheckSet()

        s = requests.Session()

        for ip in ips:
            try:

                response = s.get(f"http://{ip['ip']}:{ip['http_api_port']}/{utils.ENDPOINT_PACKETS_MIXED}", timeout=self.timeoutMixnode,allow_redirects=True)
                if response.ok:
                    stats = response.json()
                    if stats.get('packets_received_since_last_update') and stats.get('packets_sent_since_last_update'):
                        totalPacketMixed = stats.get('packets_received_since_last_update') + stats.get(
                            'packets_sent_since_last_update')
                        print(ip['ip'], totalPacketMixed)

                        self.db.updatePackets(ip['ip'], ip['http_api_port'], totalPacketMixed)
            except requests.RequestException as e:
                print(traceback.format_exc())
                print(e)

    def getMixnodesState(self):
        mixnodes = self.db.getMixnodesNoPacketMixed()

        # set mixnet to false if number of mixnode mixed packet lower thant a certain %
        if len(mixnodes) / self.numberMixnodeCheckSet >= (State.MIN_PERCENT_NODE / 100.0):
            print(mixnodes,len(mixnodes))
            print("Mixnet nok")
            return False

        print("Mixnet ok")
        return True

    def getValidatorState(self):
        s = requests.Session()

        try:
            s.get(f"{self.apiValidator}/api/v1/status/", timeout=self.timeoutValidator,allow_redirects=True)
        except requests.RequestException as e:
            print(traceback.format_exc())
            print(e)
            print("Validator nok")
            return False

        print("Validator ok")
        return True

    def setStates(self):
        self.getPacketsMixed()

        mixnetState = self.getMixnodesState()
        validatorState = self.getValidatorState()

        self.db.setState(mixnetState,validatorState)
