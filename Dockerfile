FROM python:3.11-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install runtime deps with pip (use pinned minimal if available)
COPY requirements-pinned-minimal.txt ./
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-pinned-minimal.txt

COPY . /app

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# copy installed packages from build stage site-packages
COPY --from=build /usr/local /usr/local

COPY --from=build /app /app

EXPOSE 8000
CMD ["python", "run_app.py"]
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy constraints/requirements first for caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

EXPOSE 8080

# Use gunicorn to serve the Flask app; the WSGI app is `app` in `web/app.py`
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "web.app:app"]
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_ENV=production
ENV DOWNLOADS_DIR=/app/web/static/downloads

RUN mkdir -p ${DOWNLOADS_DIR}

EXPOSE 5000

CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "web.app:app"]
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

WORKDIR /app

# Install build deps needed by some packages (lxml, cryptography etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential gcc libxml2-dev libxslt1-dev libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Create writable directories
RUN mkdir -p /app/results /app/uzs_filedrop /app/tmp_uploads \
    && chown -R www-data:www-data /app/results /app/uzs_filedrop /app/tmp_uploads

USER www-data

EXPOSE 5000

CMD ["gunicorn", "web.app:app", "--bind", "0.0.0.0:5000", "--workers", "3", "--threads", "2", "--log-level", "info"]
