import time

import db
from db import BaseModel
from state import State


if __name__ == '__main__':
    state = State()

    print(db.BaseModel().getLastCrashDate())
    state.setStates()

