import json
from pathlib import Path
from typing import Dict, Any, List
from src.config import (
    ALLOWED_CLAIM_STATUS,
    ALLOWED_ISSUE_TYPES,
    ALLOWED_SEVERITY,
    ALLOWED_OBJECT_PARTS,
    ALLOWED_RISK_FLAGS
)

def load_templates() -> Dict[str, str]:
    """Loads prompt templates from prompt_templates.json."""
    templates_path = Path(__file__).resolve().parent / "prompt_templates.json"
    try:
        with open(templates_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load prompt templates from {templates_path}: {e}")
        return {
            "system_prompt_template": "",
            "user_prompt_template": ""
        }

def build_system_prompt() -> str:
    """
    Builds the system prompt outlining the role, rules, enums, and structured reasoning process.
    """
    templates = load_templates()
    parts_by_object_str = "\n".join([f"- {obj}: {', '.join(parts)}" for obj, parts in ALLOWED_OBJECT_PARTS.items()])
    
    template = templates.get("system_prompt_template", "")
    return template.format(
        allowed_claim_status=", ".join(ALLOWED_CLAIM_STATUS),
        allowed_severity=", ".join(ALLOWED_SEVERITY),
        allowed_issue_types=", ".join(ALLOWED_ISSUE_TYPES),
        parts_by_object_str=parts_by_object_str,
        allowed_risk_flags=", ".join(ALLOWED_RISK_FLAGS)
    )

def build_user_prompt(row: Dict[str, Any], history: Dict[str, Any], requirements: List[Dict[str, Any]]) -> str:
    """
    Builds the user prompt injection containing the claim row details, user history context, and specific requirements.
    """
    templates = load_templates()
    claim_object = row["claim_object"]
    user_claim = row["user_claim"]
    image_paths = row["image_paths"]
    user_id = row["user_id"]
    
    # Format requirements
    req_lines = []
    for r in requirements:
        req_lines.append(f"- Requirement [{r['requirement_id']}] for '{r['applies_to']}': {r['minimum_image_evidence']}")
    reqs_str = "\n".join(req_lines)
    
    # Format user history
    hist_str = f"""- Past Claim Count: {history.get('past_claim_count', 0)}
- Accepted Claims: {history.get('accept_claim', 0)}
- Claims in Manual Review: {history.get('manual_review_claim', 0)}
- Rejected Claims: {history.get('rejected_claim', 0)}
- Last 90 Days Claims: {history.get('last_90_days_claim_count', 0)}
- History Flags: {history.get('history_flags', 'none')}
- History Summary: {history.get('history_summary', 'New user / no prior history')}"""

    template = templates.get("user_prompt_template", "")
    return template.format(
        user_id=user_id,
        claim_object=claim_object,
        claim_object_upper=claim_object.upper(),
        image_paths=image_paths,
        user_claim=user_claim,
        reqs_str=reqs_str,
        hist_str=hist_str
    )
