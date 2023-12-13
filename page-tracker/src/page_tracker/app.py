# src/page-tracker/app.py

from functools import cache

from flask import Flask
from redis import Redis, RedisError

app = Flask(__name__)
# redis = Redis()

@app.get("/")
def index():
    # page_views = redis.incr("page_views")
    try:
        page_views = redis().incr("page_views")
    except RedisError:
        app.logger.exception("Redis error")
        return "Sorry, something went wrong \N{pensive face}", 500
    else:
        return f'this page has been seen {page_views} times.'

@cache
def redis():
    return Redis()