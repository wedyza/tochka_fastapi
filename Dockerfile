FROM python:3.13-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN apt-get update \
    && apt-get install libpq-dev gcc -y 

RUN pip install -r /code/requirements.txt

COPY ./app /code/app