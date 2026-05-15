# Technical Playbook

This file summarizes public technical patterns from Riley Walz's visible projects and repositories. It is not an instruction to scrape irresponsibly or bypass access controls. Treat all data collection as subject to legal, platform, and safety review.

## Technical Thesis

The public engineering pattern is pragmatic:

```text
small Node.js service + public data collector + simple store + map/feed/archive UI + method note
```

The goal is usually a fast public artifact, not a generalized platform.

## Runtime Defaults

Observed defaults:

- JavaScript.
- Node.js.
- Express for small web services.
- Pug or direct static assets for simple server-rendered pages.
- Plain client-side JavaScript without heavy bundlers in older public repos.
- Socket.io for simple real-time interactions where needed.
- Environment variables for configuration and secrets.

Model implication:

```text
Use boring web primitives unless the data seam requires something heavier.
```

## Data Collection Patterns

### Public HTTP Collection

Common shape:

```text
fetch public endpoint -> parse JSON/XML/HTML -> normalize record -> write to store -> expose simple UI
```

Libraries and patterns seen in public code research:

- `node-fetch` for HTTP.
- `request` in older projects.
- `xml2js` for XML parsing.
- `himalaya` for HTML parsing.
- Browser-like headers when interacting with public web endpoints.
- Concurrency controls with `p-limit` and `async-limiter`.
- Delays between batches.

Safety requirements for new work:

- Respect `robots.txt`, terms, and API limits.
- Use rate limiting and backoff.
- Cache aggressively.
- Avoid authenticated or protected endpoints unless explicitly authorized.
- Avoid providing exact scraping recipes for sensitive sources.

### Inventory Inference

Used when a reservation or availability system exposes enough public state to estimate occupancy or change.

Recommended safer design:

- Label counts as inferred.
- Add uncertainty ranges.
- Show source limitations.
- Avoid individual-level exposure.
- Prefer cached snapshots over aggressive polling.

### Public Record Reframing

Used when records are already public but hard to navigate.

Recommended safer design:

- Preserve provenance.
- Link source documents.
- Redact vulnerable parties when needed.
- Add context around sensitive material.
- Avoid entertainment framing for serious records.

### Ambient Sensor Systems

Used when a physical location emits a public signal and commodity recognition tools classify it.

Required mitigations:

- Store derived metadata only where possible.
- Do not publish raw audio or video.
- Avoid capturing conversations or identifiable frames.
- Review local laws.
- Include a takedown/contact path.

## Data Storage Defaults

Observed public patterns:

- MySQL with `mysql2/promise` for structured scraping projects.
- Local JSON storage for lightweight bot/user state.
- In-memory objects for ephemeral games or short-lived state.

Recommended model:

```text
Prototype: JSON file or SQLite.
Live feed: small relational store.
Ephemeral state: memory is acceptable only if loss is harmless.
Sensitive data: minimize, redact, aggregate, or do not store.
```

## Mapping Defaults

Mapping projects use:

- OpenStreetMap.
- Protomaps.
- Minimal overlays.
- Timestamps or last-seen markers.

Safer mapping rules:

- Coarsen locations when individuals are involved.
- Delay updates.
- Avoid exact traces.
- Provide uncertainty and source freshness.
- Remove identifiers where possible.

## Hardware Defaults

`Bop Spotter` illustrates a low-cost hardware pattern:

- Old Android phone.
- Microphone.
- Solar panel.
- Plastic/weatherproof box.
- Public Wi-Fi.
- Periodic uploads.
- Commodity recognition service.

Model principle:

```text
Cheap hardware is acceptable when the concept is the point and the output is safe derived metadata.
```

## Deployment Defaults

Observed and inferred deployment habits:

- Simple PaaS-style hosting.
- Glitch and Heroku/Railway-like conventions.
- CapRover or VPS-style self-hosting.
- `Procfile` or `captain-definition` in some repos.
- Manual deployment more common than formal CI.

Recommended for this context system:

- Keep demos cheap and easy to kill.
- Use environment variables.
- Add health checks for live collectors.
- Keep a static fallback page.
- Keep a snapshot/export before launch.
- Document how to disable collectors.

## Architecture Templates

### One-Page Data Artifact

```text
collector.js
store.sqlite
server.js
public/
views/
about.md
```

Use for:

- Feeds.
- Simple maps.
- Archives.
- CSV-backed tables.

### Live Feed

```text
collector cron -> queue/table -> public feed -> about/method page -> kill switch
```

Required:

- Rate limit.
- Freshness timestamp.
- Backoff on errors.
- Source-down state.
- Manual disable flag.

### Archive Viewer

```text
offline crawl -> curated index -> random/shuffle UI -> takedown path -> source note
```

Required:

- Content filtering.
- Takedown mechanism.
- No vulnerable-person highlighting.
- Provenance notes.

### Familiar UI Clone

```text
public records -> normalized entities -> familiar navigation shell -> source citations -> redaction rules
```

Required:

- Avoid implying unauthorized access.
- State that records are public.
- Keep document provenance visible.
- Avoid impersonating account ownership.

## Engineering Trade-Offs

### Speed Over Robustness

The public pattern often favors a working prototype over formal tests or extensive scaling.

Agent adaptation:

- Preserve speed.
- Add minimum safety checks.
- Do not add unnecessary architecture.
- Do add a kill switch for risky public demos.

### Simplicity Over Scalability

Single-process apps and in-memory state are acceptable only when the state is disposable.

Agent adaptation:

- If state loss matters, use SQLite/Postgres/Redis.
- If a project may go viral, add caching and rate limiting.
- If the data source is fragile, create snapshot mode.

### Cost Over Reliability

Low-cost hardware and hosting are part of the pattern.

Agent adaptation:

- Keep cost low.
- Make downtime acceptable.
- Publish freshness and uncertainty.
- Avoid claiming institutional-grade reliability.

## Risk-Aware Build Checklist

Before building:

- Is the data public or consented?
- Is the method legal and allowed by terms?
- Does the data include people?
- Could it identify or track someone?
- Could it enable harassment, evasion, or social scoring?
- Can you aggregate or delay the data?
- Can you disclose the method safely?
- Is there a kill switch?
- Is there a source-down fallback?
- Is there a non-affiliation disclaimer?

Before launch:

- Add method page.
- Add source freshness timestamp.
- Add uncertainty caveat.
- Add contact/takedown path.
- Add no-affiliation statement.
- Test shutdown.
- Preserve an archive if allowed.

## Default Stack Recommendation

For safe Riley-inspired prototypes:

```text
Node.js
Express
SQLite or Postgres
node-fetch or undici
p-limit
plain HTML/CSS/JS or server-rendered templates
OpenStreetMap/Protomaps for maps
static fallback page
```

Use React/Next only when:

- The interface complexity justifies it.
- There are many interactive states.
- The repo already uses it.
- The user explicitly wants a product-grade app.

## Refusal Boundaries

Do not provide implementation details for:

- Authentication bypass.
- Anti-bot evasion.
- Credential harvesting.
- Real-time tracking of identifiable people.
- Doxxing workflows.
- Non-consensual biometric classification.
- Service disruption or coordinated denial-of-service.

Safe alternative:

```text
I can help design a public-data visualization that uses delayed, aggregated, non-identifying data with clear provenance and a kill switch.
```
