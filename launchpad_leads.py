"""
Launchpad Program – Meta Ads Lead Generation Script
=====================================================
Promotes a 12-week "Ideation to Launch" program via Instagram/Facebook Reels.
- Instant Form collects: Full Name, Email, Phone
- Audience: aspiring entrepreneurs & startup founders
- If no funds → investors pitch + match funding angle baked into copy

Setup:
  1. pip install -r requirements.txt
  2. cp .env.example .env  →  fill in credentials
  3. Replace placeholder values marked  ← UPDATE
  4. Run:  python launchpad_leads.py
"""

import os
import csv
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.leadgenform import LeadgenForm
from facebook_business.adobjects.page import Page

load_dotenv()

# ---------------------------------------------------------------------------
# Credentials (from .env)
# ---------------------------------------------------------------------------
ACCESS_TOKEN  = os.environ["META_ACCESS_TOKEN"]
APP_ID        = os.environ["META_APP_ID"]
APP_SECRET    = os.environ["META_APP_SECRET"]
AD_ACCOUNT_ID = os.environ["META_AD_ACCOUNT_ID"]   # e.g. act_123456789
PAGE_ID       = os.environ["META_PAGE_ID"]

# ---------------------------------------------------------------------------
# Ad copy variants – Reels format (short, punchy, hook-first)
# ---------------------------------------------------------------------------

REELS_COPY_VARIANTS = [
    {
        "label": "Funding angle",
        "ad_message": (
            "Got a business idea but no funds? \n\n"
            "We'll pitch it to investors and get you MATCH FUNDING — "
            "then take you from ideation to launch in just 12 weeks. \n\n"
            "Our Launchpad Program has helped founders turn ideas into "
            "real businesses with real backing. \n\n"
            "Spots are limited. Apply below — it's free to find out if you qualify."
        ),
        "ad_title": "From idea → funded business in 12 weeks",
        "call_to_action": "APPLY_NOW",
    },
    {
        "label": "Speed angle",
        "ad_message": (
            "12 weeks. That's all it takes to go from idea to launched business. \n\n"
            "The Launchpad Program walks you through every step — "
            "strategy, build, brand, and launch. \n\n"
            "No funds? No problem. We pitch your idea to investors "
            "and secure match funding so cost is never the reason you don't start. \n\n"
            "Apply now — free, 60-second form."
        ),
        "ad_title": "Turn your idea into a business — in 12 weeks",
        "call_to_action": "LEARN_MORE",
    },
    {
        "label": "Pain angle",
        "ad_message": (
            "Still sitting on that business idea? \n\n"
            "Most people wait for the 'right time'. "
            "The right time is the Launchpad Program. \n\n"
            "✅ 12-week guided journey: ideation → launch\n"
            "✅ Investor pitch support + match funding if you need it\n"
            "✅ Real mentorship, real accountability\n\n"
            "Drop your details below and let's get you started."
        ),
        "ad_title": "Stop waiting. Start building.",
        "call_to_action": "SIGN_UP",
    },
]

# ---------------------------------------------------------------------------
# Instant Form config
# ---------------------------------------------------------------------------

FORM_CONFIG = {
    "name": "Launchpad Program – Interest Form",
    "context_card": {
        "title": "Apply for the Launchpad Program",
        "content": [
            "Go from idea to launched business in 12 weeks.",
            "Don't have funds? We'll pitch your idea to investors and secure match funding.",
            "Fill in your details and a member of our team will be in touch.",
        ],
        "button_text": "Apply Now",
    },
    "questions": [
        {"type": "FULL_NAME"},
        {"type": "EMAIL"},
        {"type": "PHONE"},
    ],
    "privacy_policy_url": "https://yourwebsite.com/privacy",   # ← UPDATE
    "thank_you": {
        "title": "Application received!",
        "body": "Thanks for applying. One of our Launchpad coaches will be in touch within 24 hours.",
    },
}

