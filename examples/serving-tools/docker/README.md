## Custom Worker Image

This example shows how to build a custom worker image with toolkits.

### Requirements

-   Docker

### Build

```
docker build -t custom-worker:0.1.0 .
```

### Run

```
docker run -p 8002:8002 custom-worker:0.1.0
```

### Change the Toolkits

To change the toolkits, edit the `toolkits.txt` file.

```
arcade-google==0.1.0
arcade-web==0.1.0
arcade-zoom==0.1.2
...
```
