import os
from tasks.celery_app import app as celery_app

if __name__ == "__main__":
    os.environ["MACHINE_ID"] = "1"
    celery_app.worker_main(["worker", "-l", "debug", "-Q", "translate"])