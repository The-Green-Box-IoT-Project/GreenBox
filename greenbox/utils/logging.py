import logging, os
from pathlib import Path
from datetime import datetime


def setup_logger(base_name: str):
    logs = Path.cwd() / "logs"
    logs.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(logs, f"{base_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"),
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s: %(message)s",
        force=True)
