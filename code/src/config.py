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

# Model Configurations
MODEL_SONNET = "claude-3-5-sonnet-20241022"
MODEL_HAIKU = "claude-3-5-haiku-20241022"
MODEL_GEMINI_PRO = "gemini-1.5-pro"
MODEL_GEMINI_FLASH = "gemini-1.5-flash"

MODELS_LIST = [MODEL_SONNET, MODEL_HAIKU, MODEL_GEMINI_PRO, MODEL_GEMINI_FLASH]

# Pricing assumptions (Cost per 1M tokens)
# Values represent USD per 1M input / output tokens
MODEL_PRICING = {
    MODEL_SONNET: {"input": 3.00, "output": 15.00, "image": 3.00},  # image token cost is roughly same as input
    MODEL_HAIKU: {"input": 0.80, "output": 4.00, "image": 0.80},
    MODEL_GEMINI_PRO: {"input": 1.25, "output": 5.00, "image": 1.25},
    MODEL_GEMINI_FLASH: {"input": 0.075, "output": 0.30, "image": 0.075}
}

# Image parameters
IMAGE_MAX_DIM = 1024  # Max width/height to resize before sending (saves tokens/latency)
