FROM node:24-alpine

WORKDIR /app/frontend

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY frontend ./
RUN pnpm build

EXPOSE 8501

CMD ["pnpm", "start"]
