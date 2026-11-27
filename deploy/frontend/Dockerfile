# Frontend for a single host (DEMO.md): build the SPA, then serve it with nginx, which also
# proxies /api/ to the API container (deploy/frontend/nginx.conf).
# Build from the repo root: docker build -f deploy/frontend/Dockerfile \
#   --build-arg VITE_API_BASE_URL=http://127.0.0.1:18480 -t <tag> .
FROM node:24-alpine AS build
WORKDIR /app
# The browser origin of this nginx. The client needs an absolute URL; an empty value would fall
# back to http://127.0.0.1:8000, so it is required.
ARG VITE_API_BASE_URL
ARG VITE_APP_NAME="Enterprise AI Knowledge Assistant"
RUN test -n "$VITE_API_BASE_URL" || (echo "set --build-arg VITE_API_BASE_URL" >&2; exit 1)
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_APP_NAME=$VITE_APP_NAME
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY deploy/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
