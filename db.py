import logging
import sys
import traceback
from datetime import datetime

from peewee import *

database = SqliteDatabase('./data/data.db', pragmas={'foreign_keys': 1})

logger = logging.getLogger('db')
logHandler = logging.getLogger('db')
logHandler.setLevel(logging.DEBUG)


class BaseModel(Model):
    def connect(self):
        try:
            database.connect()
        except Exception as e:
            print(traceback.format_exc())
    def close(self):
        try:
            database.close()
        except Exception as e:
            print(traceback.format_exc())
    def getPacketsLastUpdate(self):
        self.connect()

        try:
            with database.atomic():
                return None

        except IntegrityError as e:
            print(e)
            print(traceback.format_exc())
            return False
        except DoesNotExist as e:
            print(e)
            print(traceback.format_exc())
            return False
        finally:
            self.close()

    def insertCheckSet(self, ips):
        self.connect()
        try:
            with database.atomic():
                for ip, port in ips.items():
                    now = datetime.now()

                    Mixnodes.insert(ip=ip, http_api_port=port, in_check_set=True, updated_on=now, created_on=now
                                    ).on_conflict(action="update", conflict_target=[Mixnodes.ip],
                                                  update={'ip': ip, 'http_api_port': port, "in_check_set": True,
                                                          'updated_on': datetime.now()}).execute()

        except IntegrityError as e:
            print(e)
            print(traceback.format_exc())
            return False
        except DoesNotExist as e:
            print(e)
            print(traceback.format_exc())
            return False
        finally:
            self.close()

    def updateCheckSet(self):
        self.connect()

        try:
            with database.atomic():
                Mixnodes.update(in_check_set=False, updated_on=datetime.now()).where(
                    Mixnodes.in_check_set == True).execute()
        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

    def updatePackets(self, ip, http_api_port, num_packets):
        self.connect()

        try:
            with database.atomic():
                Mixnodes.update(packets_mixed=num_packets, updated_on=datetime.now()).where(Mixnodes.ip == ip).execute()
        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

    def getCheckSet(self):
        self.connect()

        try:
            with database.atomic():
                data = [mixnode for mixnode in Mixnodes.select().where(Mixnodes.in_check_set == True).dicts()]
        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

        return data

    def getMixnodesNoPacketMixed(self):
        self.connect()

        try:
            with database.atomic():
                data = [mixnode for mixnode in
                        Mixnodes.select().where(Mixnodes.packets_mixed <= 0 & Mixnodes.in_check_set == True).dicts()]
        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

        return data

    def setState(self, mixnet,validator):
        self.connect()
        now = datetime.now()
        try:
            with database.atomic():
                State.insert(mixnet=mixnet, validator_api=validator).execute()
        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

    def getState(self):
        self.connect()

        try:
            with database.atomic():
                return [s for s in State.select().order_by(State.created_on.desc()).limit(1).dicts()][0]

        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

    def getLastOkTime(self):
        self.connect()

        try:
            with database.atomic():
                return [s for s in State.select(State.created_on).order_by(State.created_on.asc()).limit(1).dicts()][0]

        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

    def getLastCrashDate(self):
        self.connect()
        try:
            with database.atomic():
                lastCrash = [s for s in State.select(State.created_on).order_by(State.created_on.desc()).where(State.mixnet == False).limit(1).dicts()]

                if len(lastCrash) <= 0:
                    return [s for s in State.select(State.created_on).order_by(State.created_on.asc()).limit(1).dicts()][0]

                return lastCrash[0]

        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

class Mixnodes(BaseModel):
    class Meta:
        database = database
        db_table = 'mixnodes'

    ip = TextField(unique=True)
    http_api_port = IntegerField(default=8000)
    packets_mixed = FloatField(default=0)
    in_check_set = BooleanField(default=False)

    created_on = DateTimeField(default=datetime.now)
    updated_on = DateTimeField(default=datetime.now)


class State(BaseModel):
    class Meta:
        database = database
        db_table = 'state'

    mixnet = BooleanField(default=False)
    validator_api = BooleanField(default=False)
    nym_client = BooleanField(default=False)

    created_on = DateTimeField(default=datetime.now)
    updated_on = DateTimeField(default=datetime.now)


def create_tables():
    with database:
        database.create_tables([Mixnodes, State])
