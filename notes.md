[source link](https://realpython.com/docker-continuous-integration/)


# Virtual env

- modern way of specifying the projetct's dependencies and metadata through `pyproject.toml` configuration file
- `setuptools` as the build backend
- `constraints.txt` specify pinned version of your project's dependencies in order to achieve repeatable installs
- You don't specify depency versions in `pyproject.toml` instead freeze it in a constraint file
    with the following command `python -m pip freeze --exclude-editable > constraints.txt`
- because your package follow the `src layout` it's convenient to install it in editable mode during dev(`python -m pip install --editable .`).
    This will allow to make change to the source code and have them reflected immediately in the venv without a reinstall

# Redis

- `Redis` (remote-dictionary-server) commonly used with caching and data persistence (kind of DB)
- it's a remote, in-memory data structure store. Being a key-value store, Redis is like a remote Python dictionary that you can connect to from anywhere.
- `docker run -d --name redis-server redis` running in background (-d detached mode)
- [instructins to use redis docker](https://hub.docker.com/_/redis)

- in Python
```Python
from redis import Redis
redis = Redis() # if you need to connect to remote Redis(host="127.0.0.1",port=6379)
# another way : redis = Redis.from_url("redis://localhost:6379/")
# This can be especially convenient if you want to store your Redis 
# configuration in a file or environment variable.
redis.incr("page_views")
redis.incr("page_views")
```

When creating a new *Redis* instance without specifying any argument, it will try to connect to a Redis server running on localhost and the default port , 6379

# Docker

- when setting up multiple containers to work together, you should use docker networks
- First, create a user-defined bridge network: `docker network create page-tracker-network`
- next connect your existing `redis-server` container to this new virtual network `docker network connect page-tracker-network redis-server`
- command to run redis-cli to the network `docker run --rm -it \
             --name redis-client \
             --network page-tracker-network \
             redis redis-cli -h redis-server`
- the **--rm** flag tells Docker to remove the created container as soon as you terminate it. by using the **-h** param, you tell the redis-CLI to connect to a redis server identified by its container name.
- You can take advantage of **port mapping** to make redis available outside of the docker container. During dev, you'll want to connect to Redis directly and not through a virtual network from another container. Run a container with the **-p** option `docker run -d --name redis-server -p 6379:6379 redis
` on the left it's the port number on the host machine and on the right it's the mapped port in the Docker container
- info on your container `docker inspect redis-server`

# Flask app

```python
@app.get("/")
def index():
    page_views = redis.incr("page_views")
    return f'this page has been seen {page_views} times'
```
define a controller function to handle *HTTP GET* requests arriving at the web server's root adress.
Your endpoint increments the number of page views in Redis

- To verify : 
> flask --app page_tracker.app run

# Test and Secure web app

- Before packaging and deploying any project to production, you should thoroughly test, examine and secure the underlying source code
- Unit test involves testing a program's individual units or components to ensure that they work as expected.
- it's quite common to use `pytest` over the standard library's `unittest`
- add to the pyproject.toml:

```toml
[projet.optional-dependencies]
dev = [
    "pytest",
]
```

By keeping `pytest` separate from the main dependencies, you'll be able to install it on demand only when needed.

- create z`test/unit/test_app.py` The `pytest` module will discover your tests when you prefix them with the word **test**.
- start by testing the happy path of your web app. Each Flask app comes with a convenient test client that you can use to make simulated HTTP requests. It doesn't require a live server to be running (much faster and more isolated)
- When you intent to write a unit test, you must always isolate it by eliminating its dependencies that your unit of code may have.
- To run the test `python -m pytest -v test/unit/`

## Integration tests

- the goal of integration tests is to check how your components interact with each other as parts of a larger system 