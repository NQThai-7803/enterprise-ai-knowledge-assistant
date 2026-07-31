FROM node:24-alpine AS build
WORKDIR /app
ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ARG VITE_APP_NAME="Enterprise AI Knowledge Assistant"
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_APP_NAME=$VITE_APP_NAME
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:24-alpine AS runtime
ENV NODE_ENV=production
ENV PORT=8080
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY server.mjs ./server.mjs
USER node
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
CMD ["node", "server.mjs"]