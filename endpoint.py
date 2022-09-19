import threading
import time
from datetime import datetime, date, timedelta

import schedule
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from cachetools import cached, TTLCache
from state import State

from db import BaseModel

cache = TTLCache(maxsize=10 ** 9, ttl=120)
app = Flask(__name__, static_url_path='/static')
api = Api(app)


@app.route('/')
def index():
    return app.send_static_file('index.html')


class MixnetState(Resource):
    def get(self):
        data = self.read_data()
        response = jsonify(data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @cached(cache={})
    def read_data(self):
        data = {}
        db = BaseModel()

        states = db.getState()

        data.update({
            "mixnet_working": states['mixnet'],
            "validator_working": states['validator_api'],
            "last_update": states['created_on'],
        })

        return data


def update():
    mixnetState = State()
    schedule.every(10).minutes.do(mixnetState.getMixnodes)
    schedule.every(1).minutes.do(mixnetState.setStates)

    while True:
        schedule.run_pending()
        time.sleep(60)


th = threading.Thread(target=update)
th.start()

api.add_resource(MixnetState, '/api/state')

if __name__ == '__main__':
    host = '0.0.0.0'

    app.run(debug=True, port='8080', host=host)
