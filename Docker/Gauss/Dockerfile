# Stage 1: Build stage
FROM python:3.7.17-slim-bullseye AS builder

# Install system dependencies including build-essential for compilation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    gcc \
    libpq-dev \
    locales \
    locales-all \
    build-essential \
    libattr1-dev && \
    rm -rf /var/lib/apt/lists/*

# Set up the locale
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# Copy and install Python dependencies
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Stage 2: Final image
FROM python:3.7.17-slim-bullseye

RUN apt-get update && apt-get install -y locales locales-all && rm -rf /var/lib/apt/lists/*

# Set locale
RUN locale-gen es_ES.UTF-8
ENV LANG es_ES.UTF-8
ENV LANGUAGE es_ES:es
ENV LC_ALL es_ES.UTF-8

# Copy built Python dependencies from the previous stage
COPY --from=builder /usr/local/lib/python3.7/site-packages/ /usr/local/lib/python3.7/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy scripts and set permissions
COPY ./scripts/cleanMigration.sh /usr/local/bin/cleanMigration.sh
COPY ./scripts/re_migrations.sh /usr/local/bin/re_migrations.sh
COPY ./scripts/worker_start.sh /usr/local/bin/start-celeryworker.sh
COPY ./scripts/django_start.sh /usr/local/bin/start-django.sh

RUN sed -i 's/\r$//g' /usr/local/bin/cleanMigration.sh \
    /usr/local/bin/re_migrations.sh \
    /usr/local/bin/start-celeryworker.sh \
    /usr/local/bin/start-django.sh \
    && chmod +x /usr/local/bin/cleanMigration.sh \
    /usr/local/bin/re_migrations.sh \
    /usr/local/bin/start-celeryworker.sh \
    /usr/local/bin/start-django.sh

RUN mkdir -p /var/www/python/gauss3

# Switch to non-root user
RUN adduser -u 5678 --disabled-password --gecos "" appuser \
    && chown -R appuser /var/www/python/gauss3/
USER appuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Set working directory
WORKDIR /var/www/python/gauss3
