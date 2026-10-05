# Cost analysis

## AI inference — measured, not estimated

Measured from real runs recorded on 2026-10-05 (`demo_data/*.json`, field `model_usage`, cost reported by OpenRouter):

| Flow | Model calls | Cost (USD) | Latency |
|---|---|---|---|
| "Why did NVIDIA move?" — text agents (plan, news labels, risk, synthesis) | 4 × GPT-6 Luna | **≈ $0.0026** | 35–75 s end to end (data retrieval dominates) |
| + narrated audio brief (≈2 min) | 2 × GPT Audio Mini | ≈ $0.007 | ≈ 14 s |
| + follow-up question | 1 × GPT-6 Luna | ≈ $0.0007 | ≈ 6–9 s |
| + visual brief (optional, on demand) | 1 × Gemini 3.1 Flash Image | ≈ $0.067 | ≈ 8 s |
| Multimodal research: 2-min earnings call + 2-page PDF | GPT-6 Luna ×4, Gemini 3.8 Flash ×2 | **≈ $0.0195** | ≈ 50 s |
| — of which transcription (Gemini 3.8 Flash, audio in) | 1 | ≈ $0.0106 | ≈ 15–21 s |
| — of which document vision (1 table page) | 1 | ≈ $0.0064 | ≈ 9–11 s |
| Video research: 2-min results webinar (speech + 4 slides) | GPT-6 Luna ×3, Gemini 3.8 Flash ×1, embeddings ×1 | **≈ $0.031** | ≈ 60 s |
| — of which video analysis (Gemini 3.8 Flash, audio + frames in one call) | 1 | ≈ $0.029 | ≈ 35 s |
| Semantic-search indexing of one investigation (≈ 20–25 passages, Gemini Embedding 2) | 1 batched call | ≈ $0.0004 | ≈ 1 s |
| One search query (text) | 1 embedding | < $0.0001 | < 1 s + index load |
| Daily briefing with audio | 1 × GPT-6 Luna + 2 × TTS | **≈ $0.0085** | ≈ 60 s |

**Unit economics (illustrative).** A Pro user running 3 investigations/day + a daily audio briefing ≈
3 × $0.01 + $0.0085 ≈ $0.04/day ≈ **$1.2/month** of inference — well below a €19/month price point. A free user with a
daily text briefing and 1 investigation/week costs a few cents per month. The image model is the most expensive
call, which is why visual briefs are on demand only.

Cost controls built in: deterministic calculations in Python, retrieval before any model call, news deduplicated and
clustered before labelling (headlines only), one synthesis call, cached provider data, follow-ups reuse context,
TTS only when requested/enabled, audio and images never regenerated if unchanged, cheapest capable model per role
(model ids are configurable env vars).

## AWS infrastructure

Prices depend on region and usage; check the official pricing pages before deploying. The main drivers for the
`dev` environment are:

| Service | Driver | Notes | Pricing |
|---|---|---|---|
| Application Load Balancer | hourly + LCU | Largest fixed cost of the stack | https://aws.amazon.com/elasticloadbalancing/pricing/ |
| ECS Fargate | vCPU-hours + GB-hours | API 0.5 vCPU/1 GB + worker 1 vCPU/2 GB (Spot) always on; scheduler task ≈ 1 min every 15 min | https://aws.amazon.com/fargate/pricing/ |
| Public IPv4 addresses | per hour per IP | One per running task + ALB | https://aws.amazon.com/vpc/pricing/ |
| CloudFront | requests + data out | Free tier covers a class demo | https://aws.amazon.com/cloudfront/pricing/ |
| DynamoDB on-demand | requests + storage | Pennies at demo scale | https://aws.amazon.com/dynamodb/pricing/ |
| S3 | storage + requests | Uploads expire after 90 days | https://aws.amazon.com/s3/pricing/ |
| SQS, EventBridge Scheduler | requests | Within free tiers at demo scale | https://aws.amazon.com/sqs/pricing/ , https://aws.amazon.com/eventbridge/pricing/ |
| Secrets Manager | per secret per month + API calls | 1 secret | https://aws.amazon.com/secrets-manager/pricing/ |
| Cognito | MAUs | Free tier covers the demo | https://aws.amazon.com/cognito/pricing/ |
| SES | per 1,000 emails | Negligible | https://aws.amazon.com/ses/pricing/ |
| CloudWatch Logs | ingestion + storage | 14-day retention | https://aws.amazon.com/cloudwatch/pricing/ |
| ECR | storage | 10 images kept | https://aws.amazon.com/ecr/pricing/ |

Deliberately avoided: NAT Gateway, RDS, OpenSearch, ElastiCache, EKS, MSK, paid vector DBs, paid news feeds.
Use the AWS Pricing Calculator (https://calculator.aws/) with these parameters for an exact monthly estimate, and set
`api_desired_count = 0`, `worker_desired_count = 0` when not demoing. `terraform destroy` removes everything.

## External data APIs
Yahoo (yfinance), GDELT, SEC EDGAR: free. Alpha Vantage and FRED: free keys, optional.
