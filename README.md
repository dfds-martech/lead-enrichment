# Lead Enrichment API

A FastAPI service for B2B lead enrichment with company research and Orbis matching capabilities.

## Quick Start with Docker

```bash
# Build image
docker compose build

# Run container
docker compose up

# Access API
open http://localhost:8080/docs
```

## Local Development

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --group dev

# Run locally
uv run dev

# Format and lint code
ruff check .    # Check issues
ruff format .   # Format code

# Run tests (not any yet)
pytest
```

## API Endpoints

### Health Check

- `GET /health` - Service health status

### Company Matching (upcoming)

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
