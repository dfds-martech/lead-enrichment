"""
Simple Service for interacting with the CRM test data.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from models.lead import Lead

# root_dir = Path.cwd().parent
root_dir = Path(__file__).resolve().parents[2]


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
        transform_record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        return dict(sorted(transform_record.items()))

    def get_form(self, index):
        form = self.get_record(index)["dfds_fullpayload"]
        return json.loads(form)

    def get_lead(self, index) -> Lead:
        """Get a Lead object from the CRM."""
        record = self.get_record(index)
        return Lead.from_crm(record)

    # For mocking incoming lead events
    def mock_lead_event(self, index):
        """Get a lead event structure directly from the raw CRM record without creating a Lead object."""
        record = self.get_record(index)
        payload = self.get_form(index)

        # Parse country fields using the same helper as Lead.from_crm()
        from models.lead import LeadCountry

        collection_country = LeadCountry.from_crm_field(record.get("dfds_collectioncountry"))
        delivery_country = LeadCountry.from_crm_field(record.get("dfds_deliverycountry"))
        country_lookup = LeadCountry.from_crm_field(record.get("dfds_countrylookup"))

        # Extract user segment ID info
        user_segment_id = payload.get("userSegmentID", {})
        cdp_id = user_segment_id.get("UserId") or user_segment_id.get("anonymousUserId")

        # Get phone number - prefer mobilephone, fallback to telephone1 or payload
        phone = record.get("mobilephone") or record.get("telephone1") or payload.get("PhoneNumber")

        # Get email - prefer record emailaddress1, fallback to payload
        email = record.get("emailaddress1") or payload.get("CompanyEmail")

        # Get first/last name - prefer record, fallback to payload
        first_name = record.get("firstname") or payload.get("FirstName")
        last_name = record.get("lastname") or payload.get("LastName")

        return {
            "eventId": "some-azure-service-bus-event-id",
            "eventType": "lead.updated",
            "eventVersion": "1.0",
            "eventTimestamp": record.get("modifiedon") or record.get("createdon") or datetime.now().isoformat(),
            "sourceSystem": "d365-sales",
            "entityType": "Lead",
            "data": {
                "contact": {
                    "crmId": record.get("_contactid_value"),
                    "cdpId": cdp_id,
                    "dfdsId": None,
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "jobTitle": record.get("jobtitle"),
                    "jobFunction": record.get("dfds_jobfunction"),
                    "phone": phone,
                },
                "company": {
                    "crmAccountId": record.get("_accountid_value"),
                    "orbisId": record.get("dfds_orbisid"),
                    "name": record.get("companyname") or payload.get("CompanyName"),
                    "segment": record.get("dfds_accountsegment"),
                    "type": record.get("dfds_accounttype"),
                    "address": {
                        "line1": record.get("address1_line1"),
                        "line2": record.get("address1_line2"),
                        "city": record.get("address1_city") or record.get("address1_composite"),
                        "postalCode": record.get("address1_postalcode"),
                        "state": record.get("address1_stateorprovince"),
                        "country": country_lookup.name if country_lookup else None,
                        "country_code": country_lookup.alpha2 if country_lookup else None,
                    },
                },
                "campaign": {
                    "utmsource": "",
                    "utmcampaign": "",
                    "utmmedium": "",
                    "sourceURL": "",
                    "sourceId": "3WB90GZuACZtx5w1Ip5vgx",
                    "sourceName": "Customs Clearance Quote Form",
                    "leadSource": "8",
                    "recommendation": False
                },
                "lead": {
                    "crmLeadId": record.get("leadid"),
                    "sourceId": record.get("dfds_sourceid"),
                    "requestNumber": record.get("dfds_requestnumber"),
                    "description": payload.get("DescribeYourCargo"),
                    "collectionCity": record.get("dfds_collectioncity"),
                    "collectionCountry": collection_country.name if collection_country else None,
                    "collectionCountryCode": collection_country.alpha2 if collection_country else None,
                    "deliveryCity": record.get("dfds_deliverycity"),
                    "deliveryCountry": delivery_country.name if delivery_country else None,
                    "deliveryCountryCode": delivery_country.alpha2 if delivery_country else None,
                    "quoteNotes": record.get("dfds_quotenotes"),
                    "requestType": record.get("dfds_requesttype"),
                    "sourceName": record.get("dfds_sourcename"),
                    "leadSource": record.get("dfds_leadsource"),
                    "state": record.get("state"),
                    "status": record.get("status"),
                    "subject": record.get("subject"),
                    "fullPayload": record.get("dfds_fullpayload"),
                },
            }
        }
