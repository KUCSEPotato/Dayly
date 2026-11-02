FROM node:22-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY frontend/ ./
# Browser requests stay on the same origin; Nginx forwards /api to FastAPI.
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM nginx:stable-alpine AS runtime
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
