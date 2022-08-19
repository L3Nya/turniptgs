#!/bin/sh
PORT=${1:-8080}
cd $(dirname $0)
gunicorn app:web_app --bind localhost:$PORT --worker-class aiohttp.GunicornWebWorker
