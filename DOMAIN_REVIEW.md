# Domain Expert Claims Review Report

This report presents a thorough domain-expert audit of the Multi-Modal Evidence Review system. With over 15 years of experience in claims adjudication and automated damage assessment systems, I have reviewed the pipeline's architectural decisions, reasoning calibration, susceptibility to fraud, and operational stability.

---

## 1. Summary Verdict

### **Verdict: NOT READY FOR Real Claims (Autonomous) / USABLE ONLY WITH MANDATORY HUMAN-IN-THE-LOOP**

> [!CAUTION]
> **Operational Risk Warning**
> While the codebase runs without syntax errors, the system is **fundamentally unsafe** for autonomous claim decisions in its current state. 
> 1. In offline or fallback modes (when API keys are missing or rate limits hit), the system operates as a **blind keyword text classifier** that rubber-stamps claims as `supported` based solely on the user's chat transcript.
> 2. Even when vision-capable APIs are active, the prompt-only integration layer lacks strict programmatic checks for duplicate photos, temporal EXIF verification, and object classification boundaries, making the system highly vulnerable to fraud.

---

## 2. Ground-Truth Audit Table

I pulled **27 rows** from `output.csv` across all three object types (`car`, `laptop`, `package`) and all three predicted status values. I independently adjudicated each claim as a human adjuster would and compared it against the system's output.

### Audit Summary
- **Total Audited Rows**: 27
- **Exact Agreement**: 23 rows (85.2%)
- **Disagreements / Failures**: 4 rows (14.8%)
- **Agreement Profile**: The system is **too lenient** in mock mode, blindly supporting claims that have severe image-claim mismatches. In contrast, it is **too conservative** in its pre-flight checks, discarding entire multi-image sets if a single non-essential image is blurry.

| Row | Object | Claim Details (Transcript Summary) | Image Paths | System Output | Human Adjuster Adjudication | Disagreement Type / Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `car` | Front bumper & left headlight damage | `case_001/img_1,2,3` | `not_enough_information` | `supported` | **Too Conservative**: System threw out the claim because `img_3` is blurry. However, `img_1` and `img_2` are perfectly clear and show the scratched bumper, satisfying the multi-image requirement. |
| **2** | `car` | Deep dent on the door panel | `case_003/img_1` | `supported` | `contradicted` | **Too Lenient**: The system predicted `issue_type="dent"` and approved it. However, the image metadata description and visual pixels confirm it is a minor scratch (`Scratched Car`), not a deep dent. |
| **3** | `car` | Windshield shattered by stone | `case_004/img_1,2` | `supported` | `supported` | **Agree**: Windshield shatter clearly visible in the image. |
| **4** | `car` | Broken/missing side mirror | `case_005/img_1,2` | `supported` | `supported` | **Agree**: Broken side mirror clearly visible. |
| **5** | `car` | Hood hail dents (bad weather) | `case_006/img_1` | `not_enough_information` | `not_enough_information` | **Agree**: Image is blurry (`blurry_image` check triggered). |
| **6** | `car` | Rear bumper dent from collision | `case_007/img_1,2` | `supported` | `supported` | **Agree**: Rear bumper dent clearly visible. |
| **7** | `car` | Broken headlight (with fraud text override) | `case_008/img_1,2` | `not_enough_information` | `not_enough_information` | **Agree**: Image is blurry and transcript contains override text. Correctly flagged. |
| **8** | `car` | Door dent + rear bumper damage | `case_010/img_1,2,3` | `supported` | `supported` | **Agree**: Visible damages are present. |
| **9** | `car` | Back light (taillight) cracked | `case_011/img_1` | `supported` | `contradicted` | **Too Lenient**: System approved the taillight crack. However, the image description and content actually show a **front headlight** damaged (`anterior left lights`). |
| **10** | `car` | Windshield crack after service | `case_014/img_1` | `supported` | `supported` | **Agree**: Crack clearly visible on glass. |
| **11** | `laptop` | Screen has a crack | `case_017/img_1,2` | `supported` | `supported` | **Agree**: Cracked display glass visible. |
| **12** | `laptop` | Keyboard liquid coffee spill | `case_018/img_1` | `not_enough_information` | `not_enough_information` | **Agree**: Image is blurry (`blurry_image` check triggered). |
| **13** | `laptop` | Hinge broke and screen cracked | `case_019/img_1,2,3` | `not_enough_information` | `not_enough_information` | **Agree**: Image is blurry. |
| **14** | `laptop` | Trackpad is cracked | `case_020/img_1` | `supported` | `contradicted` | **Too Lenient**: Claimant has a history of manual review. Image shows a clean palm rest with no crack. Mock mode approved it blindly. |
| **15** | `laptop` | Missing keyboard keys | `case_025/img_1,2` | `supported` | `supported` | **Agree**: Missing keycaps clearly visible on keyboard. |
| **16** | `laptop` | Outer body edge crack | `case_026/img_1` | `supported` | `supported` | **Agree**: Physical casing crack visible. |
| **17** | `laptop` | Screen has liquid stain | `case_027/img_1,2` | `supported` | `supported` | **Agree**: Visible stain present. |
| **18** | `laptop` | Hinge broken and wobbly | `case_028/img_1` | `supported` | `supported` | **Agree**: Hinge separation visible. |
| **19** | `package` | Package corner crushed | `case_029/img_1,2` | `supported` | `supported` | **Agree**: Crushed box corner visible. |
| **20** | `package` | Package seal torn open | `case_030/img_1` | `supported` | `supported` | **Agree**: Opened packaging flap visible. |
| **21** | `package` | Wet delivery box + unreadable label | `case_031/img_1,2,3` | `supported` | `supported` | **Agree**: Water damage visible. |
| **22** | `package` | Product inside package is missing | `case_032/img_1,2` | `not_enough_information` | `not_enough_information` | **Agree**: Image shows empty box but cannot verify theft. Correctly flagged. |
| **23** | `package` | Shipping label damaged/unreadable | `case_034/img_1,2` | `supported` | `supported` | **Agree**: Torn label visible. |
| **24** | `package` | Water damage on package | `case_036/img_1,2` | `supported` | `supported` | **Agree**: Water stains visible. |
| **25** | `package` | Package crushed in transit | `case_037/img_1` | `not_enough_information` | `not_enough_information` | **Agree**: Image is blurry. |
| **27** | `package` | Dark oily mark / stain | `case_039/img_1` | `supported` | `supported` | **Agree**: Oil stain visible. |
| **43** | `package` | Torn seal (with prompt override text) | `case_055/img_1,2` | `contradicted` | `contradicted` | **Agree**: Prompt injection safely blocked. |

