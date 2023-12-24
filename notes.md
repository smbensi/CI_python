[source link](https://realpython.com/docker-continuous-integration/)


# Virtual env

- modern way of specifying the projetct's dependencies and metadata through `pyproject.toml` configuration file
- `setuptools` as the build backend
- `constraints.txt` specify pinned version of your project's dependencies in order to achieve repeatable installs
- You don't specify depency versions in `pyproject.toml` instead freeze it in a constraint file
    with the following command `python -m pip freeze --exclude-editable > constraints.txt`
- because your package follow the `src layout` it's convenient to install it in editable mode during dev(`python -m pip install --editable .`).
    This will allow to make change to the source code and have them reflected immediately in the venv without a reinstall

## pyproject.toml

- To install :  > python -m pip install --editable ".[dev]"

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

## Dockerfile

- a good practice is to swith to a **regular user**. By default, Docker runs your commands as superuser which a malicious attacker could exploit to gain unrestricted access to your host system. Docker gives **root-level access** to the container and your host machine
- To avoid this 

```Docker
RUN useradd --create-home realpython  # create a new user named realpython
USER realpython                       # tell Docker to use this user from now on
WORKDIR /home/realpython

```

- Consider setting up a **virtual environment**, you risk to interfere with the container's own system tools

``` Docker
ENV VIRTUALENV=/home/realpython/venv   # define a helper variable, with the path to your project's virtual env
RUN python3 -m venv $VIRTUALENV # use venv package to create it 
ENV PATH="$VIRTUALENV/bin:$PATH"
# rather than activating with a shell scrit, update the PATH variable
```
- the most reliable way of creating and activating a virtual env within your Docker image is to directly modify its PATH env variable
- This is necessary because activating your env in the usual way would only be temporary and wouldn't affect docker containers derived from your image. Moreover, if you activated the virtual env using Dockerfile's RUN instruction, then it would only last until the next instruction in your Dockerfile because each one starts a new shell section.

## Run Tests as part of the build process

```Docker
COPY --chown=realpython src/ src/
COPY --chown=realpython test/ test/

RUN python -m pip install . -c constraints.txt && \
    python -m pytest test/unit/ && \
    python -m flake8 src/ && \
    python -m isort src/ --check && \
    python -m black src/ --check --quiet && \
    python -m pylint src/ --disable=C0114,C0116,R1705 && \
    python -m bandit -r src/ --quiet

```

- By baking the automated testing tools into the build process, you ensure 
that if any one of them returns a non-zero exit status code, then building 
your Docker image will fail. That’s precisely what you want when implementing a
continuous integration pipeline.

## Specify the command to run in Docker containers

```Docker
CMD ["flask", "--app", "page_tracker.app", "run", \
     "--host", "0.0.0.0", "--port", "5000"]
```

## Reorganize your Dockerfile for multi-stage builds

- To specify a custom filename instead of the default Dockerfile when building
an image, use the **-f** or **--file** option
> docker build -f Dockerfile.dev -t page-tracker . 

- The idea behind **multi-stage builds** is to partition your Dockerfile into stages, 
**each of which can be based on a completely different image.** That's particularly useful
when your application's dev and runtime envs are different. For example, you can install
the necessary build tools in a temporary image meant just for building and testing your
app and then copy the resulting executable into the final image.

- Each stage in a Dockerfile begins with its own `FROM` instruction, so you'll have 2.
The first stage will look almost exactly the same as your current Dockerfile, except 
that you'll give the stage a name `builder` which you can refer later:

> FROM python:3.11.2-slim-bullseye AS builder

- Because we'll be transferring our packaged page tracker app from one image to another,
we must add the extra step of building a distribution package using the Python wheel 
format (`python -m pip wheel --wheel-dir dist/ . -c constraints.txt`). The `pip wheel`
command will create a file named something like `page_tracker-1.0.0-py3-none-any.whl`
in the `dist/` subfolder.

- The second stage and final stage, implicitedly named `stage-1` will look a little 
repetitive because it's based on the same image

- > COPY --from=builder /home/realpython/dist/page_tracker*.whl /home/realpython
copy the wheek from the `builder` stage

- The builder stage is temporary , so there will be no trace of it in your Docker
images afterward

## Build and Version your Docker image

different strategies for versioning your Docker images:
- **Semantic versioning**: major,minor and patch versions
- **git commit hash**: USe the hash of a git commit tied to the source code in your img
- **Timestamp**: uses Unix time

> docker build -t page-tracker:$(git rev-parse --short HEAD) .

- > docker rmi -f  9cb
the `docker rmi` command is an alias of `docker image rm ` and `docker image remove` 

- Docker lets you override the default command or entry point listed in a Dockerfile when you run a new container
you can specify a custom command for your Docker images in the `docker-compose.yml` file. 

- To run a command in a running container instead of starting up a new one, you can use the `docker exec` command
> docker exec -it -u root page-tracker-web-service-1 /bin/bash

# docker-compose 

- simplifies runnig multi-container Docker applications. It lets you define your application in
terms of independent services along with their configuration and requirements


```yaml

services:
  redis-service:
    image: "redis:7.0.10-bullseye"
    networks:
      - backend-network
    volumes:
      - "redis-volume:/data"
  web-service:
    build: ./web
    ports:
      - "80:5000"
    environment:
      - REDIS_URL: "redis://redis-service:6379"
    networks:
      - backend-network
    depends_on:
      - redis-service

networks:
  backend-network:

volumes:
  redis-volume:

```

- declaration of 2 services `redis-service` and `web-service` (you can scale up each service
so that actual number of Docker containers may be greater than the number of services 
declared here)
- in `web-service` specifies the folder with a Dockerfile to build. The `depends_on` statement
requires `redis-service` to be available before `web-service` can start
- we define a virtual network for the 2 services.
- we define a persistent volume for the redis server

- To tell Docker Compose to **rebuild** your image
> docker compose build 
> docker compose up --build

## Run end-to-end tests against the services

- instead of running end to end test locally against publicly exposed services, you can run it from another
container on the same network. Recent versions of Docker Compose lets you run subsets of services conditionally
You do this by assigning the desired services to custom `profiles` that you can activae on demand

```yaml
test-service:
    profiles:    # defines a list of profiles that your new service will belong to
      - testing
    build:              # specify the path to a directory containing your Dockerfile to build
      context: ./web
      dockerfile: Dockerfile.dev # since the file has a non-standard name, you  provide it explicitely
    environment:                # defines 2 env vars, which your test will use to connect to Redis and Flask
      REDIS_URL: "redis://redis-service:6379"   # you use Docker compose service names as host names
      FLASK_URL: "http://web-service:8000"
    networks:
      - backend-network
    depends_on:             # ensures that Redsi and Flask start before the end to end test
      - redis-service
      - web-service
    command: >                  # defines the command to run when the service starts. use > multiline literal folding
      sh -c 'python -m pytest test/e2e/ -vv
      --redis-url $$REDIS_URL
      --flask-url $$FLASK_URL'

```
- To disable premature substitution of env vars by Docker Compose you escape the dollar sign with 2 dollar signs.
To interpolate those variables when the container starts, you must wrap the entire command in single quotes '
and pass it to the shell (sh)

- When you start a multi container app with Docker Compose only the core services that don't belong to any
**profile** start. To start services that were assugned to one or more profiles, you must list those
profiles using the --profile option

> docker compose --profile testing up -d

To reveal more info about a service
> docker compose logs test-service

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

## Cache your project dependencies

- Installing dependencies in a Dockerfile looks slighty different compared to working locally on your host machine. Normally, you’d install the dependencies and then your Python package immediately afterward. In contrast, when you build a Docker image, it’s worthwhile to split that process into two steps to leverage layer caching, reducing the total time it takes to build the image.
- First, `COPY` the 2 files with the project metadata from your host machine into the docker image
- to tell `pip` to disablecaching add the option `--no-cache-dir`. you won't need those packages outside your venv, so there's no need to cache them -> Docker image smaller.


## Replace Flask's development web server with Gunicorn

- There are few options for replacing Flask's built-in dev web server. One of the most popular choices in Gunicorn (Green Unicorn)
which is a pure-Python implementation of the Web Server Gateway Interface (WSGI) protocol.
You must add it as another dependency in your project

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

- the goal of integration tests is to check how your components interact with each other as parts of a larger system .
- add `pytest-timeout` plugin to pyproject.toml to allow to force failure of test cases that take too long to run
- we add `conftest.py` where we place common fixtures which different types of test will share
- because `conftest.py` is located one level up in the folder hierarchy, pytest will pick up all the fixtures defined in it and make them visible throughout the nested folders.

## Test a real-world scenario End to End (E2E)
k

## Perform static code analysis and security scanning

- add this to the dev dependencies:
```toml

"bandit",
"black",
"flake8",
"isort",
"pylint",
```

and run those instructions:
> python -m black src/ --check      # flag any formatting inconstencies 
> python -m isort src/ --check      # ensure that the import statements are organized 
> python -m flake8 src/             # check for any other PEP8 violation
> python -m pylint src/

When you run pylint , it generally emits messages belonging to a few categories:
- E: Errors
- W: Warnings
- C: Convention violation
- R: refactoring suggestion

you should perform security or vulnerability scanning of your source code before deploying it anywhere.
To scan your code, you can use `bandit`, which you installed as an optional dependency earlier
> python -m bandit -r src/


# Docker based Continous Integration Pipeline (CI)

- requires **build and test automation** as well as **short-lived code branches** with relatively small
features to implement. Feature toggles can help with bigger features that would take longer to develop

- To introduce CI you need the following elements:
    - Version control system
    - Branching strategy
    - Build automation
    - Test automation
    - Continuous integration server
    - Frequent integrations

- It exists different control branching models also known as workflows:
    - Trunk-based Development
    - Github flow or feature branch workflow (long lived mainline or trunk - the master branch)
    - Forking Workflow (works well for open source projects)
    - Release Branching
    - Git flow

- Steps for Github flow:
    1. Fetch the latest version of the mainline to your computer
    2. Create a feature branch form the mainline
    3. Open a pull request to get early feedback from others.
    4. keep working on your feature branch
    5. Fetch the mainline often, merging it into your feature branch and resolving any 
    potential conflicts locally.
    6. Build, lint, and test the code on your local branch
    7. Push your changes whenever the local build and test succeed
    8. With each push, check the automated tests that run on the CI server against your feature branch
    9. Reproduce and fix any identified problems locally before pushing the code again
    10. Once you're done, and all tests pass, request that one or more coworkers review your changes
    11. Apply their feedback
    12. close the pull request by merging the feature branch to the mainline
    13. Check the automated tests running on the CI server against the mainline with the changes from 
    your feature brach integrated
    14. Investigate and fix any issues that may be found 

- You can be even more thorough by provisioning a dedicated staging environment with Terraform or Github codesapces
and deploying your feature branch to the cloud for additional manual testing before closing the pull request.

- You may have many options for setting up a CI server for your Docker app , both online and self-hosted
Popular choices include CircleCI, Jenkins, and Travis and GitHub Actions

## Learn to speak the GitHub Actions Lingo

-GitHub actions lets you specify one or more workflows triggered by 
certain events, like pushing code to a branch or opening a new pull request. Each workflow
can define a number of jobs consisting of steps which will execute on a runner. There are 2 types of 
runners:
    - GitHub-Hosted Runners: Ubuntu Linux, Windows, MacOS
    - Self-Hoted RunnersL On-premises servers that you own and maintain

You can check fro cross-plpateform compatibility

- Unless you say otherwise, the jobs within one workflow will run on separate runners in parallel,
which can be useful for speeding up builds.

- each step of a job is implemented by an **action** that can be either:
    1. a custom shell command or a scrip
    2. A GitHub action defined in another GitHub repo (for example building and pushing Docker Image)

- GitHub uses YAML format for configuring workflows. It looks like for a special `.github/workflows/`
folder in your repository's root folder

- To open editor in GitHub navigate your browser to a file and hit `E` or click oon the pencil icon.

## Create a Workflow using GitHub Actions

While you're edition the `cii.yml` file, give your new workflow a descriptive name and define the events
that should trigger it:

```yaml

name: Continuous Integration

on:
    pull_request:
        branches:
            - master
    push:
        branches:
            - master

jobs:
    build:
        name: Build Docker image and run end-to-end tests
        runs-on: ubuntu-latest
        steps:
            - name : Checkout code from GitHub
              uses: actions/checkout@v3
            - name: Run end-to-end tests
              run: >
                docker compose --profile testing up
                -- build
                --exit-code-from test-service
```

The 2 events that will trigger this workflow are:
    1. Opening or changing a **pull request** against the `master` branch
    2. **Pushing** code or merging a branch into the `master` branch

You can add a few more attributes to each event to narrow down the triggering conditions.

You specify a job identified as build that will run on the latest Ubuntu runner provider by GitHuh
Its first step is to check out the single commit that triggered the workflow using the action/checkout
GitHub action
