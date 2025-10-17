# Lead Enrichment TODO

## ✅ Completed

### Data Layer

- [x] Fixed `CRMService.get_record()` to convert pandas `nan` values to `None`
- [x] Updated `Lead.company_research_query` to handle None values properly
- [x] Renamed `CompanyResearchProfile` → `CompanyResearchResult` for consistency

### Agent Architecture

- [x] Updated `company_research.py` agent:

  - Fixed field name references (`name`, `city`, `country` vs old `company_name`, `company_location`)
  - Extracted instructions to `COMPANY_RESEARCH_INSTRUCTIONS` constant
  - Updated example JSON to match actual `CompanyResearchQuery` model
  - Agent returns single consolidated result with reasoning and sources

- [x] Created `company_match.py` agent:
  - Dual-input approach (original lead data + enriched research data)
  - Smart triangulation strategy (national_id → domain → location)
  - Cross-validation between original and enriched data
  - Confidence levels (high/medium/low/none)
  - Returns `CompanyMatchResult` with reasoning

### Tools & Services

- [x] Created `match_company.py` tool - wraps OrbisService for agent use
- [x] Extended `OrbisService` with:
  - `get_company_details(bvd_id)` - fetches financial/employee data
  - `OrbisCompanyDetails` model (employees, revenue, industry, etc.)
  - Proper handling of nested response structure (`Data` array)

## 🚧 Next Steps

### 1. Pipeline Integration (HIGH PRIORITY)

- [ ] Create `EnrichmentService` or orchestration function that runs the 3-stage pipeline:
  ```
  Lead → Research Agent → Match Agent → get_company_details() → EnrichedLead
  ```
- [ ] Define `EnrichedLead` model to hold all results:
  ```python
  class EnrichedLead(BaseModel):
      lead: Lead
      research: CompanyResearchResult
      match: CompanyMatchResult
      details: OrbisCompanyDetails | None
      enrichment_metadata: dict  # timestamps, confidence, etc.
  ```

### 2. Testing & Validation

- [ ] Test full pipeline with multiple lead samples (indices 0-10)
- [ ] Measure success rates:
  - Research completion rate
  - Match confidence distribution
  - Details retrieval success rate
- [ ] Test edge cases:
  - Lead with no domain
  - Lead with no location
  - No Orbis match found
  - Conflicting data between original and enriched
  - API failures/timeouts

### 3. Error Handling & Resilience

- [ ] Add retry logic for API failures
- [ ] Handle partial failures gracefully:
  - Research succeeds but match fails → still save research
  - Match succeeds but details fail → still save match
- [ ] Add timeout configurations
- [ ] Consider circuit breaker pattern for Orbis API

### 4. Optimization

- [ ] Implement conditional details fetch:
  - Only fetch for high/medium confidence matches
  - Or add confidence threshold parameter
- [ ] Add caching layer:
  - Cache research results by domain
  - Cache Orbis matches by BvD ID
  - Cache company details by BvD ID
- [ ] Batch processing support for multiple leads

### 5. Observability

- [ ] Add structured logging at each pipeline stage
- [ ] Track metrics:
  - API call counts (Serper, Orbis match, Orbis details)
  - Processing time per stage
  - Success/failure rates
  - Cost per lead enrichment
- [ ] Create monitoring dashboard

### 6. Data Quality

- [ ] Add validation rules:
  - Flag when original and enriched domains differ significantly
  - Flag when Orbis location differs from enriched location
  - Score overall confidence of enrichment
- [ ] Create data quality report
- [ ] Consider human-in-the-loop for low confidence matches

### 7. Production Readiness

- [ ] Create async batch processing endpoint
- [ ] Add rate limiting
- [ ] Implement webhook/callback for async results
- [ ] Add result storage (database/S3)
- [ ] Create API documentation
- [ ] Add authentication/authorization

## 💡 Architecture Decisions & Rationale

### Two-Agent Pattern (Research + Match)

**Decision:** Use separate agents for research and matching, not one monolithic agent.

**Rationale:**

- Clear separation of concerns (exploratory vs selective)
- Reusable components (can use research agent standalone)
- Better testability
- Allows business logic between stages
- More token-efficient than mega-agent

### Dual-Input Matching

**Decision:** Match agent receives both original and enriched data.

**Rationale:**

- Original domain from email is often reliable
- Enriched national_id is high-value
- Cross-validation improves accuracy
- Can detect and resolve conflicts
- Better than blind handoff

### Details After Matching

**Decision:** Fetch company details only after successful match.

**Rationale:**

- Need BvD ID from match to fetch details
- Details API likely more expensive
- Only fetch for confident matches
- Clean separation: matching vs data retrieval

### Single Research Result

**Decision:** Research agent returns one consolidated result, not multiple candidates.

**Rationale:**

- Agent's job is synthesis, not presenting alternatives
- Pushing multiple candidates downstream complicates matching
- Uncertainty expressed via null fields, not alternatives
- Simpler pipeline logic

## 🤔 Open Questions

1. **Cost optimization:** What's acceptable cost per lead enrichment?

   - Serper searches: ~$0.005 per search
   - Orbis API calls: TBD pricing
   - LLM costs: ~$0.02-0.05 per lead?

2. **Batch processing:** Process leads one-by-one or in batches?

   - Sequential: Simpler, easier error handling
   - Parallel: Faster, but more complex

3. **Result storage:** Where to store enriched leads?

   - Back to CRM?
   - Separate database?
   - File export?

4. **Update frequency:** Re-enrich existing leads?

   - One-time enrichment
   - Periodic updates (quarterly?)
   - On-demand refresh

5. **Human review:** When to flag for manual review?
   - All low-confidence matches?
   - Only when conflicting data?
   - Never (fully automated)?

## 📊 Success Metrics to Track

- **Coverage:** % of leads successfully enriched
- **Accuracy:** % of matches verified as correct (sample validation)
- **Confidence:** Distribution of match confidence levels
- **Speed:** Average time per lead enrichment
- **Cost:** Average cost per lead enrichment
- **API health:** Success rates for Serper, Orbis match, Orbis details
- **Data completeness:** % of enriched fields populated (employees, revenue, etc.)

## 🔄 Iteration Plan

### Phase 1: MVP (Current)

- Basic 3-stage pipeline working
- Manual testing with sample leads
- Logging and basic error handling

### Phase 2: Polish

- Comprehensive error handling
- Caching layer
- Batch processing
- Metrics tracking

### Phase 3: Production

- API endpoints
- Async processing
- Result storage
- Monitoring dashboard
- Documentation

### Phase 4: Optimization

- Cost optimization
- Performance tuning
- Data quality improvements
- Human-in-the-loop workflows
