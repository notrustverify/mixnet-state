# Mixnet-state

Endpoints:

* `api/state`

   Example
  ```json
    {
         "epoch_id": 3722,
         "epoch_working": true,
         "last_downtime": "2022-09-19T17:16:16.776853Z",
         "last_update": "2022-09-21T06:10:02.284596Z",
         "mixnet_working": true,
         "validator_working": true
    }
  ```

1. Create database `python3 -c "from db import *; create_tables()"`
