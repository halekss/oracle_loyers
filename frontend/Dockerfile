# frontend/Dockerfile
#
# Trois étapes :
# - "dev"        : serveur de dev Vite avec hot-reload, utilisée par docker-compose (target: dev).
# - "build"      : compile le bundle de production (npm run build).
# - "production" : étape par défaut (docker build sans --target) — sert le
#                  bundle statique minifié via nginx, aucun serveur de dev.

FROM node:20-slim AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
# wget (busybox) est présent par défaut dans nginx:alpine, pas besoin d'installer curl.
HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=10s \
  CMD wget --quiet --spider http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
