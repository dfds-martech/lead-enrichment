# Lead Enrichment API

A FastAPI service for B2B lead enrichment with company research and Orbis matching capabilities.

### Local Development

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --group dev

## Format and lint code
ruff check . # Check for issues
ruff format . # Format code

## Run tests
pytest

# Run locally
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### Deploy to Google Cloud Run

```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# Deploy
./deploy.sh $PROJECT_ID lead-enrichment
```

## API Endpoints

### Health Check

- `GET /health` - Service health status

### Company Matching

- `POST /api/v1/company/match` - Match companies using Orbis API

**Example Request:**

```json
{
  "name": "WILDWINE LTD",
  "city": "London",
  "country": "UK",
  "score_limit": 0.7
}
```

**Example Response:**

```json
{
  "success": true,
  "total_hits": 2,
  "matches": [
    {
      "bvd_id": "GB12262808",
      "name": "WILDWINE LTD",
      "matched_name": "WILDWINE LTD",
      "city": "LONDON",
      "country": "GB",
      "score": 1.0,
      "hint": "Potential",
      "status": "Active"
    }
  ]
}
```
