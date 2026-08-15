import random
import time


MIN_POST_INTERVAL = 1
MAX_POST_INTERVAL = 3

MIN_ROUND_INTERVAL = 15
MAX_ROUND_INTERVAL = 20


def wait_random_minutes(
    min_minutes: int,
    max_minutes: int,
    message: str,
) -> None:
    delay_seconds = random.randint(
        min_minutes * 60,
        max_minutes * 60,
    )

    minutes, seconds = divmod(delay_seconds, 60)

    print(
        f"[~] {message}: "
        f"{minutes}m {seconds}s"
    )

    time.sleep(delay_seconds)