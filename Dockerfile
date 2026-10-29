FROM python:3.12-slim AS base

# PyMuPDF and sqlite-vec both ship compiled wheels for common platforms, but
# we still need libgomp/libstdc++ present for PyMuPDF's rendering backend.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

# Local/container defaults. Render production overrides DATABASE_URL and uses
# Supabase Storage, so the free service does not depend on persistent disk.
ENV DATABASE_URL=sqlite:////data/receiptmind.db \
    UPLOAD_DIR=/data/uploads \
    PORT=8000

RUN mkdir -p /data/uploads

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
