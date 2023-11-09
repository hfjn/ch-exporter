FROM python:3.11

# Create workdir
ENV APP_DIRECTORY=/app
WORKDIR $APP_DIRECTORY

RUN pip install poetry

# Install dependencies
COPY . ./
RUN poetry config virtualenvs.in-project true \
  && poetry install --no-interaction --no-ansi -vvv

USER 1000:1000

CMD ["/app/.venv/bin/python3", "-m", "gunicorn", "-b", "127.0.0.1:8000", "main:app", "-k", "uvicorn.workers.UvicornWorker", "--workers", "1"]


