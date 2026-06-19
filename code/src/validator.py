import re
from typing import Dict, Any, List
from src.config import (
    ALLOWED_CLAIM_STATUS,
    ALLOWED_ISSUE_TYPES,
    ALLOWED_SEVERITY,
    ALLOWED_OBJECT_PARTS,
    ALLOWED_RISK_FLAGS
)

# Standardize boolean values
def to_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        val_lower = val.lower().strip()
        if val_lower in ("true", "1", "yes", "y", "t"):
            return True
        if val_lower in ("false", "0", "no", "n", "f"):
            return False
    return default

def repair_claim_status(status: Any) -> str:
    if not status or not isinstance(status, str):
        return "not_enough_information"
    status_lower = status.lower().strip()
    # Direct match
    if status_lower in ALLOWED_CLAIM_STATUS:
        return status_lower
    # Alias mapping
    if "support" in status_lower:
        return "supported"
    if "contradict" in status_lower:
        return "contradicted"
    if "not_enough" in status_lower or "information" in status_lower or "lacks" in status_lower or "insufficient" in status_lower:
        return "not_enough_information"
    return "not_enough_information"

def repair_severity(severity: Any) -> str:
    if not severity or not isinstance(severity, str):
        return "unknown"
    sev_lower = severity.lower().strip()
    if sev_lower in ALLOWED_SEVERITY:
        return sev_lower
    # Small aliases
    if sev_lower == "med":
        return "medium"
    if sev_lower == "hi":
        return "high"
    if sev_lower == "lo":
        return "low"
    return "unknown"

def repair_issue_type(issue: Any) -> str:
    if not issue or not isinstance(issue, str):
        return "unknown"
    issue_lower = issue.lower().strip().replace(" ", "_")
    
    # Direct match
    if issue_lower in ALLOWED_ISSUE_TYPES:
        return issue_lower
        
    # Alias lookup
    issue_aliases = {
        "dented": "dent",
        "dents": "dent",
        "scratched": "scratch",
        "scratches": "scratch",
        "cracked": "crack",
        "cracks": "crack",
        "shattered": "glass_shatter",
        "glass": "glass_shatter",
        "shatter": "glass_shatter",
        "broken": "broken_part",
        "missing": "missing_part",
        "torn": "torn_packaging",
        "crushed": "crushed_packaging",
        "wet": "water_damage",
        "water": "water_damage",
        "stained": "stain",
        "oil": "stain",
        "oily": "stain"
    }
    
    for alias, replacement in issue_aliases.items():
        if alias in issue_lower:
            return replacement
            
    return "unknown"

def repair_object_part(part: Any, claim_object: str) -> str:
    if claim_object not in ALLOWED_OBJECT_PARTS:
        return "unknown"
    
    allowed = ALLOWED_OBJECT_PARTS[claim_object]
    if not part or not isinstance(part, str):
        return "unknown"
        
    part_lower = part.lower().strip().replace(" ", "_").replace("-", "_")
    
    # Direct match
    if part_lower in allowed:
        return part_lower
        
    # Standard mappings
    common_mappings = {
        "frontbumper": "front_bumper",
        "rearbumper": "rear_bumper",
        "sidemirror": "side_mirror",
        "backbumper": "rear_bumper",
        "back_bumper": "rear_bumper",
        "left_mirror": "side_mirror",
        "right_mirror": "side_mirror",
        "mirror": "side_mirror",
        "head_light": "headlight",
        "tail_light": "taillight",
        "back_light": "taillight",
        "backlight": "taillight",
        "glass_windshield": "windshield",
        "glass": "windshield",
        "door_panel": "door",
        "bumper": "front_bumper" if claim_object == "car" else "unknown",
        "quarterpanel": "quarter_panel",
        
        # Laptop
        "keyboard_area": "keyboard",
        "keys": "keyboard",
        "keycaps": "keyboard",
        "display": "screen",
        "monitor": "screen",
        "hinges": "hinge",
        "outer_body": "body",
        "base_panel": "base",
        "corners": "corner",
        "palmrest": "body",
        
        # Package
        "box_corner": "package_corner",
        "box_side": "package_side",
        "label_area": "label",
        "shipping_label": "label",
        "product": "contents",
        "item": "contents",
        "inner_item": "contents",
        "tape": "seal",
        "flap": "seal"
    }
    
    if part_lower in common_mappings:
        return common_mappings[part_lower]
        
    for key, val in common_mappings.items():
        if key in part_lower and val in allowed:
            return val
            
    # Fuzzy check
    for allowed_val in allowed:
        if allowed_val in part_lower or part_lower in allowed_val:
            return allowed_val
            
    return "unknown"

