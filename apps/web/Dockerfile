FROM node:22-alpine AS build
WORKDIR /workspace/apps/web
RUN corepack enable
COPY apps/web/package.json ./package.json
COPY apps/web/pnpm-lock.yaml ./pnpm-lock.yaml
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

FROM nginx:1.29-alpine
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/web/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=10 CMD wget -q -O - http://127.0.0.1/ >/dev/null || exit 1
