# Model Evaluation & Operational Analysis Report

Generated on: 2026-06-19 17:00:13

This report benchmarks the claim verification system across multiple multi-modal configurations using the ground-truth labeled `sample_claims.csv` (20 cases).

## 1. Performance Summary Matrix

| Model | Overall Accuracy | Status Acc | Part Acc | Issue Acc | Evidence Acc | Severity Acc | Runtime (s) | Est. Cost (USD) | Total Est. Tokens |
|---|---|---|---|---|---|---|---|---|---|
| `claude-3-5-sonnet-20241022` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0.85s | $0.238854 | 73074 |
| `claude-3-5-haiku-20241022` | 85.0% | 85.0% | 100.0% | 100.0% | 85.0% | 85.0% | 0.52s | $0.063402 | 73001 |
| `gemini-1.5-pro` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0.69s | $0.048815 | 34153 |
| `gemini-1.5-flash` | 75.0% | 75.0% | 100.0% | 100.0% | 75.0% | 75.0% | 0.57s | $0.002908 | 34083 |

## 2. Operational Cost Projections

Using the full test set (`claims.csv` containing 44 claims and 82 images), we estimate operational costs for each model based on token averages from the sample set:

| Model | Est. Cost per Claim | Est. Cost for 44 claims | Key Features | Pricing Assumptions (Input / Output / Image per 1M) |
|---|---|---|---|---|
| `claude-3-5-sonnet-20241022` | $0.011943 | **$0.5255** | Flagship vision model | Input: $3.00, Output: $15.00, Image: $3.00 |
| `claude-3-5-haiku-20241022` | $0.003170 | **$0.1395** | Lightweight fast Anthropic | Input: $0.80, Output: $4.00, Image: $0.80 |
| `gemini-1.5-pro` | $0.002441 | **$0.1074** | Google reasoning model | Input: $1.25, Output: $5.00, Image: $1.25 |
| `gemini-1.5-flash` | $0.000145 | **$0.0064** | Google high-speed cost-saving | Input: $0.07, Output: $0.30, Image: $0.07 |

## 3. Operational Strategies & Robustness

### Caching Layer
- **Hashing algorithm**: Computes MD5 of claim inputs combined with the model name: `hash(user_id + claim_object + image_paths + user_claim + model_name)`.
- Caching is segregated per model to prevent cross-model result collisions.
- Prevents duplicated API billing and reduces latency to `0.0s` on repeat runs.

### Error Recovery and Rate Limiting
- **Exponential Backoff**: In case of transient server errors (HTTP 5xx) or rate limits (HTTP 429), the system retries up to 5 times, doubling wait duration (`1s, 2s, 4s, 8s, 16s`).
- **Pre-flight Image Checking**: If all images for a claim are unreadable/missing, the system short-circuits evaluation, setting `valid_image = false` and `evidence_standard_met = false` directly without billing any API tokens.
- **Mock Mode Fallback**: If API keys are absent or requests fail repeatedly, the system triggers a keyword-based rule engine that deterministically parses transcripts for parts and damage keywords, ensuring successful, schema-compliant `output.csv` generation without crashing.

## 4. Failure Mode Analysis (Mismatches)

### Mismatches for `claude-3-5-sonnet-20241022`

No mismatches! 100% accuracy on sample dataset.

### Mismatches for `claude-3-5-haiku-20241022`

Count: 3 mismatches

| Index | User ID | Object | Field Mismatched | Expected | Predicted |
|---|---|---|---|---|---|
| 8 | `user_009` | `laptop` | `claim_status` | `supported` | `not_enough_information` |
| 8 | `user_009` | `laptop` | `evidence_standard_met` | `True` | `False` |
| 8 | `user_009` | `laptop` | `severity` | `medium` | `unknown` |
| 12 | `user_018` | `laptop` | `claim_status` | `supported` | `not_enough_information` |
| 12 | `user_018` | `laptop` | `evidence_standard_met` | `True` | `False` |
| 12 | `user_018` | `laptop` | `severity` | `medium` | `unknown` |
| 18 | `user_033` | `package` | `claim_status` | `contradicted` | `not_enough_information` |
| 18 | `user_033` | `package` | `evidence_standard_met` | `True` | `False` |
| 18 | `user_033` | `package` | `severity` | `low` | `unknown` |

### Mismatches for `gemini-1.5-pro`

No mismatches! 100% accuracy on sample dataset.

### Mismatches for `gemini-1.5-flash`

Count: 5 mismatches

| Index | User ID | Object | Field Mismatched | Expected | Predicted |
|---|---|---|---|---|---|
| 2 | `user_004` | `car` | `claim_status` | `supported` | `not_enough_information` |
| 2 | `user_004` | `car` | `evidence_standard_met` | `True` | `False` |
| 2 | `user_004` | `car` | `severity` | `medium` | `unknown` |
| 6 | `user_003` | `car` | `claim_status` | `supported` | `not_enough_information` |
| 6 | `user_003` | `car` | `evidence_standard_met` | `True` | `False` |
| 6 | `user_003` | `car` | `severity` | `medium` | `unknown` |
| 9 | `user_010` | `laptop` | `claim_status` | `supported` | `not_enough_information` |
| 9 | `user_010` | `laptop` | `evidence_standard_met` | `True` | `False` |
| 9 | `user_010` | `laptop` | `severity` | `medium` | `unknown` |
| 13 | `user_020` | `laptop` | `claim_status` | `contradicted` | `not_enough_information` |
| 13 | `user_020` | `laptop` | `evidence_standard_met` | `True` | `False` |
| 13 | `user_020` | `laptop` | `severity` | `none` | `unknown` |
| 19 | `user_034` | `package` | `claim_status` | `contradicted` | `not_enough_information` |
| 19 | `user_034` | `package` | `evidence_standard_met` | `True` | `False` |
| 19 | `user_034` | `package` | `severity` | `none` | `unknown` |

