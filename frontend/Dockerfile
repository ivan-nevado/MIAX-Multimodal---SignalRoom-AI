# Multi-stage build: Vite static bundle → nginx.
# Build context is the REPOSITORY ROOT (demo mode bundles ../demo_data).
#   docker build -f frontend/Dockerfile -t signalroom-frontend .
# In AWS the same static bundle is uploaded to S3 + CloudFront (scripts/deploy.sh);
# this image is for local docker-compose and self-hosting.
FROM node:22-alpine AS build
WORKDIR /repo/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
COPY demo_data/ /repo/demo_data/
ARG VITE_API_BASE_URL=""
ARG VITE_COGNITO_USER_POOL_ID=""
ARG VITE_COGNITO_CLIENT_ID=""
ARG VITE_COGNITO_REGION=""
ARG VITE_APP_ENV="docker"
ARG VITE_DEMO_MODE="false"
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL VITE_COGNITO_USER_POOL_ID=$VITE_COGNITO_USER_POOL_ID \
    VITE_COGNITO_CLIENT_ID=$VITE_COGNITO_CLIENT_ID VITE_COGNITO_REGION=$VITE_COGNITO_REGION \
    VITE_APP_ENV=$VITE_APP_ENV VITE_DEMO_MODE=$VITE_DEMO_MODE
RUN npx vite build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/frontend/dist /usr/share/nginx/html
EXPOSE 8080
