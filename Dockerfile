# syntax=docker/dockerfile:1

# ---- Stage 1: build the React/Vite frontend ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

# ---- Stage 2: Python runtime serving the API + built SPA ----
FROM python:3.12.2-slim AS runtime
WORKDIR /app

RUN groupadd --system acrn && useradd --system --gid acrn --home /app acrn

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY --from=frontend /build/dist ./dist

RUN mkdir -p /app/uploads && chown -R acrn:acrn /app

USER acrn
EXPOSE 8000

CMD ["uvicorn", "main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
