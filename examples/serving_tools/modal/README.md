## Deploy a Custom Arcade Worker on Modal

### Requirements

-   Python 3.10+
-   Modal CLI

### Deploy

```bash
cd examples/serving-tools
modal deploy run-arcade-worker.py
```

### Changing the Toolkits

To change the toolkits, edit the `toolkits` list in the `run-arcade-worker.py` file.
