import threading
import time
import traceback
from datetime import datetime
from os.path import exists

import dateparser

import schedule
from cachetools import cached, TTLCache
from flask import Flask, jsonify, render_template, request
from flask_restful import Resource, Api, abort, fields


import utils
from db import BaseModel, create_tables
from mixnet import Mixnet
from state import State

cache = TTLCache(maxsize=10 ** 9, ttl=120)
app = Flask(__name__)
api = Api(app)
db = BaseModel()



@app.route('/')
def index():
    return render_template('index.html', api_url=utils.API_URL)


class MixnetState(Resource):
    def get(self):
        data = self.read_data()
        response = jsonify(data)
        if len(data) <= 0:
            abort(404, error_message="no data")
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @cached(cache={})
    def read_data(self):
        data = {}

        try:
            states = db.getState()[0]
            uptime = db.getLastCrashDate()

            data.update({
                "mixnet_working": states['mixnet'],
                "validator_working": states['validator_api'],
                "epoch_working": states['epoch'],
                "rpc_working": states["rpc"],
                "last_update": states['created_on'].isoformat() + "Z",
                "last_downtime": uptime['created_on'].isoformat() + 'Z',
                "epoch_id": states['epochId']
            })

            return data
        except (IndexError, KeyError):
            print(traceback.format_exc())
            return {}


class MixnetStats(Resource):
    def get(self):
        timedelta = request.args.get('timedelta', type=str, default=None)
        data = {}

        if timedelta is None:
            data = self.read_data()
        else:
            try:

                timedelta = dateparser.parse(timedelta, settings={'TIMEZONE': 'UTC'})
                data = self.read_data_timeframe(timedelta)
            except Exception as e:
                print(traceback.format_exc())
                print(f"Error with dateparser, {e}")

        if len(data) <= 0:
            abort(404, error_message="no data")

        response = jsonify(data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @cached(cache={})
    def read_data(self):
        data = {}

        try:
            packetsMixed = db.getLastMixedPackets()[0]

            payload_received = packetsMixed['total_packets_received'] * utils.SPHINX_PACKET_SIZE_BYTES
            payload_sent = packetsMixed['total_packets_sent'] * utils.SPHINX_PACKET_SIZE_BYTES
            data.update({
                "packets_received": packetsMixed['total_packets_received'],
                "packets_sent": packetsMixed['total_packets_sent'],
                "mixnet_bytes_received": payload_received,
                "mixnet_bytes_sent": payload_sent,
                "mixnet_speed_bytes_sec_received": payload_received / packetsMixed['update_packets_avg'],
                "mixnet_speed_bytes_sec_sent": payload_sent / packetsMixed['update_packets_avg'],
                "spinx_packet_bytes": utils.SPHINX_PACKET_SIZE_BYTES,
                "spinx_packet_payload_bytes": utils.SPHINX_PACKET_PAYLOAD_BYTES,
                "last_update": packetsMixed['created_on'],
                "query_second_update_mixnode": packetsMixed['update_query_mixnode']
            })

            return data
        except (IndexError, KeyError):
            print(traceback.format_exc())
            return {}

    def read_data_timeframe(self, timedelta):
        try:
            packetsMixed = db.getMixedPacketsTime(timedelta)

            return packetsMixed
        except (IndexError, KeyError):
            print(traceback.format_exc())
            return {}

api.add_resource(MixnetState, '/api/state')
api.add_resource(MixnetStats, '/api/packets')

if not (exists("./data/data.db")) or utils.DB_NAME:
    create_tables()

if __name__ == '__main__':
    host = '0.0.0.0'

    app.run(debug=False, port=8080, host=host)
