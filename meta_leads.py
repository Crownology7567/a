"""
Meta Ads Lead Generation Script
================================
Uses the Meta Marketing API (facebook-business SDK) to:
  1. Create a Lead Generation campaign
  2. Create an Ad Set with audience targeting
  3. Create a Lead Form (Instant Form) with custom questions
  4. Create an Ad Creative
  5. Launch the Ad
  6. Fetch and export collected leads to a CSV

Requirements:
  pip install -r requirements.txt

Setup:
  Copy .env.example to .env and fill in your credentials.
"""

import os
import csv
import json
import time
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
from facebook_business.exceptions import FacebookRequestError

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration  (pulled from .env)
# ---------------------------------------------------------------------------
ACCESS_TOKEN  = os.environ["META_ACCESS_TOKEN"]   # User or System User token
APP_ID        = os.environ["META_APP_ID"]
APP_SECRET    = os.environ["META_APP_SECRET"]
AD_ACCOUNT_ID = os.environ["META_AD_ACCOUNT_ID"]  # format: act_XXXXXXXXX
PAGE_ID       = os.environ["META_PAGE_ID"]         # Facebook Page linked to ad account

# ---------------------------------------------------------------------------
# Initialise API
# ---------------------------------------------------------------------------

def init_api() -> None:
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    print("[OK] Meta API initialised")


# ---------------------------------------------------------------------------
# 1. Campaign
# ---------------------------------------------------------------------------

def create_campaign(name: str, daily_budget_cents: int = 1000) -> str:
    """
    Create a LEAD_GENERATION campaign.
    daily_budget_cents: budget in account currency cents (1000 = $10.00 USD)
    Returns campaign ID.
    """
    account = AdAccount(AD_ACCOUNT_ID)
    params = {
        Campaign.Field.name: name,
        Campaign.Field.objective: Campaign.Objective.lead_generation,
        Campaign.Field.status: Campaign.Status.paused,   # start paused – review before going live
        Campaign.Field.special_ad_categories: [],
    }
    campaign = account.create_campaign(params=params)
    campaign_id = campaign["id"]
    print(f"[OK] Campaign created: {campaign_id}")
    return campaign_id


# ---------------------------------------------------------------------------
# 2. Ad Set
# ---------------------------------------------------------------------------

def create_ad_set(
    campaign_id: str,
    name: str,
    daily_budget_cents: int,
    targeting: dict,
    start_time: str | None = None,
    end_time:   str | None = None,
) -> str:
    """
    Create an Ad Set under the given campaign.
    targeting: dict following Meta targeting spec (see docs/targeting_example).
    Returns ad set ID.
    """
    account = AdAccount(AD_ACCOUNT_ID)
    params = {
        AdSet.Field.name: name,
        AdSet.Field.campaign_id: campaign_id,
        AdSet.Field.optimization_goal: AdSet.OptimizationGoal.lead_generation,
        AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
        AdSet.Field.daily_budget: daily_budget_cents,
        AdSet.Field.targeting: targeting,
        AdSet.Field.status: AdSet.Status.paused,
    }
    if start_time:
        params[AdSet.Field.start_time] = start_time
    if end_time:
        params[AdSet.Field.end_time] = end_time

    ad_set = account.create_ad_set(params=params)
    ad_set_id = ad_set["id"]
    print(f"[OK] Ad Set created: {ad_set_id}")
    return ad_set_id


# ---------------------------------------------------------------------------
# 3. Lead Form (Instant Form)
# ---------------------------------------------------------------------------

