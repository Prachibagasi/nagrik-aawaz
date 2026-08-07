"""
complaint_agent.py
==================
AI Agent that:
  1. Parses a complaint draft text file (COMP-XXXXXXXX-XXXX.txt) using Groq
  2. Enriches it with location data from a CSV file
  3. Automatically fills and submits the complaint form on the department website

Dependencies:
    pip install groq playwright pandas python-dotenv
    playwright install chromium
"""

import os
import re
import json
import time
import argparse
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY not set. Add it to your .env file.")

client = Groq(api_key=GROQ_API_KEY)

# ── Groq model ────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama3-70b-8192"   # fast + capable; change to mixtral-8x7b if preferred

# ── Department config ─────────────────────────────────────────────────────────
# Map department codes / keywords → website URL
DEPARTMENT_URL_MAP = {
    "PWD":  "http://localhost:5500/index.html",   # Replace with real URLs
    "UJS":  "http://localhost:5500/index_jal.html",
    "DEFAULT": "http://localhost:5500/index.html",
}

# ── Zone / District normaliser ────────────────────────────────────────────────
VALID_ZONES = [
    "Dehradun", "Haridwar", "Nainital", "Almora", "Pauri Garhwal",
    "Tehri Garhwal", "Uttarkashi", "Chamoli", "Rudraprayag",
    "Pithoragarh", "Bageshwar", "Champawat", "US Nagar",
]

def normalise_zone(raw: str) -> str:
    """Fuzzy-match raw district/zone to a valid dropdown value."""
    raw_lower = raw.lower()
    for z in VALID_ZONES:
        if z.lower() in raw_lower or raw_lower in z.lower():
            return z
    return "Dehradun"   # fallback

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Parse complaint text with Groq
# ─────────────────────────────────────────────────────────────────────────────

PARSE_PROMPT = """
You are an expert complaint processing assistant for Indian government departments.

Extract the following fields from the complaint letter below and return ONLY valid JSON.
Do NOT add any explanation or markdown fences.

Required JSON keys:
{{
  "complaint_id":    "string – complaint ID starting with COMP-",
  "complainant_name": "string – name of the person who filed; use 'The Complainant' if not given",
  "mobile":          "string – 10-digit mobile number if present, else empty string",
  "account_no":      "string – consumer/account number if present, else empty string",
  "department":      "string – department code e.g. PWD, UJS, etc.",
  "district":        "string – district/zone mentioned",
  "complaint_type":  "string – one of: Water Supply Disruption | Pipe Leakage / Burst | Billing Dispute | Water Quality Issue | New Water Connection | Low Water Pressure | Meter Issue | Sewage / Drainage Problem | Road Pothole | Encroachment on Road | Other Request",
  "description":     "string – concise English description of the problem (max 300 chars)",
  "priority":        "string – Low / Medium / High"
}}

Complaint letter:
---
{letter}
---
"""

def parse_complaint(text: str) -> dict:
    """Use Groq LLM to extract structured fields from the complaint draft."""
    prompt = PARSE_PROMPT.format(letter=text.strip())

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=512,
    )

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Groq returned non-JSON output:\n{raw}") from e

    return data


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Enrich with location data from CSV
# ─────────────────────────────────────────────────────────────────────────────

def load_locations(csv_path: str) -> pd.DataFrame:
    """
    Load location CSV.
    Expected columns (case-insensitive):
        complaint_id, address, district, ward, pincode   (at minimum complaint_id + address)
    """
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower()
    return df


def enrich_with_location(parsed: dict, df: pd.DataFrame) -> dict:
    """Merge location data from CSV into the parsed complaint dict."""
    cid = parsed.get("complaint_id", "").strip()
    match = df[df["complaint_id"].astype(str).str.strip() == cid]

    if match.empty:
        print(f"  [WARN] No location row found for {cid}. Proceeding with draft data.")
        return parsed

    row = match.iloc[0].to_dict()

    # Prefer CSV district over LLM-extracted if available
    if "district" in row and pd.notna(row["district"]) and row["district"]:
        parsed["district"] = str(row["district"])

    # Build a richer description appending address
    address_parts = []
    for col in ["address", "ward", "pincode"]:
        if col in row and pd.notna(row[col]) and row[col]:
            address_parts.append(str(row[col]))

    if address_parts:
        location_str = ", ".join(address_parts)
        parsed["description"] = (parsed.get("description", "") +
                                  f" [Location: {location_str}]")[:500]
    return parsed


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Resolve website URL
# ─────────────────────────────────────────────────────────────────────────────

def resolve_url(parsed: dict) -> str:
    dept = parsed.get("department", "DEFAULT").upper()
    for key, url in DEPARTMENT_URL_MAP.items():
        if key in dept:
            return url
    return DEPARTMENT_URL_MAP["DEFAULT"]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Playwright automation
# ─────────────────────────────────────────────────────────────────────────────

