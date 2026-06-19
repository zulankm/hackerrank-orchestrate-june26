
import os
import argparse
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
import concurrent.futures
from threading import Lock
import re

from src.config import OUTPUT_COLUMNS, MODELS_LIST, MODEL_SONNET
from src.loader import load_user_history, load_evidence_requirements, get_requirements_for_object, resolve_and_check_images
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

def process_row(idx, row, args, dataset_dir, cache_path, user_history, evidence_reqs, sample_df):
    user_id = str(row["user_id"]).strip()
    claim_object = str(row["claim_object"]).strip()
    image_paths = str(row["image_paths"]).strip()
    
    # 1. Resolve history
    history = user_history.get(user_id, {
        "past_claim_count": 0,
        "accept_claim": 0,
        "manual_review_claim": 0,
        "rejected_claim": 0,
        "last_90_days_claim_count": 0,
        "history_flags": "none",
        "history_summary": "New user with no prior claim history"
    })
    
    # 2. Resolve requirements
    reqs = get_requirements_for_object(evidence_reqs, claim_object)
    
    # 3. Process images (includes CV diagnostics)
    base64_images, valid_image_flag, image_errors = resolve_and_check_images(
        image_paths_str=image_paths,
        dataset_dir=dataset_dir
    )
    
    # 4. Build Prompts
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(row, history, reqs)
    
    # 5. Evaluate Claim (incorporating caching and fallback mock)
    pred = evaluate_claim(
        row=row,
        base64_images=base64_images,
        valid_image_flag=valid_image_flag,
        history=history,
        requirements=reqs,
        model_name=args.model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        cache_path=cache_path,
        sample_df=sample_df
    )
    
    # 6. Check pre-flight computer-vision diagnostics (blur / low light)
    # We only degrade if ALL images in the set are bad, or the only image is bad.
    # If at least one image is clear, we keep the decision, but add CV flags as warning.
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
        # Merge pre-flight CV flags into prediction risk_flags
        existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
        for f in diag_flags:
            if f not in existing_flags:
                existing_flags.append(f)
        pred["risk_flags"] = ";".join(existing_flags) if existing_flags else "none"
        
        # If there are quality flags, require manual review
        existing_flags_list = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
        if "manual_review_required" not in existing_flags_list:
            existing_flags_list.append("manual_review_required")
        pred["risk_flags"] = ";".join(existing_flags_list)
        
        # If ALL images are bad, degrade standard and status to not_enough_information
        if not has_clear_image:
            pred["evidence_standard_met"] = False
            pred["evidence_standard_met_reason"] = "Visual standard not met due to quality check failing (all images blurry/low light)."
            pred["claim_status"] = "not_enough_information"
            pred["severity"] = "unknown"
            pred["supporting_image_ids"] = "none"

    # 6.5 Apply Programmatic Evidence-Requirement and Post-Adjudication Escalation Rules
    customer_text = get_customer_text(str(row["user_claim"]))
    
    # 6.5.1 Multi-Part Evidence Check
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
        
    # 6.5.2 Enforce History Override Cap
    if "user_history_risk" in str(history.get("history_flags", "")) or "manual_review_required" in str(history.get("history_flags", "")):
        existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
        if "user_history_risk" not in existing_flags:
            existing_flags.append("user_history_risk")
        pred["risk_flags"] = ";".join(existing_flags)

    # 6.5.3 Programmatic Escalation Triggers
    conf_score = pred.get("confidence_score", 0.5)
    
    # Trigger A: Confidence score < 0.85
    if conf_score < 0.85:
        print(f"  [OPERATIONAL ALERT] Low confidence review ({conf_score:.2f}) for User {user_id} ({claim_object}). Routing to human queue.")
        existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
        if "manual_review_required" not in existing_flags:
            existing_flags.append("manual_review_required")
        pred["risk_flags"] = ";".join(existing_flags)

    # Trigger B: High Severity escalation
    if str(pred["severity"]).strip().lower() == "high":
        existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
        if "manual_review_required" not in existing_flags:
            existing_flags.append("manual_review_required")
        pred["risk_flags"] = ";".join(existing_flags)

    # Trigger C: Any non-none risk flag forces manual review
    existing_flags = [f.strip() for f in pred["risk_flags"].split(";") if f.strip() and f.strip() != "none"]
    if existing_flags and "manual_review_required" not in existing_flags:
        existing_flags.append("manual_review_required")
        pred["risk_flags"] = ";".join(existing_flags)

    # Trigger D: If status is not_enough_information, force standard False and unknown severity
    if pred["claim_status"] == "not_enough_information":
        pred["evidence_standard_met"] = False
        pred["severity"] = "unknown"
        pred["supporting_image_ids"] = "none"

    # Merge input fields with predictions
    result_row = {
        "user_id": row["user_id"],
        "image_paths": row["image_paths"],
        "user_claim": row["user_claim"],
        "claim_object": row["claim_object"],
        "evidence_standard_met": str(pred["evidence_standard_met"]).lower(),
        "evidence_standard_met_reason": pred["evidence_standard_met_reason"],
        "risk_flags": pred["risk_flags"],
        "issue_type": pred["issue_type"],
        "object_part": pred["object_part"],
        "claim_status": pred["claim_status"],
        "claim_status_justification": pred["claim_status_justification"],
        "supporting_image_ids": pred["supporting_image_ids"],
        "valid_image": str(pred["valid_image"]).lower(),
        "severity": pred["severity"]
    }
    
    return idx, result_row

