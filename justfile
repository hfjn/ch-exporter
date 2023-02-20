set dotenv-load

install:
    poetry install

run:
    poetry run python3 main.py

docker:
    docker run --env-file .env  hfjn/ch_exporter

build:
    docker build -t hfjn/ch_exporter .

push:
    docker push hfjn/ch_exporter