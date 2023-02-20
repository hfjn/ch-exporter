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

CMD ["poetry", "run", "python", "/app/main.py"]


