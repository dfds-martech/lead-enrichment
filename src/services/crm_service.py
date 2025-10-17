"""
Simple Service for interacting with the CRM test data.
"""

import json
from pathlib import Path

import pandas as pd

root_dir = Path.cwd().parent


class CRMService:
    def __init__(self):
        self._leads = None

    @property
    def leads(self):
        if self._leads is None:
            crm_leads_full_csv_file = root_dir / "data" / "crm_leads_full.csv"
            self._leads = pd.read_csv(crm_leads_full_csv_file)

        return self._leads

    def get_record(self, index):
        return self.leads.iloc[index]

    def get_form(self, index):
        form = self.get_record(index)["dfds_fullpayload"]
        return json.loads(form)

    def get_lead(self, index):
        form = self.get_form(index)
        record = self.get_record(index)

        transport = {
            "collection_city": record.get("dfds_collectioncity", None),
            "collection_country": "TODO",
            "delivery_city": record.get("dfds_deliverrycity", None),
            "delivery_country": "TODO",
        }

        userSegmentID = form.get("userSegmentID", {})
        identifiers = {
            "email": form.get("CompanyEmail", None) or form.get("PersonalEmail", None),
            "user_id": userSegmentID.get("UserId", None),
            "anonymous_id": userSegmentID.get("anonymousUserId", None),
        }

        user = {
            "first_name": form.get("FirstName", "").strip(),
            "last_name": form.get("LastName", "").strip(),
        }
        user["full_name"] = f"{user['first_name']} {user['last_name']}".strip()

        company = {
            "name": form.get("CompanyName"),
            "city": record.get("address1_city") or record.get("address1_composite"),
            "contry": "TODO",
            "phone_number": form.get(""),
        }

        merged = form | transport
        return {
            "identifiers": identifiers,
            "user": user,
            "company": company,
        } | dict(sorted(merged.items()))
