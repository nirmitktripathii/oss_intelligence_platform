# Amazon Bedrock / Nova: external blocker evidence

Submission note for judges. The Bedrock integration is code-complete and tested; live Nova
responses are blocked by an account-level restriction on the AWS side, not by the code.

## Summary

- Region: `us-east-1`. Account plan: Paid, with hackathon credits.
- Every Bedrock Converse call fails with `ValidationException: Operation not allowed`.
  This holds for Amazon Nova 2 Lite/Pro/Lite/Micro and Anthropic Claude Haiku 4.5, which
  rules out a model-specific cause.
- The Bedrock API key authenticates; the request reaches the Converse operation and is
  rejected.
- All on-demand Bedrock inference quotas on the account are applied at `0` (table below).
  The documented Nova 2 Lite defaults are non-zero. The requests-per-minute quota is not
  adjustable through Service Quotas.
- Devpost staff advised this is typically an account-level trust restriction that Service
  Quotas and model-access requests cannot resolve.

## Support trail

| Item | Reference | Date |
| --- | --- | --- |
| AWS Support case (Technical) | 179043719800889 | opened 2026-09-26; AWS replied 2026-10-01: under manual review by the Service team |
| Service limit increase request (Nova 2 Lite, 100 RPM / 200K TPM) | submitted via the service limit increase form | 2026-10-01 |
| Second case (Account and billing, verification expedite) | _add case ID when opened_ | |
| AWS re:Post question | _add link when posted_ | |
| Devpost organisers | email thread with Devpost staff; Discord help-forum post | 2026-09-30 |

## Quotas applied at 0 (read with `aws service-quotas list-service-quotas`, 2026-10-01)

| Quota | Code | Applied value |
| --- | --- | --- |
| Cross-region model inference requests per minute, Nova 2 Lite | L-F06F1187 | 0 |
| Cross-region model inference tokens per minute, Nova 2 Lite | L-C6F5908D | 0 |
| Global cross-region requests per minute, Nova 2 Lite | L-D5F39C2F | 0 |
| Global cross-region tokens per minute, Nova 2 Lite | L-71C69B70 | 0 |
| Model invocation max tokens per day, Nova 2 Lite | L-210172B5 | 0 |
| Global cross-region tokens per day, Nova 2 Lite | L-AD940EDE | 0 |
| Cross-region requests per minute, Claude Haiku 4.5 | L-CCA5DF70 | 0 |
| Cross-region tokens per minute, Claude Haiku 4.5 | L-58BE175A | 0 |
| Global cross-region requests per minute, Claude Haiku 4.5 | L-E5084BBA | 0 |
| Global cross-region tokens per minute, Claude Haiku 4.5 | L-9A11C666 | 0 |

For contrast, non-inference quotas such as batch records per job (100,000) show normal
values, so the zeros are specific to on-demand inference.

## What works today

The provider chain falls back automatically (`bedrock` then `gemini`, `groq`, `openai`,
`ollama`), so the product runs end to end on Gemini. Each mission records which provider
answered. Once AWS lifts the restriction, `backend/scripts/check_bedrock.py` verifies a live
Nova response and the provenance shows `bedrock:us.amazon.nova-2-lite-v1:0`.

## Reproduce

```
python backend/scripts/check_bedrock.py
```

Expected today: `FAILED` with `Operation not allowed`. Expected once unblocked:
`OK ... via bedrock:us.amazon.nova-2-lite-v1:0`.