def repair_risk_flags(flags: Any) -> str:
    if not flags:
        return "none"
    if isinstance(flags, list):
        flag_list = flags
    elif isinstance(flags, str):
        flag_list = [f.strip() for f in flags.split(";") if f.strip()]
    else:
        return "none"
        
    cleaned_flags = []
    for f in flag_list:
        f_lower = str(f).lower().strip().replace(" ", "_")
        
        # Direct match
        if f_lower in ALLOWED_RISK_FLAGS:
            if f_lower != "none":
                cleaned_flags.append(f_lower)
            continue
            
        # Aliases mapping
        aliases = {
            "blurry": "blurry_image",
            "blur": "blurry_image",
            "obstructed": "cropped_or_obstructed",
            "cropped": "cropped_or_obstructed",
            "obstruction": "cropped_or_obstructed",
            "glare": "low_light_or_glare",
            "reflection": "low_light_or_glare",
            "low_light": "low_light_or_glare",
            "dark": "low_light_or_glare",
            "angle": "wrong_angle",
            "object": "wrong_object",
            "part": "wrong_object_part",
            "not_visible": "damage_not_visible",
            "mismatch": "claim_mismatch",
            "manipulation": "possible_manipulation",
            "fake": "possible_manipulation",
            "non_original": "non_original_image",
            "instruction": "text_instruction_present",
            "text": "text_instruction_present",
            "history": "user_history_risk",
            "manual": "manual_review_required"
        }
        
        matched = False
        for k, v in aliases.items():
            if k in f_lower:
                cleaned_flags.append(v)
                matched = True
                break
        
        if not matched and f_lower != "none":
            # If it's not matched, but is a non-empty string, map to manual review as safety fallback
            cleaned_flags.append("manual_review_required")
            
    # Remove duplicates preserving order
    unique_flags = []
    for f in cleaned_flags:
        if f not in unique_flags:
            unique_flags.append(f)
            
    if not unique_flags:
        return "none"
        
    return ";".join(unique_flags)

def repair_supporting_image_ids(ids: Any) -> str:
    if not ids:
        return "none"
        
    if isinstance(ids, list):
        id_list = ids
    elif isinstance(ids, str):
        # Handle cases like "img_1, img_2" or "img_1; img_2" or "img_1 and img_2"
        delimiters = r"[;,|]|\band\b"
        id_list = [i.strip() for i in re.split(delimiters, ids) if i.strip()]
    else:
        return "none"
        
    cleaned_ids = []
    for i in id_list:
        i_clean = str(i).strip().lower().replace("images/sample/", "").replace("images/test/", "")
        # Remove file extension if present
        i_clean = re.sub(r"\.(jpg|jpeg|png|webp|gif)$", "", i_clean)
        # Extract filename part
        i_clean = i_clean.split("/")[-1].split("\\")[-1]
        
        if i_clean and i_clean != "none":
            cleaned_ids.append(i_clean)
            
    if not cleaned_ids:
        return "none"
        
    return ";".join(cleaned_ids)

def validate_and_repair_output(raw: Dict[str, Any], claim_object: str) -> Dict[str, Any]:
    """
    Validates and repairs a raw dictionary output from the model to match strict schema enums.
    """
    repaired = {}
    
    # Booleans
    repaired["evidence_standard_met"] = to_bool(raw.get("evidence_standard_met"), False)
    repaired["valid_image"] = to_bool(raw.get("valid_image"), False)
    
    # Text reasons
    repaired["evidence_standard_met_reason"] = str(raw.get("evidence_standard_met_reason") or "No reason provided").strip()
    repaired["claim_status_justification"] = str(raw.get("claim_status_justification") or "No justification provided").strip()
    
    # Enums
    repaired["claim_status"] = repair_claim_status(raw.get("claim_status"))
    repaired["severity"] = repair_severity(raw.get("severity"))
    repaired["issue_type"] = repair_issue_type(raw.get("issue_type"))
    repaired["object_part"] = repair_object_part(raw.get("object_part"), claim_object)
    
    # Semicolon-separated lists
    repaired["risk_flags"] = repair_risk_flags(raw.get("risk_flags"))
    repaired["supporting_image_ids"] = repair_supporting_image_ids(raw.get("supporting_image_ids"))
    
    # Confidence Score (between 0.0 and 1.0)
    raw_conf = raw.get("confidence_score")
    if raw_conf is None:
        raw_conf = raw.get("confidence")  # alias check
    try:
        conf_val = float(raw_conf)
        repaired["confidence_score"] = max(0.0, min(1.0, conf_val))
    except Exception:
        repaired["confidence_score"] = 0.5
    
    # If evidence_standard_met is False, claim_status should be not_enough_information and severity should be unknown
    # unless there is a clear contradiction or claim mismatch. We let repair logic stand but ensure schema compliance.
    if not repaired["evidence_standard_met"] and repaired["claim_status"] == "supported":
        repaired["claim_status"] = "not_enough_information"
        repaired["severity"] = "unknown"
        
    return repaired
