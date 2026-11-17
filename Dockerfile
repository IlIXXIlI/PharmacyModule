FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

ARG INSTALL_POSTGRES=false
RUN if [ "$INSTALL_POSTGRES" = "true" ]; then \
      python -m pip install --no-cache-dir '.[postgres]'; \
    else \
      python -m pip install --no-cache-dir .; \
    fi

ENV DATABASE_BACKEND=sqlite \
    SQLITE_DATABASE_PATH=/app/data/pharmacy.db \
    PYTHONUNBUFFERED=1

VOLUME ["/app/data"]
CMD ["python", "-m", "pharmacy", "interactive"]
