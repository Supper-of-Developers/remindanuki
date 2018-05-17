FROM python:alpine3.7

LABEL maintainer K.Naito

RUN pip install --upgrade pip \
    && pip install flask gunicorn line-bot-sdk redis mysql-connector-python-rf pytz sqlalchemy  \
    && mkdir /app \
    && apk add --update busybox-suid
    

WORKDIR /app

COPY ./crontabs/root /etc/crontabs/
