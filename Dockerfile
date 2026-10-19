# One image with the API and the built frontend:
#   docker build -t compass .
#   docker run -p 8000:8000 -v compass-data:/data compass
# then open http://localhost:8000. See wiki/Getting-Started.md for the environment variables.

FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Same origin as the API, so the browser calls /api/... directly.
ENV VITE_API_BASE=""
RUN npm run build

FROM python:3.13-slim
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist
RUN useradd --create-home compass && mkdir -p /data && chown compass /data
USER compass
ENV COMPASS_STATIC_DIR=/app/frontend/dist \
    COMPASS_CACHE_PATH=/data/cache.sqlite3 \
    COMPASS_DB_PATH=/data/compass.db \
    COMPASS_CORS_ORIGINS=http://localhost:8000 \
    PORT=8000
VOLUME /data
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
