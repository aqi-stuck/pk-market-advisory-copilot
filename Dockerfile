FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install poetry==1.7.1 poetry-plugin-export

COPY pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry lock --no-update 2>/dev/null || true \
    && poetry install --no-interaction --no-root

COPY . .

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
