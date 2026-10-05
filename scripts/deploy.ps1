# PowerShell version of deploy.sh. Usage:
#   ./scripts/deploy.ps1                  full deploy
#   ./scripts/deploy.ps1 -FrontendOnly    rebuild + upload the SPA
#   ./scripts/deploy.ps1 -RestartOnly     restart ECS services (after set_secrets.ps1)
param([switch]$FrontendOnly, [switch]$RestartOnly, [string]$ImageTag = "")
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$tfDir = Join-Path $root "terraform/environments/dev"
function Out([string]$name) { (terraform -chdir="$tfDir" output -raw $name) }
if (-not $ImageTag) { $ImageTag = (git -C $root rev-parse --short HEAD) }

function Restart-Services {
  $cluster = Out "ecs_cluster"; $region = Out "region"
  foreach ($svc in @((Out "ecs_api_service"), (Out "ecs_worker_service"))) {
    aws ecs update-service --region $region --cluster $cluster --service $svc --force-new-deployment | Out-Null
    Write-Host "restarted $svc"
  }
}

function Publish-Frontend {
  Write-Host "Building frontend"
  Push-Location (Join-Path $root "frontend")
  try {
    npm ci --no-audit --no-fund
    $env:VITE_API_BASE_URL = ""
    $env:VITE_COGNITO_USER_POOL_ID = Out "cognito_user_pool_id"
    $env:VITE_COGNITO_CLIENT_ID = Out "cognito_client_id"
    $env:VITE_COGNITO_REGION = Out "region"
    $env:VITE_APP_ENV = "dev"; $env:VITE_DEMO_MODE = "false"
    npx vite build
  } finally { Pop-Location }
  $bucket = Out "frontend_bucket"
  aws s3 sync "$root/frontend/dist/" "s3://$bucket/" --delete --cache-control "public,max-age=31536000,immutable" --exclude index.html
  aws s3 cp "$root/frontend/dist/index.html" "s3://$bucket/index.html" --cache-control "no-cache"
  aws cloudfront create-invalidation --distribution-id (Out "cloudfront_distribution_id") --paths "/index.html" "/" | Out-Null
  Write-Host "Frontend published"
}

if ($RestartOnly) { Restart-Services; exit 0 }
if ($FrontendOnly) { Publish-Frontend; exit 0 }

terraform -chdir="$tfDir" init -input=false | Out-Null
$repo = ""
try { $repo = Out "ecr_repository_url" } catch { }
if (-not $repo) {
  Write-Host "First run: creating the ECR repository"
  terraform -chdir="$tfDir" apply -input=false -auto-approve -target=module.ecr
  $repo = Out "ecr_repository_url"
}
$region = $repo.Split(".")[3]
Write-Host "Building & pushing $repo`:$ImageTag"
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $repo.Split("/")[0]
docker build --platform linux/amd64 -t "$repo`:$ImageTag" -t "$repo`:latest" (Join-Path $root "backend")
docker push "$repo`:$ImageTag"
docker push "$repo`:latest"

terraform -chdir="$tfDir" apply -input=false -auto-approve -var "image_tag=$ImageTag"
$secret = Out "secret_name"
aws secretsmanager get-secret-value --region $region --secret-id $secret 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Warning "Secret $secret has no value yet: run ./scripts/set_secrets.ps1 then ./scripts/deploy.ps1 -RestartOnly" }

Publish-Frontend
Restart-Services
Write-Host "SignalRoom deployed: $(Out 'app_url')  (API docs: $(Out 'api_docs_url'))"
