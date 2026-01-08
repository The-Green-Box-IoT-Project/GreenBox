import time
from dotenv import load_dotenv
from controller import Controller


def main():
    """Start the control bridge (Controller) and keep it alive."""
    load_dotenv()
    
    ctrl = Controller()

    try:
        ctrl.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted, shutting down controller...")
    finally:
        try:
            ctrl.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
