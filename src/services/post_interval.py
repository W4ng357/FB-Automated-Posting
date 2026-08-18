import random
import time

from collections.abc import Callable


MIN_POST_INTERVAL = 1
MAX_POST_INTERVAL = 3

MIN_ROUND_INTERVAL = 15
MAX_ROUND_INTERVAL = 20


def wait_random_minutes(
    min_minutes: int,
    max_minutes: int,
    message: str,
    progress_callback: Callable[[str], None] | None = None,
    stop_requested: Callable[[], bool] | None = None,
) -> bool:
    delay_seconds = random.randint(
        min_minutes * 60,
        max_minutes * 60,
    )

    minutes, seconds = divmod(delay_seconds, 60)

    wait_message = (
        f"[~] {message}: {minutes}m {seconds}s"
    )
    print(wait_message)
    if progress_callback is not None:
        progress_callback(wait_message)

    if stop_requested is None:
        time.sleep(delay_seconds)
        return True

    deadline = time.monotonic() + delay_seconds
    while True:
        if stop_requested():
            return False
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        time.sleep(min(remaining, 0.25))
