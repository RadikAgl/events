## Запуск celery
```bash
docker compose build 
docker compose up -d redis 
docker compose run --rm celery python manage.py migrate
docker compose up -d celery
```