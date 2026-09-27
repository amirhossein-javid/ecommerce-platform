# E-commerce API

Production-oriented REST API built with Python 3.12, Django 5.2, Django REST
Framework, PostgreSQL, and Docker.

## Local setup with Docker

1. Copy `.env.example` to `.env` and replace the development secret.
2. Start the services:

   ```bash
   docker compose up --build
   ```

The API is available at `http://localhost:8000`. Useful endpoints:

- Health check: `GET /api/v1/health/`
- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`

## Quality checks

Run these inside the web container:

```bash
docker compose run --rm web pytest
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
docker compose run --rm web python manage.py check
```

## Production proxy settings

HSTS is disabled by default. Set `DJANGO_SECURE_HSTS_SECONDS` only after HTTPS
is working reliably for the production domain.

Set `DJANGO_TRUST_X_FORWARDED_PROTO=True` only when Django runs behind a trusted
reverse proxy that removes any client-supplied `X-Forwarded-Proto` header and
sets the header itself. Leave it disabled when that assumption does not hold.