# ---------------------------------------------------------------------------
# Targeting – aspiring entrepreneurs & startup founders
# ---------------------------------------------------------------------------

TARGETING = {
    "age_min": 22,
    "age_max": 45,
    "geo_locations": {
        "countries": ["GB"],   # ← UPDATE: e.g. ["US", "CA"] or ["GB"]
    },
    # Entrepreneur / startup interests
    "interests": [
        {"id": "6003257670735", "name": "Entrepreneurship"},
        {"id": "6003397425735", "name": "Startup company"},
        {"id": "6003195547625", "name": "Business"},
        {"id": "6003382348435", "name": "Small business"},
        {"id": "6003108194145", "name": "Self-employment"},
        {"id": "6004046736183", "name": "Venture capital"},
    ],
    # Reels placements only
    "publisher_platforms": ["facebook", "instagram"],
    "facebook_positions": ["reels"],
    "instagram_positions": ["reels"],
    "device_platforms": ["mobile"],
}

# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

DAILY_BUDGET_CENTS = 3000   # $30 / £30 per day  ← UPDATE as needed


# ===========================================================================
# API helpers
# ===========================================================================

def init_api() -> None:
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    print("[OK] Meta API initialised")


def upload_image(image_path: str) -> str:
    """Upload a local image; return its hash for use in creatives."""
    account = AdAccount(AD_ACCOUNT_ID)
    with open(image_path, "rb") as fh:
        result = account.create_ad_image(params={"filename": fh})
    image_hash = list(result["images"].values())[0]["hash"]
    print(f"[OK] Image uploaded — hash: {image_hash}")
    return image_hash


def create_campaign() -> str:
    account = AdAccount(AD_ACCOUNT_ID)
    campaign = account.create_campaign(params={
        Campaign.Field.name: f"Launchpad Program – Reels Leads {datetime.now(timezone.utc):%Y-%m-%d}",
        Campaign.Field.objective: Campaign.Objective.lead_generation,
        Campaign.Field.status: Campaign.Status.paused,
        Campaign.Field.special_ad_categories: [],
    })
    cid = campaign["id"]
    print(f"[OK] Campaign: {cid}")
    return cid


def create_ad_set(campaign_id: str) -> str:
    account = AdAccount(AD_ACCOUNT_ID)
    ad_set = account.create_ad_set(params={
        AdSet.Field.name: "Launchpad – Entrepreneurs 22-45 – Reels",
        AdSet.Field.campaign_id: campaign_id,
        AdSet.Field.optimization_goal: AdSet.OptimizationGoal.lead_generation,
        AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
        AdSet.Field.daily_budget: DAILY_BUDGET_CENTS,
        AdSet.Field.targeting: TARGETING,
        AdSet.Field.status: AdSet.Status.paused,
    })
    sid = ad_set["id"]
    print(f"[OK] Ad Set: {sid}")
    return sid


def create_lead_form() -> str:
    page = Page(PAGE_ID)
    cfg = FORM_CONFIG
    form = page.create_leadgen_form(params={
        LeadgenForm.Field.name: cfg["name"],
        LeadgenForm.Field.questions: cfg["questions"],
        LeadgenForm.Field.privacy_policy: {"url": cfg["privacy_policy_url"]},
        LeadgenForm.Field.context_card: cfg["context_card"],
        LeadgenForm.Field.thank_you_page: cfg["thank_you"],
        LeadgenForm.Field.locale: "en_US",
    })
    fid = form["id"]
    print(f"[OK] Lead Form: {fid}")
    return fid


def create_creative(ad_set_id: str, form_id: str, copy: dict, image_hash: str) -> str:
    account = AdAccount(AD_ACCOUNT_ID)
    creative = account.create_ad_creative(params={
        AdCreative.Field.name: f"Launchpad Creative – {copy['label']}",
        AdCreative.Field.object_story_spec: {
            "page_id": PAGE_ID,
            "link_data": {
                "message": copy["ad_message"],
                "name": copy["ad_title"],
                "call_to_action": {
                    "type": copy["call_to_action"],
                    "value": {"lead_gen_form_id": form_id},
                },
                "image_hash": image_hash,
            },
        },
    })
    crid = creative["id"]
    print(f"[OK] Creative ({copy['label']}): {crid}")
    return crid


