# Implementing a Distance Vector Routing Algorithm


# Development step

## localhost test
### two host communication
![two host](images/two_hosts.jpeg)
```shell script
python dvrouter.py -p 8000 8001:2
```

```shell script
python dvrouter.py -p 8001 8000:2
```

### three host communication
![three host](images/three_hosts.jpeg)

```shell script
python dvrouter.py -p 8000 8001:4 8002:1
```

```shell script
python dvrouter.py -p 8001 8000:4 8002:50
```

```shell script
python dvrouter.py -p 8002 8000:1 8001:50
```

### four host communication
![four host](images/four_hosts.png)

```shell script
python dvrouter.py -p 8000 8001:1 8002:3 8003:7
```

```shell script
python dvrouter.py -p 8001 8000:1 8002:1
```

```shell script
python dvrouter.py -p 8002 8000:3 8001:1 8003:2
```

```shell script
python dvrouter.py -p 8003 8000:7 8002:2
```

The test output will be in test/ folder