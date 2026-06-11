#!/bin/bash
source .venv/bin/activate
echo "Starting Email Validator backend on http://localhost:8000 ..."
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
