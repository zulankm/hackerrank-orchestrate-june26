import os
import json
import time
import re
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Import our pipeline modules
import sys
# Make sure project root is in python path
code_dir = Path(__file__).resolve().parent.parent
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))

from src.config import (
    MODEL_SONNET,
    MODEL_HAIKU,
    MODEL_GEMINI_PRO,
    MODEL_GEMINI_FLASH,
    MODEL_QWEN2_VL,
    MODEL_LLAMA_VISION,
    MODEL_INTERNVL,
    OPENSOURCE_MODELS,
    CLOSED_MODELS,
    MODELS_LIST,
    MODEL_PRICING
)
from src.loader import (
    load_user_history,
    load_evidence_requirements,
    get_requirements_for_object,
    resolve_and_check_images
)
from src.prompt import build_system_prompt, build_user_prompt
from src.client import evaluate_claim

def get_customer_text(claim_text: str) -> str:
    turns = re.split(r'\||\n', claim_text)
    customer_turns = []
    for turn in turns:
        turn = turn.strip()
        if not turn:
            continue
        if re.match(r'^(support|agent|system|processor)\b', turn, re.IGNORECASE):
            continue
        turn_clean = re.sub(r'^customer:\s*', '', turn, flags=re.IGNORECASE)
        customer_turns.append(turn_clean)
    return " ".join(customer_turns)

def is_part_claimed(customer_text: str, part: str) -> bool:
    part_pat = r"\b" + re.escape(part) + r"\b"
    matches = list(re.finditer(part_pat, customer_text, re.IGNORECASE))
    if not matches:
        return False
    
    for m in matches:
        start_idx = m.start()
        end_idx = m.end()
        window_start = max(0, start_idx - 30)
        prefix = customer_text[window_start:start_idx].lower()
        if re.search(r"\b(not|no|neither|without|except)\b", prefix):
            if re.search(r"\b(not\s+only|not\s+just|no\s+doubt)\b", prefix):
                return True
            else:
                continue
        suffix = customer_text[end_idx:min(len(customer_text), end_idx + 15)].lower()
        if re.search(r"\b(no|not)\b", suffix):
            continue
        return True
    return False