def main():
    # Load .env file if present
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Multi-Modal Evidence Review System")
    parser.add_argument(
        "--input",
        type=str,
        default="dataset/claims.csv",
        help="Path to the input claims CSV file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output.csv",
        help="Path to save the output predictions CSV file"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=MODEL_SONNET,
        choices=MODELS_LIST,
        help="The model configuration to run"
    )
    parser.add_argument(
        "--cache",
        type=str,
        default="dataset/claim_cache.json",
        help="Path to the claim decision cache file"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Maximum thread workers for parallel execution"
    )
    
    args = parser.parse_args()
    
    # Setup paths relative to script parent or repository root
    code_dir = Path(__file__).resolve().parent
    repo_root = code_dir.parent
    
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = repo_root / input_path
        
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
        
    cache_path = Path(args.cache)
    if not cache_path.is_absolute():
        cache_path = repo_root / cache_path
        
    dataset_dir = repo_root / "dataset"
    
    print(f"Starting Multi-Modal Evidence Review System")
    print(f"Model: {args.model}")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Cache: {cache_path}")
    print(f"Max Thread Workers: {args.max_workers}")
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found at {input_path}")
        
    # Preprocessing Layer
    print("Loading datasets...")
    user_history = load_user_history(dataset_dir)
    evidence_reqs = load_evidence_requirements(dataset_dir)
    claims_df = pd.read_csv(input_path)
    
    # Load sample_claims.csv if available for offline mock mode grounding
    sample_claims_path = dataset_dir / "sample_claims.csv"
    sample_df = pd.read_csv(sample_claims_path) if sample_claims_path.exists() else None
    
    results_map = {}
    
    # Run evaluation concurrently
    print(f"Processing {len(claims_df)} claims in parallel...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(
                process_row, idx, row, args, dataset_dir, cache_path, user_history, evidence_reqs, sample_df
            ): idx
            for idx, row in claims_df.iterrows()
        }
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(claims_df), desc="Verifying claims"):
            idx = futures[future]
            try:
                _, result_row = future.result()
                results_map[idx] = result_row
            except Exception as e:
                print(f"Error processing row {idx}: {e}")
                
    # Reassemble results sorted by original index
    results = [results_map[idx] for idx in sorted(results_map.keys())]
        
    # Save output CSV
    output_df = pd.DataFrame(results)
    # Ensure column order matches specifications exactly
    output_df = output_df[OUTPUT_COLUMNS]
    
    # Save to the requested output path
    output_df.to_csv(output_path, index=False)
    print(f"Saved {len(output_df)} predictions to {output_path}")
    
    # Also write to dataset/output.csv as a secondary copy for completion
    secondary_output = dataset_dir / "output.csv"
    output_df.to_csv(secondary_output, index=False)
    print(f"Secondary predictions copy saved to {secondary_output}")

if __name__ == "__main__":
    main()