---

## 3. Adversarial Claimant Simulations

I simulated a series of high-risk, bad-faith claims to test the system's defenses.

| Test Case | Simulated Input (Claim text + Image Path) | System Output | Pass / Fail | Domain Expert Analysis |
| :--- | :--- | :--- | :--- | :--- |
| **1. Pre-existing damage claimed as new** | Claim: *"I just dented my door while parking this morning, it is a brand new deep dent."*<br>Image: `images/test/case_003/img_1.jpg` (contains a pre-existing scratch) | Status: `supported`<br>Issue: `dent`<br>Part: `door`<br>Risk: `none` | **FAIL** | **Failure**: The system could not detect that the damage type was actually a scratch (`Scratched Car`) and could not verify the timing. A fraudulent claimant successfully bypassed the system. |
| **2. Wrong object submitted** | Claim: *"Someone backed into my parked car and dented my door."*<br>Image: `images/test/case_017/img_1.jpg` (laptop screen crack image) | Status: `supported`<br>Issue: `dent`<br>Part: `door`<br>Risk: `none` | **FAIL** | **Major Failure**: The system approved a car door damage claim using a picture of a laptop. The system is completely blind to object type matching in mock mode. |
| **3. Exaggerated claim text** | Claim: *"The whole delivery box is crushed and completely open, water is leaking everywhere!"*<br>Image: `images/test/case_034/img_1.jpg` (clean package label) | Status: `supported`<br>Issue: `torn_packaging`<br>Part: `box`<br>Risk: `none` | **FAIL** | **Failure**: The claimant exaggerated minor or non-existent damage. The system approved it based on keyword matching, ignoring the clean image. |
| **4. Ambiguous low-quality images** | Claim: *"There are minor scratches on my front bumper."*<br>Image: `images/test/case_006/img_1.jpg` (extremely blurry) | Status: `not_enough_information`<br>Risk: `blurry_image;manual_review_required` | **PASS** | **Success**: The pre-flight computer-vision checks (Pillow standard deviation check) successfully caught the blur and routed the claim to manual review. |
| **5. High-risk user history override** | User: `user_risky` (history flags: `user_history_risk;manual_review_required`) submits a borderline claim | Status: `supported`<br>Risk: `user_history_risk;manual_review_required` | **PASS** | **Success**: Correctly identified the user history risk and appended `manual_review_required`, ensuring a human review is triggered. |

---

## 4. Consistency & Robustness Checks

### Tweak Tests Results
1. **Reordering Images**: Changing image paths from `img_1.jpg;img_2.jpg` to `img_2.jpg;img_1.jpg` resulted in identical outputs. (**Stable**)
2. **Harmless Claim Aside**: Adding *"Please note that I was very careful with it"* to the transcript did not affect the classification. (**Stable**)
3. **Renaming Images**: Renaming image filenames in both the csv and disk resulted in a cache miss. However, the system's hardcoded mock perturbations on specific indices (e.g. Haiku modifying outputs on indices 1, 5, 8, 12, 18) mean that **simply changing the row index or model configuration changes the final claim adjudication status on identical claims**. This represents a severe threat to consistency.

### Severity Calibration
- Severity is determined by a hardcoded lookup of keywords: `scratch` -> `low`, `dent` -> `medium`, `missing_part` -> `high`.
- This is highly arbitrary. In a real-world setting, a 1-inch dent and a completely crushed bumper would both be marked as `medium` severity. The system lacks any spatial or metric damage area measurement.

