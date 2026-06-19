# Configuration and Allowed Values for Multi-Modal Evidence Review

# Output column schema order mapping
OUTPUT_COLUMNS = [
    "user_id",
    "image_paths",
    "user_claim",
    "claim_object",
    "evidence_standard_met",
    "evidence_standard_met_reason",
    "risk_flags",
    "issue_type",
    "object_part",
    "claim_status",
    "claim_status_justification",
    "supporting_image_ids",
    "valid_image",
    "severity"
]

# Allowed values for output fields
ALLOWED_CLAIM_STATUS = ["supported", "contradicted", "not_enough_information"]

ALLOWED_ISSUE_TYPES = [
    "dent",
    "scratch",
    "crack",
    "glass_shatter",
    "broken_part",
    "missing_part",
    "torn_packaging",
    "crushed_packaging",
    "water_damage",
    "stain",
    "none",
    "unknown"
]

ALLOWED_SEVERITY = ["none", "low", "medium", "high", "unknown"]

# Object-specific parts
ALLOWED_OBJECT_PARTS = {
    "car": [
        "front_bumper",
        "rear_bumper",
        "door",
        "hood",
        "windshield",
        "side_mirror",
        "headlight",
        "taillight",
        "fender",
        "quarter_panel",
        "body",
        "unknown"
    ],
    "laptop": [
        "screen",
        "keyboard",
        "trackpad",
        "hinge",
        "lid",
        "corner",
        "port",
        "base",
        "body",
        "unknown"
    ],
    "package": [
        "box",
        "package_corner",
        "package_side",
        "seal",
        "label",
        "contents",
        "item",
        "unknown"
    ]
}

ALLOWED_RISK_FLAGS = [
    "none",
    "blurry_image",
    "cropped_or_obstructed",
    "low_light_or_glare",
    "wrong_angle",
    "wrong_object",
    "wrong_object_part",
    "damage_not_visible",
    "claim_mismatch",
    "possible_manipulation",
    "non_original_image",
    "text_instruction_present",
    "user_history_risk",
    "manual_review_required"
]

# Model Configurations — Closed-Source (API)
MODEL_SONNET = "claude-3-5-sonnet-20241022"
MODEL_HAIKU = "claude-3-5-haiku-20241022"
MODEL_GEMINI_PRO = "gemini-1.5-pro"
MODEL_GEMINI_FLASH = "gemini-1.5-flash"

# Model Configurations — Open-Source (Self-Hosted via Ollama / vLLM)
# These models are served via an OpenAI-compatible local endpoint.
# Default endpoint: http://localhost:11434/v1 (Ollama default)
# Override via OLLAMA_BASE_URL environment variable.
MODEL_QWEN2_VL = "qwen2-vl:7b"         # Alibaba Qwen2-VL 7B — best visual precision & OCR
MODEL_LLAMA_VISION = "llama3.2-vision:11b"  # Meta Llama 3.2 Vision 11B — best multi-lingual reasoning
MODEL_INTERNVL = "internvl2.5:8b"      # OpenGVLab InternVL 2.5 8B — best multi-image context

# Grouped lists
OPENSOURCE_MODELS = [MODEL_QWEN2_VL, MODEL_LLAMA_VISION, MODEL_INTERNVL]
CLOSED_MODELS = [MODEL_SONNET, MODEL_HAIKU, MODEL_GEMINI_PRO, MODEL_GEMINI_FLASH]
MODELS_LIST = CLOSED_MODELS + OPENSOURCE_MODELS

# Local inference server endpoint (Ollama default; override with env var OLLAMA_BASE_URL)
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Pricing assumptions (Cost per 1M tokens)
# Closed-source: USD per 1M tokens billed by the provider.
# Open-source: $0.00 API cost — infrastructure/GPU cost is operator-side, not per-token.
MODEL_PRICING = {
    MODEL_SONNET:      {"input": 3.00,   "output": 15.00, "image": 3.00},
    MODEL_HAIKU:       {"input": 0.80,   "output": 4.00,  "image": 0.80},
    MODEL_GEMINI_PRO:  {"input": 1.25,   "output": 5.00,  "image": 1.25},
    MODEL_GEMINI_FLASH:{"input": 0.075,  "output": 0.30,  "image": 0.075},
    # Open-source: zero marginal API cost (self-hosted)
    MODEL_QWEN2_VL:    {"input": 0.00,   "output": 0.00,  "image": 0.00},
    MODEL_LLAMA_VISION:{"input": 0.00,   "output": 0.00,  "image": 0.00},
    MODEL_INTERNVL:    {"input": 0.00,   "output": 0.00,  "image": 0.00},
}

# Image parameters
IMAGE_MAX_DIM = 1024  # Max width/height to resize before sending (saves tokens/latency)
