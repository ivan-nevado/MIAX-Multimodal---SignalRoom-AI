# Email setup (Amazon SES)

Daily briefing emails are sent through SES v2 (`backend/app/integrations/email/ses.py`) using the template
`backend/app/templates/email/daily_briefing.html` (+ `.txt`). Emails are **never** sent unless the user enables
"Email me the briefing" in Settings. Locally, emails are written to `data/runtime/outbox/` and can be previewed in the
UI (Briefing → **Email preview**).

## Steps (no domain required)

1. Choose a sender address you control, e.g. a team Gmail (`signalroom.briefings@gmail.com`).
2. In `terraform/environments/dev/terraform.tfvars`:
   ```hcl
   ses_from_email         = "signalroom.briefings@gmail.com"
   ses_sandbox_recipients = ["teammate1@gmail.com", "professor@university.edu"]
   ```
3. `terraform apply` (or `./scripts/deploy.sh`). AWS sends a **verification email** to the sender and to each
   recipient — everyone must click the link (check spam).
4. Add `SES_FROM_EMAIL=signalroom.briefings@gmail.com` to `.env` and run `./scripts/set_secrets.sh`, then
   `./scripts/deploy.sh --restart-only` (Terraform also passes it as a plain environment variable).
5. Check identities: `aws sesv2 list-email-identities --region eu-west-1` → `VerificationStatus: SUCCESS`.
6. In the app: Settings → enable Daily briefing + "Email me the briefing", set the time ~15 minutes ahead in your
   timezone. EventBridge runs the scheduler every 15 minutes; the briefing is generated and emailed once.
   For an immediate test: Briefings → "Generate briefing now" with email (API `send_email: true`).

## SES sandbox
New accounts are in the sandbox: you can only send **to verified addresses**, max 200 emails/day, 1/s.
That is enough for the class. Leaving the sandbox requires a production-access request
(SES console → Account dashboard → Request production access) describing the use case.

## Deliverability notes
Sending "from" a Gmail address through SES may land in spam because Gmail's DMARC policy is not aligned with SES.
For the demo this is acceptable (ask recipients to check spam). With a domain you would verify the domain, add DKIM
CNAMEs and a custom MAIL FROM — the module `terraform/modules/ses` is where to add it.

## Unsubscribe
Each email contains a "Manage preferences or unsubscribe" link to `/app/settings#briefing`.
