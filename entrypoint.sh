#!/bin/bash

NUM_WORKERS=${NUM_WORKERS:-1}

/app/.venv/bin/python -m celery -A tasks.celery_app.app worker -Q translate -c ${NUM_WORKERS};
