FROM python:3.11.2-slim-bullseye

RUN apt-get update && \
    apt-get upgrade --yes

RUN useradd --create-home realpython  
USER realpython                       
WORKDIR /home/realpython

ENV VIRTUALENV=/home/realpython/venv
RUN python3 -m venv $VIRTUALENV
ENV PATH="$VIRTUALENV/bin:$PATH"