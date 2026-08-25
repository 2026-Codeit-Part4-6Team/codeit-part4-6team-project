FROM node:24-alpine

WORKDIR /app/frontend

ARG VITE_NAVER_MAPS_CLIENT_ID
ENV VITE_NAVER_MAPS_CLIENT_ID=$VITE_NAVER_MAPS_CLIENT_ID

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY frontend ./
RUN pnpm build

EXPOSE 8501

CMD ["pnpm", "start"]