def create_ad(ad_set_id: str, creative_id: str, label: str) -> str:
    account = AdAccount(AD_ACCOUNT_ID)
    ad = account.create_ad(params={
        Ad.Field.name: f"Launchpad Ad – {label}",
        Ad.Field.adset_id: ad_set_id,
        Ad.Field.creative: {"creative_id": creative_id},
        Ad.Field.status: Ad.Status.paused,
    })
    aid = ad["id"]
    print(f"[OK] Ad ({label}): {aid}")
    return aid


# ---------------------------------------------------------------------------
# Activate helpers
# ---------------------------------------------------------------------------

def go_live(campaign_id: str, ad_set_id: str, ad_ids: list[str]) -> None:
    """Set campaign, ad set, and all ads to ACTIVE."""
    Campaign(campaign_id).api_update(params={Campaign.Field.status: Campaign.Status.active})
    AdSet(ad_set_id).api_update(params={AdSet.Field.status: AdSet.Status.active})
    for aid in ad_ids:
        Ad(aid).api_update(params={Ad.Field.status: Ad.Status.active})
    print("[OK] Campaign, Ad Set, and Ads are now ACTIVE")


# ---------------------------------------------------------------------------
# Fetch & export leads
# ---------------------------------------------------------------------------

def fetch_leads(form_id: str, output_csv: str = "launchpad_leads.csv") -> list[dict]:
    """Download all leads from the Instant Form and save to CSV."""
    form = LeadgenForm(form_id)
    cursor = form.get_leads(fields=["id", "created_time", "field_data"])

    rows: list[dict] = []
    for lead in cursor:
        row = {"lead_id": lead["id"], "created_time": lead["created_time"]}
        for field in lead.get("field_data", []):
            row[field["name"]] = ", ".join(field.get("values", []))
        rows.append(row)

    if not rows:
        print("[INFO] No leads collected yet.")
        return rows

    fieldnames = list(rows[0].keys())
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] {len(rows)} lead(s) saved to {output_csv}")
    return rows


# ===========================================================================
# Main – full setup
# ===========================================================================

def main() -> None:
    init_api()

    # -- Image --
    # Provide a 9:16 vertical image (1080x1920 px) for Reels.
    # For a quick test, a 1200x628 image also works.
    image_hash = upload_image("launchpad_reel.jpg")   # ← UPDATE: path to your image

    # -- Campaign & Ad Set --
    campaign_id = create_campaign()
    ad_set_id   = create_ad_set(campaign_id)

    # -- Single shared Lead Form --
    form_id = create_lead_form()

    # -- One ad per copy variant (A/B test all three) --
    ad_ids = []
    for copy in REELS_COPY_VARIANTS:
        creative_id = create_creative(ad_set_id, form_id, copy, image_hash)
        ad_id       = create_ad(ad_set_id, creative_id, copy["label"])
        ad_ids.append(ad_id)

    # -- Summary --
    summary = {
        "campaign_id": campaign_id,
        "ad_set_id":   ad_set_id,
        "form_id":     form_id,
        "ad_ids":      ad_ids,
    }
    print("\n=== LAUNCHPAD CAMPAIGN READY (all PAUSED) ===")
    print(json.dumps(summary, indent=2))
    print(
        "\nNext steps:\n"
        "  1. Review ads in Meta Ads Manager\n"
        "  2. Call go_live(campaign_id, ad_set_id, ad_ids) to activate\n"
        "  3. Collect leads:  fetch_leads(form_id)\n"
        "  4. Update PRIVACY_POLICY_URL, GEO, and DAILY_BUDGET_CENTS at top of file"
    )


if __name__ == "__main__":
    main()
