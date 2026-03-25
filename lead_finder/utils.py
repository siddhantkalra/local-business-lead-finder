import time
import random


def jitter_sleep(base_seconds: float = 0.2, jitter_seconds: float = 0.3) -> None:
    time.sleep(base_seconds + random.random() * jitter_seconds)