def fill_and_submit(parsed: dict, url: str, headless: bool = False, dry_run: bool = False):
    """
    Open the website, navigate to the complaints dashboard, fill the form,
    and submit it. Returns the complaint confirmation ID shown on screen.
    """
    zone = normalise_zone(parsed.get("district", "Dehradun"))

    # Map parsed complaint_type to dropdown option
    complaint_type_raw = parsed.get("complaint_type", "Other Request")
    valid_types = [
        "Water Supply Disruption", "Pipe Leakage / Burst", "Billing Dispute",
        "Water Quality Issue", "New Water Connection", "Low Water Pressure",
        "Meter Issue", "Sewage / Drainage Problem", "Other Request",
        # PWD-specific (add more as needed)
        "Road Pothole", "Encroachment on Road",
    ]
    complaint_type = complaint_type_raw if complaint_type_raw in valid_types else "Other Request"

    print(f"\n  → Zone      : {zone}")
    print(f"  → Type      : {complaint_type}")
    print(f"  → Desc      : {parsed['description'][:80]}...")
    print(f"  → URL       : {url}")

    if dry_run:
        print("\n  [DRY RUN] Skipping browser automation.")
        return "DRY-RUN-NO-SUBMISSION"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=400)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        # ── Open dashboard ─────────────────────────────────────────────────
        try:
            # Try clicking the nav item first
            page.click("#complaintsNav span", timeout=5_000)
        except PWTimeoutError:
            # Fallback: look for any "Complaint Registration" link
            page.click("text=Complaint Registration", timeout=5_000)

        # Wait for the overlay
        page.wait_for_selector("#dashboardOverlay.show", timeout=8_000)
        print("  [OK] Dashboard opened")

        # ── Make sure "File a Complaint" tab is active ─────────────────────
        page.click("button:has-text('File a Complaint')")
        page.wait_for_selector("#tab-file", timeout=4_000)

        # ── Fill form fields ───────────────────────────────────────────────
        account_no = parsed.get("account_no") or "N/A"
        page.fill("#fc_accountNo", account_no)

        page.fill("#fc_name", parsed.get("complainant_name", "The Complainant"))

        mobile = parsed.get("mobile", "")
        if not re.fullmatch(r"\d{10}", mobile):
            mobile = "9999999999"   # placeholder if not available
        page.fill("#fc_mobile", mobile)

        # Zone dropdown
        page.select_option("#fc_zone", label=zone)

        # Complaint type dropdown — select closest available option
        try:
            page.select_option("#fc_type", label=complaint_type)
        except Exception:
            page.select_option("#fc_type", label="Other Request")

        page.fill("#fc_desc", parsed.get("description", "No description provided."))
        print("  [OK] Form filled")

        # ── Submit ─────────────────────────────────────────────────────────
        page.click("button:has-text('Submit Complaint')")

        # Wait for success message
        try:
            page.wait_for_selector("#fc_msg.fc-msg-success", timeout=6_000)
            success_text = page.inner_text("#fc_msg")
            print(f"  [OK] Submitted → {success_text}")
        except PWTimeoutError:
            # Check for error message
            try:
                err_text = page.inner_text("#fc_msg")
                print(f"  [WARN] Form response: {err_text}")
            except Exception:
                print("  [WARN] No confirmation message detected.")

        time.sleep(2)   # brief pause so you can see the result
        screenshot_path = f"screenshot_{parsed['complaint_id']}.png"
        page.screenshot(path=screenshot_path)
        print(f"  [OK] Screenshot saved → {screenshot_path}")

        browser.close()
        return success_text if 'success_text' in dir() else "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def process_complaint(complaint_file: str, csv_file: str,
                       headless: bool = False, dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"  Processing: {complaint_file}")
    print(f"{'='*60}")

    # 1. Read complaint text
    text = Path(complaint_file).read_text(encoding="utf-8")
    print(f"  [1/4] Read complaint file ({len(text)} chars)")

    # 2. Parse with Groq
    parsed = parse_complaint(text)
    print(f"  [2/4] Groq parsed complaint:")
    for k, v in parsed.items():
        print(f"         {k}: {v}")

    # 3. Enrich with CSV location
    if csv_file and Path(csv_file).exists():
        df = load_locations(csv_file)
        parsed = enrich_with_location(parsed, df)
        print(f"  [3/4] Location data merged from CSV")
    else:
        print(f"  [3/4] CSV not found / not provided, skipping enrichment")

    # 4. Automate submission
    url = resolve_url(parsed)
    print(f"  [4/4] Starting browser automation...")
    result = fill_and_submit(parsed, url, headless=headless, dry_run=dry_run)

    print(f"\n  ✅ Done. Result: {result}\n")
    return parsed, result


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Agent — Auto-fill government complaint forms"
    )
    parser.add_argument(
        "complaint_files",
        nargs="+",
        help="One or more complaint .txt files (COMP-XXXXXXXX-XXXX.txt)"
    )
    parser.add_argument(
        "--csv",
        default="locations.csv",
        help="Path to locations CSV (default: locations.csv)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no GUI)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse & enrich only, do not open browser"
    )

    args = parser.parse_args()

    results = []
    for f in args.complaint_files:
        parsed, outcome = process_complaint(
            complaint_file=f,
            csv_file=args.csv,
            headless=args.headless,
            dry_run=args.dry_run,
        )
        results.append({"file": f, "id": parsed.get("complaint_id"), "outcome": outcome})

    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    for r in results:
        print(f"  {r['id']}  →  {r['outcome']}")