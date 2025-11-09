from .worker import celery_app
import time

@celery_app.task
def demo_sleep(n: int = 3) -> str:
    time.sleep(n)
    return f"Finished after {n}s"
