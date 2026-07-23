FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN groupadd --system aplicativo \
    && useradd --system --gid aplicativo aplicativo

COPY requirements.txt requirements-api.txt ./
RUN python -m pip install -r requirements-api.txt

COPY api ./api
COPY src ./src

USER aplicativo

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