def create_lead_form(
    name: str,
    headline: str,
    description: str,
    privacy_policy_url: str,
    questions: list[dict] | None = None,
) -> str:
    """
    Create a Meta Instant Form (lead form) on your Page.

    questions: list of question dicts.  Omit to use the defaults below.
      Each dict: {"type": "FULL_NAME"} or {"type": "CUSTOM", "label": "Your question?"}

    Predefined types: FULL_NAME, EMAIL, PHONE, COMPANY_NAME, JOB_TITLE,
                      WORK_EMAIL, STREET_ADDRESS, CITY, STATE, COUNTRY,
                      ZIP, DATE_TIME, GENDER, MARITAL_STATUS, CUSTOM.

    Returns form ID.
    """
    if questions is None:
        questions = [
            {"type": "FULL_NAME"},
            {"type": "EMAIL"},
            {"type": "PHONE"},
            {
                "type": "CUSTOM",
                "label": "What product/service are you interested in?",
                "key": "interest",
            },
        ]

    page = Page(PAGE_ID)
    params = {
        LeadgenForm.Field.name: name,
        LeadgenForm.Field.questions: questions,
        LeadgenForm.Field.privacy_policy: {"url": privacy_policy_url},
        LeadgenForm.Field.context_card: {
            "title": headline,
            "content": [description],
            "button_text": "Get Started",
        },
        LeadgenForm.Field.thank_you_page: {
            "title": "Thank you!",
            "body": "We will be in touch shortly.",
        },
        LeadgenForm.Field.locale: "en_US",
    }
    form = page.create_leadgen_form(params=params)
    form_id = form["id"]
    print(f"[OK] Lead form created: {form_id}")
    return form_id


# ---------------------------------------------------------------------------
# 4. Ad Creative
# ---------------------------------------------------------------------------

def create_ad_creative(
    name: str,
    form_id: str,
    image_hash: str,
    ad_title: str,
    ad_body: str,
    call_to_action: str = "SIGN_UP",
) -> str:
    """
    Create an Ad Creative that links to the lead form.
    image_hash: upload an image to the ad account first and use the returned hash.
    Returns creative ID.
    """
    account = AdAccount(AD_ACCOUNT_ID)
    link_data = {
        "message": ad_body,
        "name": ad_title,
        "call_to_action": {
            "type": call_to_action,
            "value": {"lead_gen_form_id": form_id},
        },
        "image_hash": image_hash,
    }
    params = {
        AdCreative.Field.name: name,
        AdCreative.Field.object_story_spec: {
            "page_id": PAGE_ID,
            "link_data": link_data,
        },
    }
    creative = account.create_ad_creative(params=params)
    creative_id = creative["id"]
    print(f"[OK] Ad Creative created: {creative_id}")
    return creative_id


# ---------------------------------------------------------------------------
# 5. Ad
# ---------------------------------------------------------------------------

def create_ad(
    name: str,
    ad_set_id: str,
    creative_id: str,
) -> str:
    """Create an Ad linking ad set and creative. Returns ad ID."""
    account = AdAccount(AD_ACCOUNT_ID)
    params = {
        Ad.Field.name: name,
        Ad.Field.adset_id: ad_set_id,
        Ad.Field.creative: {"creative_id": creative_id},
        Ad.Field.status: Ad.Status.paused,
    }
    ad = account.create_ad(params=params)
    ad_id = ad["id"]
    print(f"[OK] Ad created: {ad_id}")
    return ad_id


# ---------------------------------------------------------------------------
# 6. Upload image helper
# ---------------------------------------------------------------------------

def upload_image(image_path: str) -> str:
    """
    Upload a local image to the ad account and return its hash.
    The hash is required when creating an Ad Creative.
    """
    account = AdAccount(AD_ACCOUNT_ID)
    with open(image_path, "rb") as fh:
        image = account.create_ad_image(
            params={"filename": fh},
        )
    image_hash = list(image["images"].values())[0]["hash"]
    print(f"[OK] Image uploaded, hash: {image_hash}")
    return image_hash


# ---------------------------------------------------------------------------
# 7. Fetch leads
# ---------------------------------------------------------------------------

