# examples

```python

import Client from py-opentsdb

host="opentsdb.some.where"
port=4242

c = Client(host, port)

rslt = c.query(**{
        "metric": "system_load1",
        "tags": {"host": "*"},
        "start": "60m-ago",
        "aggr": "sum"
        })

df = rslt.DataFrame()

print(df)
```
