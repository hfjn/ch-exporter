set dotenv-load
version := `cat .version`

install:
    poetry install

run:
    poetry run python3 main.py

docker:
    docker run --env-file .env  hfjn/ch_exporter

build:
    docker build -t hfjn/ch_exporter:{{version}} -t hfjn/ch_exporter:latest .

push:
    docker push hfjn/ch_exporter:{{version}} --all-tags

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