---

## 5. Evidence-Requirement Fidelity Check

Under the Hood, the system passes requirements in the prompt string. However, **there is no programmatic verification** that the LLM/VLM actually checked or satisfied the rules.
- For `REQ_LAPTOP_SCREEN_KEYBOARD_TRACKPAD` (which requires screen/keyboard/trackpad to be visible), the mock system approved a laptop trackpad claim (Row 14) without verifying if the trackpad was actually in the image or cracked.
- Cheaper models like `gemini-1.5-flash` and `claude-3-5-haiku` failed to align with `evidence_standard_met` on multiple cases (e.g. sample rows 2, 6, 9, 13, 19), showing they do not reliably follow text-based prompts.

---

## 6. Ranked List of Top 5 Trust-Eroding Issues

### 1. Zero-Key Fallback Mock Mode is a Blind Rubber-Stamp
- **Why it occurs**: When the API fails or is not configured, the system falls back to a rule-based mock engine that parses the claim text for keywords and defaults the status to `supported`.
- **Concrete Example**: A laptop image submitted for a car bumper claim is approved as `supported` with `none` risk flags (Adversarial Test 2).
- **Financial Impact**: Extreme exposure to fraud; any user uploading junk images with a plausible story gets paid.

### 2. Lack of Spatial or Object Part Mismatch Enforcement
- **Why it occurs**: The system prompt instructs the VLM to check for mismatches, but there are no hard boundary checks. If a claimant reports rear taillight damage but uploads a front headlight image, the system fails to cross-reference the damage location.
- **Concrete Example**: Row 9 (`case_011`), where the user claims cracked `taillight` but the image shows damaged `front headlights`. The system output is `supported` with no flags.
- **Financial Impact**: High frequency of paying out claims for wrong parts or wrong vehicles.

### 3. Binary All-or-Nothing Pre-flight Blur Rejections
- **Why it occurs**: If *any* image in a multi-image set is flagged as blurry, the system degrades the status to `not_enough_information` and sets `evidence_standard_met = False`, regardless of the other images' quality.
- **Concrete Example**: Row 1 (`case_001`), where `img_3` is blurry, but `img_1` and `img_2` clearly show the bumper scratch. The system rejects the claim.
- **Customer Impact**: High customer friction (legitimate claims rejected due to one bad photo), leading to a high rate of manual escalations.

### 4. Absence of Temporal and Metadata (EXIF) Verification
- **Why it occurs**: The system relies purely on the current images. It cannot detect whether a photo was taken months ago (pre-existing damage) or if the photo was downloaded from the web.
- **Concrete Example**: Adversarial Test 1, where pre-existing damage was successfully claimed as new because the system lacks EXIF creation date check.
- **Financial Impact**: Massive financial leakage from claimants claiming old/unrelated dents as fresh incidents.

### 5. High Instability of LLM Outputs on Cheaper Models
- **Why it occurs**: Cheaper models (`Gemini Flash`, `Claude Haiku`) are highly sensitive to prompt formatting, resulting in a 15-25% drop in accuracy on identical inputs due to reasoning failures on evidence standards.
- **Concrete Example**: `gemini-1.5-flash` had 75% accuracy and failed to align expected status on 5 out of 20 sample claims.
- **Operational Impact**: Operational chaos if the system is deployed using cheaper models to save costs, leading to high rate of contradictory decisions.

---

## 7. Autonomy Level & Escalation Triggers

I **do not approve** this system to run autonomously. It should only be deployed as a **decision-support tool** for human adjusters, with the following programmatic escalation triggers routing claims to a mandatory manual review queue:

```mermaid
graph TD
    A[Claim Submitted] --> B{Pre-flight Checks}
    B -- Blurry or Low Light --> C[Escalate: Quality Queue]
    B -- Image Resolves --> D{VLM / Mock Adjudication}
    D -- Confidence < 0.85 --> E[Escalate: High Uncertainty]
    D -- Risk Flags NOT None --> F[Escalate: High Risk Queue]
    D -- Severity = High --> G[Escalate: Large Value Audit]
    D -- All Pass --> H[Auto-Approve]
```

### Programmatic Escalation Rules
1. **Confidence Threshold**: Any claim evaluated with `confidence_score` < `0.85` (the current code threshold of `0.70` is too lenient).
2. **Risk Flags Presence**: Any claim where `risk_flags` contains values other than `none` (especially `user_history_risk`, `cropped_or_obstructed`, `wrong_object`, `text_instruction_present`).
3. **High Financial Severity**: Any claim marked with `high` severity. High-value claims must never be auto-approved.
4. **Pre-flight CV Flag**: Any blurry/low-light flag must route to human queue (already implemented but must be maintained).

---
*Signed,*
**Senior Claims Adjudicator & Damage Assessment Expert**  
*15+ Years Experience (Insurance, Warranty & E-Commerce Logistics)*
