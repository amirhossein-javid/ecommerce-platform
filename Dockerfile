FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

ARG REQUIREMENTS_FILE=requirements/production.txt

COPY requirements ./requirements
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r "${REQUIREMENTS_FILE}"

COPY . .

RUN addgroup --system django \
    && adduser --system --ingroup django django \
    && chown -R django:django /app

USER django

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]

