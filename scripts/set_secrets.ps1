# PowerShell version of set_secrets.sh — loads API keys from .env into AWS Secrets Manager.
# Values are never printed. Usage:  ./scripts/set_secrets.ps1  [-SecretId signalroom/dev/app]
param(
  [string]$SecretId = "",
  [string]$EnvFile = "$PSScriptRoot/../.env"
)
$ErrorActionPreference = "Stop"
$tfDir = Join-Path $PSScriptRoot "../terraform/environments/dev"
if (-not (Test-Path $EnvFile)) { throw "Missing $EnvFile (copy .env.example)" }
if (-not $SecretId) { $SecretId = (terraform -chdir="$tfDir" output -raw secret_name) }
$region = if ($env:AWS_REGION) { $env:AWS_REGION } else { (terraform -chdir="$tfDir" output -raw region) }

$values = @{}
Get-Content $EnvFile | ForEach-Object {
  $line = $_.Trim()
  if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
    $k, $v = $line.Split("=", 2)
    $values[$k.Trim()] = ($v -split " #")[0].Trim().Trim('"').Trim("'")
  }
}
$openrouter = if ($values["OPENROUTER_API_KEY"]) { $values["OPENROUTER_API_KEY"] } else { $values["OPEN_ROUTER_API_KEY"] }
if (-not $openrouter -and -not $values["OPENAI_API_KEY"] -and -not $values["GEMINI_API_KEY"]) { throw "No AI key found in .env" }
$secret = [ordered]@{
  OPENROUTER_API_KEY   = "$openrouter"
  OPENAI_API_KEY       = "$($values['OPENAI_API_KEY'])"
  GEMINI_API_KEY       = "$($values['GEMINI_API_KEY'])"
  ALPHAVANTAGE_API_KEY = "$($values['ALPHAVANTAGE_API_KEY'])"
  FRED_API_KEY         = "$($values['FRED_API_KEY'])"
  SEC_USER_AGENT       = if ($values["SEC_USER_AGENT"]) { $values["SEC_USER_AGENT"] } else { "SignalRoom AI academic prototype (contact: signalroom-demo@example.com)" }
  SES_FROM_EMAIL       = "$($values['SES_FROM_EMAIL'])"
}
$tmp = New-TemporaryFile
try {
  $secret | ConvertTo-Json -Compress | Set-Content -Path $tmp -Encoding utf8NoBOM
  aws secretsmanager put-secret-value --region $region --secret-id $SecretId --secret-string "file://$tmp" | Out-Null
  Write-Host "Secret '$SecretId' updated with keys: $(($secret.GetEnumerator() | Where-Object { $_.Value } | ForEach-Object Key) -join ', ')"
} finally {
  Remove-Item $tmp -Force
}
