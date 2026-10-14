# Global Economic Futures, 2026–2030: static explorer image.
# Build for linux/amd64 (Render free Docker hosts). Context: this directory.
#   docker build --platform linux/amd64 -t gef-explorer:local .
FROM --platform=linux/amd64 python:3.13.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=10000 \
    SITE_ROOT=/app/site

# Unprivileged system user; no login shell, no home directory.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app

WORKDIR /app
# Only the server and the built site are copied (see .dockerignore). Owned by root, read-only to the app user.
COPY serve.py /app/serve.py
COPY site/ /app/site/
RUN chmod -R a+rX /app && chmod 0644 /app/serve.py

USER 10001:10001
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python3", "-c", "import os,sys,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','10000'), timeout=4); sys.exit(0)"]

CMD ["python3", "/app/serve.py"]
