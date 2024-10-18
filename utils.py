import logging
import os
from dotenv import load_dotenv
from datetime import datetime


def read_env():
    load_dotenv()


def setup_logger():
    os.makedirs(os.getenv("LOGS"), exist_ok=True)
    logging.basicConfig(filename=os.path.join(os.getenv("LOGS"), f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"),
                        level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s: %(message)s",
                        force=True)

if __name__ == '__main__':

    # Read the environment
    read_env()

    # Set up the useful directories and check that files exist
    setup_logger()

    logging.info("Environment setup complete")

    # print("prova")
