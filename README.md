# School Backend (Django + DRF)

API для сайта школы: преподаватели, отзывы, контакты и документы с загрузкой/скачиванием.

## Стек
- Python 3.11+ (Django 5.2, DRF, drf-spectacular)
- SQLite по умолчанию
- CORS открыт для всех доменов (corsheaders)

## Быстрый старт
1. Перейдите в папку проекта: `cd /Users/rajymbekadilgereev/Documents/Codes/school`
2. Создайте окружение и установите зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Примените миграции и создайте администратора:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. Запустите dev-сервер: `python manage.py runserver`
5. Полезные ссылки:
   - Swagger UI: `http://127.0.0.1:8000/api/docs/`
   - OpenAPI схема: `http://127.0.0.1:8000/api/schema/`
   - Админка: `http://127.0.0.1:8000/admin/`

## API вкратце
- `GET /api/teachers/` — список активных преподавателей. CRUD доступен админу.
- `GET/POST /api/reviews/` — отзывы; создание доступно анонимно. Троттлинг: `reviews=20/hour`, общий `anon=200/hour`.
- `GET /api/school/` — контакты/описание (возвращает одну запись). `PUT/PATCH` — только админ.
- `GET/POST /api/documents/` — документы с фильтрами `audience`, `category`. Создание/удаление только админ. Скачивание: `GET /api/documents/{id}/download/`.

## Файлы и медиа
- Статичные файлы: `STATIC_ROOT=static/`
- Медиа: `MEDIA_ROOT=media/`
- Фото учителей → `media/teachers/`, документы → `media/docs/%Y/%m`. Для продакшена замените `DEBUG=True`, настройте `ALLOWED_HOSTS`, `DATABASES` и сервер для отдачи статики/медиа.

## Тесты
- Базовый прогон: `python manage.py test`
