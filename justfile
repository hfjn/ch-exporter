set dotenv-load
version := `cat .version`

install:
    poetry install

dev:
    poetry run python3 main.py

run:
    poetry run gunicorn -b 127.0.0.1:8000 main:app -k uvicorn.workers.UvicornWorker --workers 1

docker:
    docker run --env-file .env  docker.io/hfjn/ch_exporter:23.11.03

build:
    docker build -t hfjn/ch_exporter:{{version}} -t hfjn/ch_exporter:latest .

push:
    docker push hfjn/ch_exporter:{{version}}
    docker push hfjn/ch_exporter:latest

_bump_version:
  #! /usr/bin/env python3
  import datetime
  from pathlib import Path
  curr_version = "{{ version }}"
  curr_date = datetime.datetime.now().strftime("%y.%m")
  if curr_date > curr_version:
    curr_version = curr_date + ".01"
  else:
    left, right = curr_version.rsplit('.', 1)
    curr_version = left + f".{(int(right) + 1):02}"

  Path(".version").write_text(curr_version)

  pyproject = []
  for line in Path("pyproject.toml").read_text().splitlines():
    if line.startswith("version = "):
      pyproject.append(f'version = "{curr_version}"')
    else:
      pyproject.append(line)
  Path("pyproject.toml").write_text("\n".join(pyproject))






