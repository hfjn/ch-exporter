FROM python:3.11 AS builder

# Create workdir
ENV APP_DIRECTORY=/app
WORKDIR $APP_DIRECTORY

RUN pip install poetry

# Install dependencies
COPY . ./
RUN poetry config virtualenvs.in-project true \
  && poetry install --no-interaction --no-ansi -vvv

USER 1000:1000

FROM python:3.11 as publish

# Copy dependencies
COPY --from=builder /app /app
ADD . /app

USER 1000:1000

ENV PYTHONPATH=/app
COPY . .

CMD ["python3", "/app/main.py"]
