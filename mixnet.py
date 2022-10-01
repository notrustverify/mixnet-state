import datetime
import json
import sys
import random
import traceback
from functools import reduce
from pprint import pprint

import backoff
from dateutil import parser
import aiohttp
import requests
from aiohttp import ClientTimeout

import utils
import asyncio

from db import BaseModel


class Mixnet:
    PERCENT_NODES_TEST = 10
    ACTIVE_SET_SIZE = 240
    MIN_PERCENT_NODE = 60
    TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

    def __init__(self):
        # https://validator.nymtech.net/api/v1/openapi.json
        self.db = BaseModel()
        self.timeoutMixnode = 5

    @backoff.on_exception(backoff.expo,
                          requests.exceptions.RequestException,max_time=30,max_tries=2)
    def getActiveSetNodes(self, firstRun=True):
        if not firstRun:
            try:
                packetsLastUpdate = self.db.getLastMixedPackets()[0]['updated_on']
                if utils.getNextEpoch() is not None and datetime.datetime.timestamp(
                        packetsLastUpdate) < utils.getNextEpoch():
                    return
            except KeyError and IndexError:
                print(traceback.format_exc())

        self.db.updateActiveSet()
        s = requests.Session()
        ipsPort = dict()

        print(f"{datetime.datetime.now()} - update active set")

        try:
            response = s.get(f"{utils.NYM_VALIDATOR_API_BASE}/api/v1/mixnodes/active")
            count = {1: 0, 2: 0, 3: 0}
            if response.ok:
                activeSet = response.json()

                for mixnode in activeSet:
                    if mixnode.get('mix_node'):
                        count[mixnode['layer']] += 1

                        ipsPort.update({mixnode['mix_node']['host']: {
                            'http_api_port': mixnode['mix_node']['http_api_port'], 'layer': mixnode['layer']}})

                self.db.insertActiveSet(ipsPort)
                print(f"Layer repartition {count}")
        except requests.RequestException as e:
            print(traceback.format_exc())

    def getDiffPacketsMixed(self):
        packets = self.db.getLastMixedPackets()
        try:
            pktRcv = packets[0]['total_packets_received'] - packets[1]['total_packets_received']
            pktSent = packets[0]['total_packets_sent'] - packets[1]['total_packets_sent']
            print(f"Delta from last Recv {pktRcv}  Sent {pktSent}")

            return {"deltaPktsRcv": pktRcv, "deltaPktsSent": pktSent}
        except KeyError and IndexError as e:
            print(traceback.format_exc())
            print(e)

    def getPacketsMixnode(self):
        asyncio.run(self.getConcurrentPacketsMixed())

    @staticmethod
    async def fetch(session, url):

        async with session.get(url, allow_redirects=True, timeout=5) as resp:
            try:
                return await resp.json() if resp.ok else None
            except requests.RequestException or asyncio.TimeoutError as e:
                print(traceback.format_exc())
                print(e)

    async def getConcurrentPacketsMixed(self):
        self.getActiveSetNodes()

        allLayerData = {}
        timeUpdate = []
        totalPktsRecv = 0
        totalPktsSent = 0
        totalPktsByLayer = {"recv": {1: 0, 2: 0, 3: 0}, "sent": {1: 0, 2: 0, 3: 0}}

        for layer in range(1, utils.NUM_LAYER + 1):
            ips = [f"http://{ip['ip']}:{ip['http_api_port']}/{utils.ENDPOINT_PACKETS_MIXED}" for ip in
                   self.db.getActiveSet(layer=layer)]

            async with aiohttp.ClientSession(raise_for_status=True) as session:
                urls = [asyncio.ensure_future(utils.fetch(session, url, timeout=5)) for url in ips]
                data = await asyncio.gather(*urls, return_exceptions=True)

            allLayerData.update({layer: data})

        for layer in range(1, utils.NUM_LAYER + 1):
            for stats in allLayerData[layer]:
                # type must be tested because fetch method could return Timeout object
                if type(stats) == dict:
                    if stats.get('packets_received_since_last_update') and stats.get(
                            'packets_sent_since_last_update'):
                        # print(ip['ip'], stats.get('packets_received_since_last_update'),
                        #     stats.get('packets_sent_since_last_update'))
                        totalPktsRecv += stats.get('packets_received_since_last_update')
                        totalPktsSent += stats.get('packets_sent_since_last_update')

                        totalPktsByLayer["recv"][layer] += stats.get('packets_received_since_last_update')
                        totalPktsByLayer["sent"][layer] += stats.get('packets_sent_since_last_update')

                        updateTime = parser.isoparse(stats.get('update_time'))
                        previousUpdateTime = parser.isoparse(stats.get('previous_update_time'))
                        timeUpdate.append(updateTime - previousUpdateTime)

        avgTimeUpdate = reduce(lambda a, b: a + b, timeUpdate) / len(timeUpdate)

        MU = 10.0 ** 6
        # microseconds are maybe overkill but could be useful later
        avgTimeUpdate = avgTimeUpdate.seconds + avgTimeUpdate.microseconds / MU

        if utils.DEBUG:
            for layer in range(1, 4):
                if layer == 1:
                    print(f"Received from outside {totalPktsByLayer['recv'][layer]} pkts")
                    print(f"Sent from layer {layer} to layer {layer + 1} --> {totalPktsByLayer['sent'][layer]} pkts ")
                elif layer == 2:
                    print(
                        f"Received from layer {layer - 1} {totalPktsByLayer['recv'][layer]} pkts (loss {abs(totalPktsByLayer['sent'][layer - 1] - totalPktsByLayer['recv'][layer])} pkts)")
                    print(f"Sent from layer {layer} to layer {layer + 1} --> {totalPktsByLayer['recv'][layer]} pkts")
                else:
                    print(
                        f"Received from layer {layer - 1} {totalPktsByLayer['recv'][layer]} pkts (loss {abs(totalPktsByLayer['sent'][layer - 1] - totalPktsByLayer['recv'][layer])} pkts) ")
                    print(f"Sent from layer {layer} to outside {totalPktsByLayer['sent'][layer]} pkts")

        self.db.updateTotalPackets(totalPktsRecv, totalPktsSent, avgTimeUpdate)

        print(
            f"{datetime.datetime.now()} - update mixed packets end. Pkts avg mixnodes update {reduce(lambda a, b: a + b, timeUpdate) / len(timeUpdate)}s")
