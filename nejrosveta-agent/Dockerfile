FROM n8nio/n8n:latest

USER root
RUN apk add --no-cache tzdata
ENV TZ=Europe/Moscow

USER node
EXPOSE 5678

HEALTHCHECK --interval=30s --timeout=10s \
  CMD wget -qO- http://localhost:5678/healthz || exit 1
