#!/usr/bin/env bash
# Deploy SignalRoom to AWS (dev environment).
#   1. terraform apply (ECR first on the very first run)
#   2. build + push the backend image to ECR (linux/amd64)
#   3. terraform apply (all infrastructure, tasks reference the pushed image)
#   4. build the SPA with Cognito ids from Terraform outputs, sync to S3, invalidate CloudFront
#   5. force a new ECS deployment so tasks pick up the image and the secret
#
# Usage:  ./scripts/deploy.sh                 full deploy
#         ./scripts/deploy.sh --frontend-only rebuild + upload the SPA
#         ./scripts/deploy.sh --restart-only  restart ECS services (e.g. after set_secrets.sh)
# Requires: aws CLI v2 (credentials configured), terraform >= 1.6, docker, node 20+.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="terraform -chdir=$ROOT/terraform/environments/dev"
MODE="${1:-full}"
TAG="${IMAGE_TAG:-$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || date +%s)}"

out() { $TF output -raw "$1"; }

restart() {
  local cluster; cluster="$(out ecs_cluster)"
  for svc in "$(out ecs_api_service)" "$(out ecs_worker_service)"; do
    aws ecs update-service --region "$(out region)" --cluster "$cluster" --service "$svc" --force-new-deployment >/dev/null
    echo "restarted $svc"
  done
}

frontend() {
  echo "> Building frontend"
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund && \
    VITE_API_BASE_URL="" \
    VITE_COGNITO_USER_POOL_ID="$(out cognito_user_pool_id)" \
    VITE_COGNITO_CLIENT_ID="$(out cognito_client_id)" \
    VITE_COGNITO_REGION="$(out region)" \
    VITE_APP_ENV="dev" VITE_DEMO_MODE="false" npx vite build)
  aws s3 sync "$ROOT/frontend/dist/" "s3://$(out frontend_bucket)/" --delete \
    --cache-control "public,max-age=31536000,immutable" --exclude index.html
  aws s3 cp "$ROOT/frontend/dist/index.html" "s3://$(out frontend_bucket)/index.html" --cache-control "no-cache"
  aws cloudfront create-invalidation --distribution-id "$(out cloudfront_distribution_id)" --paths "/index.html" "/" >/dev/null
  echo "Frontend published"
}

case "$MODE" in
  --restart-only) restart; exit 0 ;;
  --frontend-only) frontend; exit 0 ;;
esac

echo "> Terraform init"
$TF init -input=false >/dev/null
if ! $TF output -raw ecr_repository_url >/dev/null 2>&1; then
  echo "> First run: creating the ECR repository"
  $TF apply -input=false -auto-approve -target=module.ecr
fi

REPO="$(out ecr_repository_url)"
REGION="$(echo "$REPO" | cut -d. -f4)"
echo "> Building & pushing backend image $REPO:$TAG"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${REPO%%/*}"
docker build --platform linux/amd64 -t "$REPO:$TAG" -t "$REPO:latest" "$ROOT/backend"
docker push "$REPO:$TAG"
docker push "$REPO:latest"

echo "> Terraform apply"
$TF apply -input=false -auto-approve -var "image_tag=$TAG"

SECRET="$(out secret_name)"
if ! aws secretsmanager get-secret-value --region "$REGION" --secret-id "$SECRET" >/dev/null 2>&1; then
  echo "WARNING: secret $SECRET has no value yet -> run ./scripts/set_secrets.sh then ./scripts/deploy.sh --restart-only"
fi

frontend
restart
echo
echo "SignalRoom deployed: $(out app_url)"
echo "API docs:           $(out api_docs_url)"
