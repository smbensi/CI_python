# src/page-tracker/app.py

from functools import cache

from flask import Flask
from redis import Redis

app = Flask(__name__)
# redis = Redis()

@app.get("/")
def index():
    # page_views = redis.incr("page_views")
    page_views = redis().incr("page_views")
    return f'this page has been seen {page_views} times.'

@cache
def redis():
    return Redis()