def fetch_leads(form_id: str, output_csv: str = "leads.csv") -> list[dict]:
    """
    Download all leads collected by a Lead Form and save them to a CSV.
    Returns list of lead dicts.
    """
    form = LeadgenForm(form_id)
    leads_cursor = form.get_leads(
        fields=[
            "id",
            "created_time",
            "field_data",
        ]
    )

    all_leads: list[dict] = []
    for lead in leads_cursor:
        row: dict = {
            "lead_id":      lead["id"],
            "created_time": lead["created_time"],
        }
        for field in lead.get("field_data", []):
            row[field["name"]] = ", ".join(field.get("values", []))
        all_leads.append(row)

    if not all_leads:
        print("[INFO] No leads found yet.")
        return all_leads

    # Write CSV
    fieldnames = list(all_leads[0].keys())
    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_leads)

    print(f"[OK] {len(all_leads)} lead(s) exported to {output_csv}")
    return all_leads


# ---------------------------------------------------------------------------
# 8. Activate (unpause) helpers
# ---------------------------------------------------------------------------

def activate_campaign(campaign_id: str) -> None:
    campaign = Campaign(campaign_id)
    campaign.api_update(params={Campaign.Field.status: Campaign.Status.active})
    print(f"[OK] Campaign {campaign_id} set to ACTIVE")


def activate_ad_set(ad_set_id: str) -> None:
    ad_set = AdSet(ad_set_id)
    ad_set.api_update(params={AdSet.Field.status: AdSet.Status.active})
    print(f"[OK] Ad Set {ad_set_id} set to ACTIVE")


def activate_ad(ad_id: str) -> None:
    ad = Ad(ad_id)
    ad.api_update(params={Ad.Field.status: Ad.Status.active})
    print(f"[OK] Ad {ad_id} set to ACTIVE")


# ---------------------------------------------------------------------------
# Main – end-to-end example
# ---------------------------------------------------------------------------

def main() -> None:
    init_api()

    # ---- Targeting spec example ----
    # Adjust age, location, interests to match your audience.
    targeting = {
        "age_min": 25,
        "age_max": 55,
        "geo_locations": {
            "countries": ["US"],
        },
        "interests": [
            {"id": "6003107902433", "name": "Real estate"},  # example interest ID
        ],
        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed", "right_hand_column"],
        "instagram_positions": ["stream"],
    }

    # 1. Campaign
    campaign_id = create_campaign(
        name="Lead Gen Campaign - " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        daily_budget_cents=2000,   # $20/day
    )

    # 2. Ad Set
    ad_set_id = create_ad_set(
        campaign_id=campaign_id,
        name="Lead Gen Ad Set - US 25-55",
        daily_budget_cents=2000,
        targeting=targeting,
    )

    # 3. Lead Form
    form_id = create_lead_form(
        name="Lead Form - " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        headline="Interested? Get in touch!",
        description="Fill out the form below and one of our team will contact you shortly.",
        privacy_policy_url="https://yourwebsite.com/privacy",   # <-- update this
    )

    # 4. Upload image & create creative
    #    Replace 'ad_image.jpg' with your actual image path (1200x628 px recommended).
    image_hash = upload_image("ad_image.jpg")

    creative_id = create_ad_creative(
        name="Lead Creative",
        form_id=form_id,
        image_hash=image_hash,
        ad_title="Ready to get started?",
        ad_body="We help you achieve [your goal]. Contact us today — it only takes 30 seconds.",
        call_to_action="LEARN_MORE",
    )

    # 5. Ad
    ad_id = create_ad(
        name="Lead Ad",
        ad_set_id=ad_set_id,
        creative_id=creative_id,
    )

    # ---- Summary ----
    summary = {
        "campaign_id":  campaign_id,
        "ad_set_id":    ad_set_id,
        "form_id":      form_id,
        "creative_id":  creative_id,
        "ad_id":        ad_id,
    }
    print("\n=== Setup Complete (all objects PAUSED) ===")
    print(json.dumps(summary, indent=2))
    print("\nReview your campaign in Meta Ads Manager before activating.")
    print("To activate, call activate_campaign(), activate_ad_set(), activate_ad()")
    print("To fetch leads later, call: fetch_leads(form_id)")


if __name__ == "__main__":
    main()
