#!/bin/bash
source venv/bin/activate
quick_start=1 uvicorn src.main:app --host localhost --port 4502 --log-level ${LOG_LEVEL:-debug}
