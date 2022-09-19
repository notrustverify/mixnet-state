# Mixnet-state

Endpoints:

* `api/state`

   Example
  ```json
  {
    "last_downtime": "2022-09-19T20:10:51.498950Z",
    "last_update": "2022-09-19T20:23:41.794004Z",
    "mixnet_working": true,
    "validator_working": true
  }
  ```

1. Create database `python3 -c "from db import *; create_tables()"`
