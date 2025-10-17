"""
Simple Service for interacting with the CRM test data.
"""

import json
from pathlib import Path

import pandas as pd

from models.lead import Lead

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
        record = self.leads.iloc[index].to_dict()
        return {k: (None if pd.isna(v) else v) for k, v in record.items()}

    def get_form(self, index):
        form = self.get_record(index)["dfds_fullpayload"]
        return json.loads(form)

    def get_lead(self, index) -> Lead:
        """Get a Lead object from the CRM."""
        record = self.get_record(index)
        return Lead.from_crm(record)
