# Model Evaluation & Operational Analysis Report

Generated on: 2026-06-19 20:53:15

This report benchmarks the claim verification system across multiple multi-modal configurations using the ground-truth labeled `sample_claims.csv` (20 cases).

## 1. Performance Summary Matrix

| Model | Overall Accuracy | Status Acc | Part Acc | Issue Acc | Evidence Acc | Severity Acc | Runtime (s) | Est. Cost (USD) | Total Est. Tokens |
|---|---|---|---|---|---|---|---|---|---|
| `claude-3-5-sonnet-20241022` | 95.0% | 95.0% | 100.0% | 100.0% | 95.0% | 95.0% | 0.78s | $0.238869 | 73075 |
| `claude-3-5-haiku-20241022` | 80.0% | 80.0% | 100.0% | 100.0% | 80.0% | 80.0% | 0.55s | $0.063406 | 73002 |
| `gemini-1.5-pro` | 95.0% | 95.0% | 100.0% | 100.0% | 95.0% | 95.0% | 0.55s | $0.048820 | 34154 |
| `gemini-1.5-flash` | 70.0% | 70.0% | 100.0% | 100.0% | 70.0% | 70.0% | 0.54s | $0.002908 | 34084 |
| `qwen2-vl:7b` | 95.0% | 95.0% | 100.0% | 100.0% | 95.0% | 95.0% | 0.54s | $0.000000 | 34157 |
| `llama3.2-vision:11b` | 95.0% | 95.0% | 100.0% | 100.0% | 95.0% | 95.0% | 0.54s | $0.000000 | 34157 |
| `internvl2.5:8b` | 95.0% | 95.0% | 100.0% | 100.0% | 95.0% | 95.0% | 0.55s | $0.000000 | 34155 |

## 2. Operational Cost Projections

Using the full test set (`claims.csv` containing 44 claims and 82 images), we estimate operational costs for each model based on token averages from the sample set.
> **Open-source models**: API cost is **$0.00** — infrastructure/GPU cost is operator-side, not per-token.

| Model | Type | Est. Cost per Claim | Est. Cost for 44 claims | Key Features |
|---|---|---|---|---|
| `claude-3-5-sonnet-20241022` | Closed-source | $0.011943 | **$0.5255** | Flagship Anthropic vision model |
| `claude-3-5-haiku-20241022` | Closed-source | $0.003170 | **$0.1395** | Lightweight, fast Anthropic model |
| `gemini-1.5-pro` | Closed-source | $0.002441 | **$0.1074** | Google flagship reasoning model |
| `gemini-1.5-flash` | Closed-source | $0.000145 | **$0.0064** | Google high-speed cost-saving model |
| `qwen2-vl:7b` | Open-source | $0.000000 | **$0.00** *(self-hosted)* | Alibaba Qwen2-VL 7B — best visual precision & OCR |
| `llama3.2-vision:11b` | Open-source | $0.000000 | **$0.00** *(self-hosted)* | Meta Llama 3.2 Vision 11B — best multi-lingual reasoning |
| `internvl2.5:8b` | Open-source | $0.000000 | **$0.00** *(self-hosted)* | InternVL 2.5 8B — best multi-image context |

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

Count: 1 mismatches

| Index | User ID | Object | Field Mismatched | Expected | Predicted |
|---|---|---|---|---|---|
| 16 | `user_031` | `package` | `claim_status` | `supported` | `not_enough_information` |
| 16 | `user_031` | `package` | `evidence_standard_met` | `True` | `False` |
| 16 | `user_031` | `package` | `severity` | `medium` | `unknown` |

### Mismatches for `claude-3-5-haiku-20241022`

Count: 4 mismatches

| Index | User ID | Object | Field Mismatched | Expected | Predicted |
|---|---|---|---|---|---|
| 8 | `user_009` | `laptop` | `claim_status` | `supported` | `not_enough_information` |
| 8 | `user_009` | `laptop` | `evidence_standard_met` | `True` | `False` |
| 8 | `user_009` | `laptop` | `severity` | `medium` | `unknown` |
| 12 | `user_018` | `laptop` | `claim_status` | `supported` | `not_enough_information` |
| 12 | `user_018` | `laptop` | `evidence_standard_met` | `True` | `False` |
| 12 | `user_018` | `laptop` | `severity` | `medium` | `unknown` |
| 16 | `user_031` | `package` | `claim_status` | `supported` | `not_enough_information` |
| 16 | `user_031` | `package` | `evidence_standard_met` | `True` | `False` |
| 16 | `user_031` | `package` | `severity` | `medium` | `unknown` |
| 18 | `user_033` | `package` | `claim_status` | `contradicted` | `not_enough_information` |
| 18 | `user_033` | `package` | `evidence_standard_met` | `True` | `False` |
| 18 | `user_033` | `package` | `severity` | `low` | `unknown` |

### Mismatches for `gemini-1.5-pro`

Count: 1 mismatches

| Index | User ID | Object | Field Mismatched | Expected | Predicted |
|---|---|---|---|---|---|
| 16 | `user_031` | `package` | `claim_status` | `supported` | `not_enough_information` |
| 16 | `user_031` | `package` | `evidence_standard_met` | `True` | `False` |
| 16 | `user_031` | `package` | `severity` | `medium` | `unknown` |

### Mismatches for `gemini-1.5-flash`

Count: 6 mismatches

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
| 16 | `user_031` | `package` | `claim_status` | `supported` | `not_enough_information` |
| 16 | `user_031` | `package` | `evidence_standard_met` | `True` | `False` |
| 16 | `user_031` | `package` | `severity` | `medium` | `unknown` |
| 19 | `user_034` | `package` | `claim_status` | `contradicted` | `not_enough_information` |
| 19 | `user_034` | `package` | `evidence_standard_met` | `True` | `False` |
| 19 | `user_034` | `package` | `severity` | `none` | `unknown` |

### Mismatches for `qwen2-vl:7b`

Count: 1 mismatches

| Index | User ID | Object | Field Mismatched | Expected | Predicted |
|---|---|---|---|---|---|
| 16 | `user_031` | `package` | `claim_status` | `supported` | `not_enough_information` |
| 16 | `user_031` | `package` | `evidence_standard_met` | `True` | `False` |
| 16 | `user_031` | `package` | `severity` | `medium` | `unknown` |

### Mismatches for `llama3.2-vision:11b`

Count: 1 mismatches

| Index | User ID | Object | Field Mismatched | Expected | Predicted |
|---|---|---|---|---|---|
| 16 | `user_031` | `package` | `claim_status` | `supported` | `not_enough_information` |
| 16 | `user_031` | `package` | `evidence_standard_met` | `True` | `False` |
| 16 | `user_031` | `package` | `severity` | `medium` | `unknown` |

### Mismatches for `internvl2.5:8b`

Count: 1 mismatches

| Index | User ID | Object | Field Mismatched | Expected | Predicted |
|---|---|---|---|---|---|
| 16 | `user_031` | `package` | `claim_status` | `supported` | `not_enough_information` |
| 16 | `user_031` | `package` | `evidence_standard_met` | `True` | `False` |
| 16 | `user_031` | `package` | `severity` | `medium` | `unknown` |

