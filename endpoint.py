import threading
import time
from datetime import datetime, date, timedelta
from os.path import exists
import schedule
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_restful import Resource, Api
from cachetools import cached, TTLCache
import utils

import db
from state import State

from db import BaseModel

cache = TTLCache(maxsize=10 ** 9, ttl=120)
app = Flask(__name__)
api = Api(app)


@app.route('/')
def index():
    return render_template('index.html', api_url=utils.API_URL)


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
        uptime = db.getLastCrashDate()

        data.update({
            "mixnet_working": states['mixnet'],
            "validator_working": states['validator_api'],
            "last_update": states['created_on'].isoformat() + "Z",
            "last_downtime": uptime['created_on'].isoformat() + 'Z',
            "epoch_working": states['epoch'],
            "epoch_id": states['epochId']
        })

        return data


def update():
    mixnetState = State()
    firstLaunch = False
    if firstLaunch:
        print("Running first time - update check set")
        mixnetState.getMixnodes()
        firstLaunch = True
    
    schedule.every(utils.UPDATE_MINUTES_CHECK_SET).minutes.do(mixnetState.getMixnodes)
    schedule.every(utils.UPDATE_MINUTES_STATE).minutes.do(mixnetState.setStates)

    while True:
        schedule.run_pending()
        time.sleep(60)


th = threading.Thread(target=update)
th.start()

api.add_resource(MixnetState, '/api/state')

if not (exists("./data/data.db")):
    db.create_tables()

if __name__ == '__main__':
    host = '0.0.0.0'

    app.run(debug=False, port='8080', host=host)
