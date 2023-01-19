import asyncio
import datetime
import random
import traceback
import backoff

import aiohttp

import utils
import requests

from db import BaseModel


class State:
    PERCENT_NODES_TEST = 10
    ACTIVE_SET_SIZE = 240
    MIN_PERCENT_NODE = 60

    def __init__(self):
        # https://validator.nymtech.net/api/v1/openapi.json
        self.getPacketsMixedEndpoint = utils.ENDPOINT_PACKETS_MIXED
        self.db = BaseModel()
        self.numberMixnodeCheckSet = State.ACTIVE_SET_SIZE / State.PERCENT_NODES_TEST
        self.timeoutMixnode = 30
        self.timeoutValidator = 45
        self.timeoutRPC = 45

    @backoff.on_exception(backoff.expo,
                          requests.exceptions.RequestException, max_time=30, max_tries=2)
    def getMixnodes(self):
        s = requests.Session()
        ipsPort = dict()
        selected = dict()
        print(f"{datetime.datetime.utcnow()} - update check set")
        try:
            response = s.get(f"{utils.NYM_VALIDATOR_API_BASE}/api/v1/mixnodes/active")

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

                response = s.get(f"http://{ip['ip']}:{ip['http_api_port']}/{utils.ENDPOINT_PACKETS_MIXED}",
                                 timeout=self.timeoutMixnode, allow_redirects=True)
                if response.ok:
                    totalPacketMixed = 0
                    stats = response.json()
                    if stats.get('packets_received_since_last_update') and stats.get('packets_sent_since_last_update'):
                        totalPacketMixed = stats.get('packets_received_since_last_update') + stats.get(
                            'packets_sent_since_last_update')
                        print(ip['ip'], totalPacketMixed)

                        self.db.updatePackets(ip['ip'], ip['http_api_port'], totalPacketMixed)
                    else:
                        print(ip['ip'], totalPacketMixed)
                        self.db.updatePackets(ip['ip'], ip['http_api_port'], totalPacketMixed)
            except requests.RequestException as e:
                self.db.updatePackets(ip['ip'], ip['http_api_port'], 0)
                print(traceback.format_exc())
                print(e)

    async def getConcurrentPacketsMixed(self):

        ips = [f"{ip['ip']}:{ip['http_api_port']}" for ip in self.db.getCheckSet()]

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            urls = [asyncio.ensure_future(utils.fetch(session, f"http://{url}/{utils.ENDPOINT_PACKETS_MIXED}")) for url
                    in ips]
            data = await asyncio.gather(*urls, return_exceptions=True)

        data = dict(zip(ips, data))

        for ipPort, stats in data.items():
            # type must be tested because fetch method could return Timeout object
            if type(stats) == dict:
                totalPacketMixed = 0
                ip = ipPort.split(':')[0]
                port = ipPort.split(':')[1]

                if stats.get('packets_received_since_last_update') and stats.get('packets_sent_since_last_update'):
                    totalPacketMixed = stats.get('packets_received_since_last_update') + stats.get(
                        'packets_sent_since_last_update')
                    print(ip, totalPacketMixed)

                    self.db.updatePackets(ip, port, totalPacketMixed)
                else:
                    print(ip, totalPacketMixed)
                    self.db.updatePackets(ip, port, totalPacketMixed)

    def getMixnodesState(self):
        mixnodes = self.db.getMixnodesNoPacketMixed()

        # set mixnet to false if number of mixnode mixed packet lower thant a certain %
        if len(mixnodes) / self.numberMixnodeCheckSet >= (State.MIN_PERCENT_NODE / 100.0):
            print(mixnodes, len(mixnodes))
            print(f"{datetime.datetime.utcnow()} Mixnet nok")
            return False

        print(f"{datetime.datetime.utcnow()} Mixnet ok")
        return True

    def getValidatorState(self):
        s = requests.Session()

        try:
            s.get(f"{utils.NYM_VALIDATOR_API_BASE}/api/v1/epoch/current", timeout=self.timeoutValidator,
                  allow_redirects=True)
        except requests.RequestException as e:
            print(traceback.format_exc())
            print(e)
            print(f"{datetime.datetime.utcnow()} Validator nok")
            return False

        print(f"{datetime.datetime.utcnow()} Validator ok")
        return True

    def getRPCState(self):
        s = requests.Session()

        try:
            response = s.get(f"{utils.NYM_RPC}/status", timeout=self.timeoutRPC, allow_redirects=True)
            if response.ok:
                state = response.json()

                if "error" in state:
                    print(f"{datetime.datetime.utcnow()} RPC nok")
                    return False
            else:
                print(f"{datetime.datetime.utcnow()} RPC nok")
                return False
        except requests.RequestException as e:
            print(traceback.format_exc())
            print(e)
            print(f"{datetime.datetime.utcnow()} RPC nok")
            return False

        print(f"{datetime.datetime.utcnow()} RPC ok")
        return True

    @backoff.on_exception(backoff.expo,
                          requests.exceptions.RequestException, max_time=30, max_tries=2)
    def getEpochState(self):
        s = requests.Session()
        epochId = 0
        try:
            response = s.get(f"{utils.NYM_VALIDATOR_API_BASE}/api/v1/epoch/current", timeout=self.timeoutValidator,
                             allow_redirects=True)

            if response.ok:
                state = response.json()

                if state.get('epoch_length'):
                    now = datetime.datetime.utcnow()
                    epochLength = state['epoch_length']['secs']
                    epochStart = datetime.datetime.fromisoformat(state['current_epoch_start'].replace('Z', ''))
                    epochId = state['current_epoch_id']

                    if now > epochStart + datetime.timedelta(seconds=epochLength):
                        print(f"{datetime.datetime.utcnow()} Epoch nok")
                        return False, epochId
            else:
                print(f"{datetime.datetime.utcnow()} Epoch nok")
                return False, 0

        except (requests.RequestException,AttributeError) as e:
            print(traceback.format_exc())
            print(e)
            print(f"{datetime.datetime.utcnow()} Epoch nok")
            return False, 0

        print(f"{datetime.datetime.utcnow()} Epoch ok")
        return True, epochId

    def setStates(self):
        asyncio.run(self.getConcurrentPacketsMixed())

        mixnetState = self.getMixnodesState()
        validatorState = self.getValidatorState()
        rpcState = self.getRPCState()
        try:
            epochState, epochId = self.getEpochState()
        except TypeError as e:
            print(e)

        self.db.setState(mixnetState, validatorState, rpcState, epochState, epochId)

    def getUptime(self):
        lastCrash = self.db.getLastCrashDate()

        if len(lastCrash) <= 0:
            return self.db.getState()

        return lastCrash[0]
