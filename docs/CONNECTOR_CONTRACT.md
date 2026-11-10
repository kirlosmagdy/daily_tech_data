# Bronze Connector Contract

Every source connector in `connectors/` is a standalone Python module that implements a single entry function:

```python
def extract(cfg: dict) -> dict