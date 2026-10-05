# AWS architecture

```mermaid
flowchart TB
    U[User browser] -->|HTTPS *.cloudfront.net| CF[CloudFront]
    CF -->|/ (OAC)| S3F[(S3 frontend - private)]
    CF -->|/api/* + X-Origin-Verify| ALB[ALB - CloudFront prefix list only]
    ALB --> API[ECS Fargate - FastAPI]
    U -->|presigned PUT/GET| S3U[(S3 uploads - private)]
    U -->|SRP auth| COG[Cognito User Pool]
    API --> DDB[(DynamoDB x8)]
    API --> S3U
    API --> SQS[[SQS investigation / briefing + DLQs]]
    SQS --> WRK[ECS Fargate worker - Spot]
    WRK --> DDB & S3U
    WRK --> OR[OpenRouter: GPT-6 Luna, Gemini 3.8 Flash, GPT Audio, Gemini Image]
    WRK --> DATA[Yahoo, SEC, GDELT, Alpha Vantage, FRED]
    WRK --> SES[Amazon SES]
    EB[EventBridge Scheduler rate 15 min] --> SCH[ECS one-shot scheduler task]
    SCH --> DDB & SQS
    SM[Secrets Manager] -.loaded at start.-> API & WRK & SCH
    API & WRK & SCH --> CW[CloudWatch Logs]
```

## Do we need a domain? — No

The academic deployment uses the free CloudFront domain (`https://dxxxx.cloudfront.net`) with
AWS's default TLS certificate:

* **HTTPS** works out of the box (CloudFront default certificate).
* **One origin** for UI and API: CloudFront routes `/api/*` to the ALB, so there is no CORS between them.
* **Cognito** works without a hosted UI domain (the SPA talks to Cognito directly).
* **S3 uploads** use presigned URLs with CORS for the CloudFront origin.
* **SES**: without a domain you verify a single sender email address; in the SES sandbox recipients must be verified
  too (enough for the professor/team demo). A domain would only be needed for DKIM-branded email at scale.

The only trade-off: CloudFront → ALB is HTTP inside AWS (no ACM certificate without a domain). The ALB is protected
by CloudFront's managed prefix list + a secret header, and all browser traffic is HTTPS. With a domain you would add
ACM certificates and Route 53 records.

Does deploying make sense at all? The assignment asks for "aplicación desplegada en la nube **o** demo grabada".
A live URL is the strongest evidence of a working MVP and costs only credits; the recorded demo and `VITE_DEMO_MODE`
remain as backup.

## Budget protection (who can use the demo)

Everything below is configured in `terraform.tfvars` — nothing manual:

| Layer | Variable | Effect |
|---|---|---|
| Invite list at sign-up | `allowed_emails = ["a@x.com", "@miax.es"]` | Cognito **pre sign-up Lambda** rejects any other email (account never created). |
| Invite list in the API | same variable (→ `ALLOWED_EMAILS` on ECS) | Every API call checks the email of the token (defence in depth; removing someone from the list revokes access immediately after `terraform apply`). |
| Site password | `site_password = "…"` | CloudFront Function asks for HTTP Basic Auth before serving the web app (user `site_username`). |
| Usage limits | `max_investigations_per_day`, `max_briefings_per_day` | Per-user daily caps (HTTP 429 with a friendly message). |
| Rate limiting | built in | Per-client request limit in the API. |
| Provider budget | OpenRouter dashboard | Set a credit limit on the API key (outside AWS). |

## Terraform layout

```
terraform/
  modules/  networking ecr ecs alb s3 cloudfront cognito dynamodb sqs eventbridge secrets-manager iam ses
  environments/dev/  main.tf variables.tf outputs.tf provider.tf versions.tf terraform.tfvars.example
```

No account ids, passwords, keys or domains are hardcoded. Region defaults to `eu-west-1` (variable `region`).

## Cost decisions

* No NAT Gateway: tasks run in public subnets with public IPs, but their security group only admits the ALB.
  Production would move them to private subnets + NAT/VPC endpoints.
* DynamoDB on-demand, SQS, Scheduler, Secrets Manager: near-zero idle cost.
* Worker on Fargate Spot (SQS makes interruptions safe).
* `api_desired_count = 0` / `worker_desired_count = 0` pauses compute without destroying anything.
* Container Insights disabled; 14-day log retention.

## Deployment

See `NEXT_STEPS.md` for the exact first-deployment checklist. In short:

```bash
cp terraform/environments/dev/terraform.tfvars.example terraform/environments/dev/terraform.tfvars
./scripts/deploy.sh          # ECR → image → terraform apply → SPA → S3/CloudFront → ECS restart
./scripts/set_secrets.sh     # .env keys → Secrets Manager (never via Terraform)
./scripts/deploy.sh --restart-only
```

Windows: `scripts/deploy.ps1`, `scripts/set_secrets.ps1`.
