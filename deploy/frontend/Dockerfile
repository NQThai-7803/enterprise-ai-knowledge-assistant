# Frontend for a single host (DEMO.md): build the SPA, then serve it with nginx, which also
# proxies /api/ to the API container (deploy/frontend/nginx.conf).
# Build from the repo root: docker build -f deploy/frontend/Dockerfile \
#   --build-arg VITE_API_BASE_URL= -t <tag> .
FROM node:24-alpine AS build
WORKDIR /app
# BR-13: "" (the usual value here) = the page's own origin, so any host name works through this
# nginx; an absolute URL is used as given. It must be passed: left unset, the app would call the
# dev API at http://127.0.0.1:8000.
ARG VITE_API_BASE_URL
ARG VITE_APP_NAME="Enterprise AI Knowledge Assistant"
RUN test "${VITE_API_BASE_URL+set}" = set \
  || (echo 'pass --build-arg VITE_API_BASE_URL= (same origin) or an absolute URL' >&2; exit 1)
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_APP_NAME=$VITE_APP_NAME
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
# nginx.conf is a template; at start the entrypoint writes conf.d/default.conf from it.
ENV FRONTEND_SERVER_NAMES="" \
    NGINX_ENVSUBST_FILTER="FRONTEND_SERVER_NAMES"
RUN rm /etc/nginx/conf.d/default.conf
COPY deploy/frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
