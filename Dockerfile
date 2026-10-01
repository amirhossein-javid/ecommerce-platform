# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

ARG REQUIREMENTS_FILE=requirements/production.txt

COPY requirements ./requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r "${REQUIREMENTS_FILE}" \
    && groupadd --gid 10001 django \
    && useradd --uid 10001 --gid django --no-create-home \
        --shell /usr/sbin/nologin django

COPY --chown=django:django . .

RUN mkdir /app/staticfiles /app/media \
    && chown django:django /app/staticfiles /app/media

USER django

RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY=StaticBuildKey-A7x9-StaticBuildKey-B4m2-StaticBuildKey-C8q6 \
    DJANGO_JWT_SIGNING_KEY=StaticJwtKey-R5v1-StaticJwtKey-T9p3-StaticJwtKey-W2n7 \
    DJANGO_ALLOWED_HOSTS=static-build.invalid \
    DATABASE_URL=postgresql://localhost/static \
    python manage.py collectstatic --noinput --clear

EXPOSE 8000

STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "/app/docker/healthcheck.py"]

CMD ["gunicorn"]