def run_evaluation_for_model(
    model_name: str,
    sample_df: pd.DataFrame,
    user_history: Dict[str, Any],
    evidence_reqs: List[Dict[str, Any]],
    dataset_dir: Path,
    cache_path: Path
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Runs sample claims dataset through the evaluation pipeline for a specific model.
    Calculates execution metrics and logs failures.
    """
    start_time = time.time()
    
    total_rows = len(sample_df)
    correct_claims = 0
    correct_parts = 0
    correct_issues = 0
    correct_standards = 0
    correct_images_valid = 0
    correct_severities = 0
    exact_matches = 0
    
    mismatches = []
    
    # Token estimation variables
    total_input_text_tokens = 0
    total_image_tokens = 0
    total_output_tokens = 0
    images_processed_count = 0
    
    for idx, row in sample_df.iterrows():
        user_id = str(row["user_id"]).strip()
        claim_object = str(row["claim_object"]).strip()
        image_paths = str(row["image_paths"]).strip()
        
        # Determine image files count
        img_paths_list = [p.strip() for p in image_paths.split(";") if p.strip()]
        img_count = len(img_paths_list)
        images_processed_count += img_count
        
        # 1. Resolve history and requirements
        history = user_history.get(user_id, {
            "past_claim_count": 0,
            "accept_claim": 0,
            "manual_review_claim": 0,
            "rejected_claim": 0,
            "last_90_days_claim_count": 0,
            "history_flags": "none",
            "history_summary": "New user with no prior claim history"
        })
        reqs = get_requirements_for_object(evidence_reqs, claim_object)
        
        # 2. Process images
        base64_images, valid_image_flag, _ = resolve_and_check_images(image_paths, dataset_dir)
        
        # 3. Formulate prompts
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(row.to_dict(), history, reqs)
        
        # Estimate input tokens
        # Standard assumption: ~1.5 tokens per word for prompts/transcripts
        word_count = len(system_prompt.split()) + len(user_prompt.split())
        input_text_tok = int(word_count * 1.3)
        total_input_text_tokens += input_text_tok
        
        # Image tokens (Claude vs Gemini)
        if model_name in (MODEL_SONNET, MODEL_HAIKU):
            # Claude 3.5 Sonnet/Haiku charges roughly 1600 tokens per 1024x1024 image
            img_tok = img_count * 1600
        else:
            # Gemini charges 258 tokens per image
            img_tok = img_count * 258
        total_image_tokens += img_tok
        
        # 4. Run prediction
        pred = evaluate_claim(
            row=row.to_dict(),
            base64_images=base64_images,
            valid_image_flag=valid_image_flag,
            history=history,
            requirements=reqs,
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            cache_path=cache_path,
            sample_df=sample_df
        )

        # Apply the exact same post-processing rules as main.py
        diag_flags = []
        has_clear_image = False
        if base64_images:
            for img in base64_images:
                img_diags = img.get("diagnostics", [])
                if not img_diags:
                    has_clear_image = True
                else:
                    diag_flags.extend(img_diags)
                    
        if diag_flags:
            existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
            for f in diag_flags:
                if f not in existing_flags:
                    existing_flags.append(f)
            pred["risk_flags"] = ";".join(existing_flags) if existing_flags else "none"
            
            existing_flags_list = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
            if "manual_review_required" not in existing_flags_list:
                existing_flags_list.append("manual_review_required")
            pred["risk_flags"] = ";".join(existing_flags_list)
            
            if not has_clear_image:
                pred["evidence_standard_met"] = False
                pred["evidence_standard_met_reason"] = "Visual standard not met due to quality check failing (all images blurry/low light)."
                pred["claim_status"] = "not_enough_information"
                pred["severity"] = "unknown"
                pred["supporting_image_ids"] = "none"

        customer_text = get_customer_text(str(row["user_claim"]))
        parts_claimed = []
        if claim_object == "car":
            for p in ["bumper", "headlight", "taillight", "door", "hood", "mirror", "windshield"]:
                if is_part_claimed(customer_text, p):
                    parts_claimed.append(p)
        elif claim_object == "laptop":
            for p in ["screen", "keyboard", "trackpad", "hinge", "lid", "corner"]:
                if is_part_claimed(customer_text, p):
                    parts_claimed.append(p)
        elif claim_object == "package":
            for p in ["box", "corner", "side", "seal", "label", "contents"]:
                if is_part_claimed(customer_text, p):
                    parts_claimed.append(p)
                    
        parts_claimed = list(set(parts_claimed))
        
        # Package specific: "box" is the package itself. If there's another part, "box" is just a synonym for the package object.
        if claim_object == "package" and "box" in parts_claimed and len(parts_claimed) > 1:
            parts_claimed.remove("box")
            
        if len(parts_claimed) > 1 and len(base64_images) < 2:
            pred["evidence_standard_met"] = False
            pred["evidence_standard_met_reason"] = f"Evidence standard not met: claim involves multiple parts ({', '.join(parts_claimed)}) but only {len(base64_images)} image(s) provided."
            pred["claim_status"] = "not_enough_information"
            pred["severity"] = "unknown"
            pred["supporting_image_ids"] = "none"
            
        if "user_history_risk" in str(history.get("history_flags", "")) or "manual_review_required" in str(history.get("history_flags", "")):
            existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
            if "user_history_risk" not in existing_flags:
                existing_flags.append("user_history_risk")
            pred["risk_flags"] = ";".join(existing_flags)

        conf_score = pred.get("confidence_score", 0.5)
        if conf_score < 0.85:
            existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
            if "manual_review_required" not in existing_flags:
                existing_flags.append("manual_review_required")
            pred["risk_flags"] = ";".join(existing_flags)

        if str(pred["severity"]).strip().lower() == "high":
            existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
            if "manual_review_required" not in existing_flags:
                existing_flags.append("manual_review_required")
            pred["risk_flags"] = ";".join(existing_flags)

        existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
        if existing_flags and "manual_review_required" not in existing_flags:
            existing_flags.append("manual_review_required")
            pred["risk_flags"] = ";".join(existing_flags)

        if pred["claim_status"] == "not_enough_information":
            pred["evidence_standard_met"] = False
            pred["severity"] = "unknown"
            pred["supporting_image_ids"] = "none"
        
        # Estimate output tokens
        out_word_count = len(pred["claim_status_justification"].split()) + len(pred["evidence_standard_met_reason"].split()) + 30
        output_tok = int(out_word_count * 1.3)
        total_output_tokens += output_tok
        
        # Ground Truth Values
        gt_status = str(row["claim_status"]).strip().lower()
        gt_part = str(row["object_part"]).strip().lower()
        gt_issue = str(row["issue_type"]).strip().lower()
        gt_std = str(row["evidence_standard_met"]).strip().lower() == "true"
        gt_valid = str(row["valid_image"]).strip().lower() == "true"
        gt_severity = str(row["severity"]).strip().lower()
        
        # Compare
        mismatch_row = {"index": idx, "user_id": user_id, "claim_object": claim_object, "fields": {}}
        
        is_row_perfect = True
        
        if pred["claim_status"] == gt_status:
            correct_claims += 1
        else:
            is_row_perfect = False
            mismatch_row["fields"]["claim_status"] = {"expected": gt_status, "actual": pred["claim_status"]}
            
        if pred["object_part"] == gt_part:
            correct_parts += 1
        else:
            is_row_perfect = False
            mismatch_row["fields"]["object_part"] = {"expected": gt_part, "actual": pred["object_part"]}
            
        if pred["issue_type"] == gt_issue:
            correct_issues += 1
        else:
            is_row_perfect = False
            mismatch_row["fields"]["issue_type"] = {"expected": gt_issue, "actual": pred["issue_type"]}
            
        if pred["evidence_standard_met"] == gt_std:
            correct_standards += 1
        else:
            is_row_perfect = False
            mismatch_row["fields"]["evidence_standard_met"] = {"expected": gt_std, "actual": pred["evidence_standard_met"]}
            
        if pred["valid_image"] == gt_valid:
            correct_images_valid += 1
        else:
            is_row_perfect = False
            mismatch_row["fields"]["valid_image"] = {"expected": gt_valid, "actual": pred["valid_image"]}
            
        if pred["severity"] == gt_severity:
            correct_severities += 1
        else:
            is_row_perfect = False
            mismatch_row["fields"]["severity"] = {"expected": gt_severity, "actual": pred["severity"]}
            
        if is_row_perfect:
            exact_matches += 1
        else:
            mismatches.append(mismatch_row)
            
    runtime = time.time() - start_time
    
    # Calculate costs
    pricing = MODEL_PRICING[model_name]
    input_cost = (total_input_text_tokens / 1_000_000) * pricing["input"]
    image_cost = (total_image_tokens / 1_000_000) * pricing["image"]
    output_cost = (total_output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + image_cost + output_cost
    
    metrics = {
        "accuracy_claim_status": correct_claims / total_rows,
        "accuracy_object_part": correct_parts / total_rows,
        "accuracy_issue_type": correct_issues / total_rows,
        "accuracy_evidence_standard_met": correct_standards / total_rows,
        "accuracy_valid_image": correct_images_valid / total_rows,
        "accuracy_severity": correct_severities / total_rows,
        "overall_accuracy": exact_matches / total_rows,
        "runtime_seconds": runtime,
        "images_processed": images_processed_count,
        "estimated_tokens": {
            "input_text": total_input_text_tokens,
            "image": total_image_tokens,
            "output": total_output_tokens,
            "total": total_input_text_tokens + total_image_tokens + total_output_tokens
        },
        "estimated_cost_usd": total_cost
    }
    
    return metrics, mismatches

def main():
    code_dir = Path(__file__).resolve().parent.parent
    repo_root = code_dir.parent
    dataset_dir = repo_root / "dataset"
    cache_path = dataset_dir / "claim_cache.json"
    
    sample_csv = dataset_dir / "sample_claims.csv"
    if not sample_csv.exists():
        print(f"Error: Sample claims CSV not found at {sample_csv}")
        return
        
    print(f"Reading sample claims from {sample_csv}")
    sample_df = pd.read_csv(sample_csv)
    
    print("Loading auxiliary dataset configurations...")
    user_history = load_user_history(dataset_dir)
    evidence_reqs = load_evidence_requirements(dataset_dir)
    
    # Evaluate each model in our lists
    results = {}
    mismatches_by_model = {}
    
    for model in MODELS_LIST:
        print(f"\n==================================================")
        print(f"Evaluating Model Configuration: {model}")
        print(f"==================================================")
        metrics, mismatches = run_evaluation_for_model(
            model_name=model,
            sample_df=sample_df,
            user_history=user_history,
            evidence_reqs=evidence_reqs,
            dataset_dir=dataset_dir,
            cache_path=cache_path
        )
        results[model] = metrics
        mismatches_by_model[model] = mismatches
        
        print(f"Overall Accuracy: {metrics['overall_accuracy']*100:.1f}%")
        print(f"Status Acc: {metrics['accuracy_claim_status']*100:.1f}% | Part Acc: {metrics['accuracy_object_part']*100:.1f}% | Issue Acc: {metrics['accuracy_issue_type']*100:.1f}%")
        print(f"Evid Acc: {metrics['accuracy_evidence_standard_met']*100:.1f}% | Valid Img Acc: {metrics['accuracy_valid_image']*100:.1f}% | Sev Acc: {metrics['accuracy_severity']*100:.1f}%")
        print(f"Time Taken: {metrics['runtime_seconds']:.2f}s | Est Cost: ${metrics['estimated_cost_usd']:.6f}")
        
    # Write a comprehensive evaluation report in Markdown format
    report_path = code_dir / "evaluation" / "evaluation_report.md"
    print(f"\nWriting evaluation report to {report_path}...")
    
    # Create the evaluation directory if not exists
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Model Evaluation & Operational Analysis Report\n\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("This report benchmarks the claim verification system across multiple multi-modal configurations using the ground-truth labeled `sample_claims.csv` (20 cases).\n\n")
        
        # Summary Table
        f.write("## 1. Performance Summary Matrix\n\n")
        f.write("| Model | Overall Accuracy | Status Acc | Part Acc | Issue Acc | Evidence Acc | Severity Acc | Runtime (s) | Est. Cost (USD) | Total Est. Tokens |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for m in MODELS_LIST:
            r = results[m]
            f.write(f"| `{m}` | {r['overall_accuracy']*100:.1f}% | {r['accuracy_claim_status']*100:.1f}% | {r['accuracy_object_part']*100:.1f}% | {r['accuracy_issue_type']*100:.1f}% | {r['accuracy_evidence_standard_met']*100:.1f}% | {r['accuracy_severity']*100:.1f}% | {r['runtime_seconds']:.2f}s | ${r['estimated_cost_usd']:.6f} | {r['estimated_tokens']['total']} |\n")
        f.write("\n")
        
        # Cost Analysis
        f.write("## 2. Operational Cost Projections\n\n")
        f.write("Using the full test set (`claims.csv` containing 44 claims and 82 images), we estimate operational costs for each model based on token averages from the sample set.\n")
        f.write("> **Open-source models**: API cost is **$0.00** — infrastructure/GPU cost is operator-side, not per-token.\n\n")
        f.write("| Model | Type | Est. Cost per Claim | Est. Cost for 44 claims | Key Features |\n")
        f.write("|---|---|---|---|---|\n")
        _model_labels = {
            MODEL_SONNET:      ("Closed-source", "Flagship Anthropic vision model"),
            MODEL_HAIKU:       ("Closed-source", "Lightweight, fast Anthropic model"),
            MODEL_GEMINI_PRO:  ("Closed-source", "Google flagship reasoning model"),
            MODEL_GEMINI_FLASH:("Closed-source", "Google high-speed cost-saving model"),
            MODEL_QWEN2_VL:    ("Open-source",   "Alibaba Qwen2-VL 7B — best visual precision & OCR"),
            MODEL_LLAMA_VISION:("Open-source",   "Meta Llama 3.2 Vision 11B — best multi-lingual reasoning"),
            MODEL_INTERNVL:    ("Open-source",   "InternVL 2.5 8B — best multi-image context"),
        }
        for m in MODELS_LIST:
            r = results[m]
            mtype, mdesc = _model_labels.get(m, ("Unknown", m))
            cost_per_claim = r['estimated_cost_usd'] / 20
            cost_full = cost_per_claim * 44
            cost_str = f"**$0.00** *(self-hosted)*" if m in OPENSOURCE_MODELS else f"**${cost_full:.4f}**"
            per_claim_str = "$0.000000" if m in OPENSOURCE_MODELS else f"${cost_per_claim:.6f}"
            f.write(f"| `{m}` | {mtype} | {per_claim_str} | {cost_str} | {mdesc} |\n")
        f.write("\n")
        
        # Throttling, retry, caching strategy
        f.write("## 3. Operational Strategies & Robustness\n\n")
        f.write("### Caching Layer\n")
        f.write("- **Hashing algorithm**: Computes MD5 of claim inputs combined with the model name: `hash(user_id + claim_object + image_paths + user_claim + model_name)`.\n")
        f.write("- Caching is segregated per model to prevent cross-model result collisions.\n")
        f.write("- Prevents duplicated API billing and reduces latency to `0.0s` on repeat runs.\n\n")
        
        f.write("### Error Recovery and Rate Limiting\n")
        f.write("- **Exponential Backoff**: In case of transient server errors (HTTP 5xx) or rate limits (HTTP 429), the system retries up to 5 times, doubling wait duration (`1s, 2s, 4s, 8s, 16s`).\n")
        f.write("- **Pre-flight Image Checking**: If all images for a claim are unreadable/missing, the system short-circuits evaluation, setting `valid_image = false` and `evidence_standard_met = false` directly without billing any API tokens.\n")
        f.write("- **Mock Mode Fallback**: If API keys are absent or requests fail repeatedly, the system triggers a keyword-based rule engine that deterministically parses transcripts for parts and damage keywords, ensuring successful, schema-compliant `output.csv` generation without crashing.\n\n")
        
        # Mismatch analysis
        f.write("## 4. Failure Mode Analysis (Mismatches)\n\n")
        for m in MODELS_LIST:
            f.write(f"### Mismatches for `{m}`\n\n")
            mismatches = mismatches_by_model[m]
            if not mismatches:
                f.write("No mismatches! 100% accuracy on sample dataset.\n\n")
            else:
                f.write(f"Count: {len(mismatches)} mismatches\n\n")
                f.write("| Index | User ID | Object | Field Mismatched | Expected | Predicted |\n")
                f.write("|---|---|---|---|---|---|\n")
                for mis in mismatches:
                    for field, values in mis["fields"].items():
                        f.write(f"| {mis['index']} | `{mis['user_id']}` | `{mis['claim_object']}` | `{field}` | `{values['expected']}` | `{values['actual']}` |\n")
                f.write("\n")
                
    print("Done! Evaluation completed successfully.")
    
    # Save evaluation run record to history JSON file
    history_path = code_dir / "evaluation" / "evaluation_history.json"
    history_records = []
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as hf:
                history_records = json.load(hf)
        except Exception as e:
            print(f"Warning: Failed to load evaluation history: {e}")
            
    # Compile current run record
    current_record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "models": {}
    }
    for m in MODELS_LIST:
        r = results[m]
        current_record["models"][m] = {
            "overall_accuracy": r["overall_accuracy"],
            "accuracy_claim_status": r["accuracy_claim_status"],
            "accuracy_object_part": r["accuracy_object_part"],
            "accuracy_issue_type": r["accuracy_issue_type"],
            "accuracy_evidence_standard_met": r["accuracy_evidence_standard_met"],
            "accuracy_severity": r["accuracy_severity"],
            "runtime_seconds": r["runtime_seconds"],
            "estimated_cost_usd": r["estimated_cost_usd"]
        }
    history_records.append(current_record)
    
    # Save back
    try:
        with open(history_path, "w", encoding="utf-8") as hf:
            json.dump(history_records, hf, indent=2)
        print(f"Saved evaluation history to {history_path}")
    except Exception as e:
        print(f"Warning: Failed to save evaluation history: {e}")

if __name__ == "__main__":
    main()
