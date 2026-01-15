# Lead Enrichment API

A FastAPI service for B2B lead enrichment with company research and Orbis matching capabilities.

## Local Development

```bash
# Install dependencies / dev-dependencies / all
uv sync
uv sync --group dev
uv sync --all-groups

# Run locally
uv run dev

# Format and lint code
uv run ruff check .    # Check issues
uv run ruff format .   # Format code

# Run tests
uv run pytest
```

## Docker (not necessary for local dev)

```bash
# Build image
docker compose build

# Run container
docker compose up

# Access API
open http://localhost:8080/docs
```

## API Endpoints

Run local server and vist
http://localhost:8080/docs

# Google Cloud

Project name (staging) "data-enrichment-staging"
https://console.cloud.google.com/home/dashboard?hl=en&project=data-enrichment-staging

# Google Cloud Run

Currently deplyed:
https://console.cloud.google.com/run/detail/europe-west1/lead-enrichment-staging

# Google Search JSON API

Companies are reserached via Google Search JSON API. The API is validated and can be used in production as is (tied to the martech google-cloud project)

Search Engine:
https://programmablesearchengine.google.com/controlpanel/overview

# Serper API - Google Search

Companies are researched via the Serper API. Maybe we should deprecated this, and switch entirely to Google Search JSON API.

Serper API is currently running on a trial key with limited credits

TODO: We need to test what gives the best result

# DFDS Capabilities

The project uses Azure OpenAi resources. They are regsitered through the "b2b-lead-qualification" capability

https://build.dfds.cloud/capabilities/b2b-lead-qualification-cstff

TODO: We need a production deployment of OpenAi models that will be able to run in a Goolge Cloud Run environment

# Sales Enablement documentation

Expected payload on Service Bus events

https://dfds.sharepoint.com/sites/CRMSystemMigrationProject/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FCRMSystemMigrationProject%2FShared%20Documents%2FFeatures%2FLeads%2FLead%20attribution%2FLead%20Event%20Payloads&viewid=2ef87e2a%2D4310%2D4dd2%2D9441%2Df52350745426&ga=1

List of desired features / generator system

https://dfds.sharepoint.com/:x:/s/CRMSystemMigrationProject/IQBN_5QGjkcATZMUN8rMfKRgAQViYUisM_T3HXPEgKSHKmE

# CRM cargo categories

https://dfdscrmdev.crm4.dynamics.com/api/data/v9.2/dfds_equipmenttypes?$select=dfds_descriptionlmm,dfds_equipmenttypecode,dfds_equipmenttypeid,dfds_name&$expand=dfds_EquipmentGroup($select=dfds_descriptionlmm,dfds_name)&$filter=(dfds_leadenrichmentenabled+eq+true)+and+(dfds_EquipmentGroup/dfds_equipmentgroupid+ne+null)

https://dfdscrmdev.crm4.dynamics.com/api/data/v9.2/dfds_equipmentgroups?$select=dfds_description,dfds_descriptionlmm,dfds_equipmentgroupcode,dfds_equipmentgroupid,dfds_name&$filter=(dfds_leadenrichmentenabled+eq+true)
