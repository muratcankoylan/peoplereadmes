# Advanced Technical Intelligence

This file captures Riley Walz's public technical ability patterns at a deeper level than a stack summary. It is designed to help agents and builders understand the craft behind the projects: how public data seams are found, converted into thin systems, and framed as useful or culturally legible artifacts.

Boundary:

```text
This is public-source technical pattern analysis. It is not Riley Walz, not affiliated with him, and not a guide to bypass access controls, evade anti-bot systems, harvest private data, or replicate harmful behavior.
```

## Core Technical Thesis

The above-average ability is not "scraping" by itself. Many engineers can write scrapers.

The actual technical edge is a compound skill:

```text
public-client observation + data seam detection + state-change inference + cheap collector design + one-screen productization + public method framing
```

He repeatedly turns an ordinary public interface into a new instrument:

- A city payment portal becomes a near-real-time civic map.
- A public catalog becomes a checkout feed.
- A booking interface becomes occupancy inference.
- A music recognition app becomes an ambient culture sensor.
- A default filename pattern becomes a digital archaeology engine.
- Public records become searchable through a familiar UI.
- A payphone registry becomes a physical game.

Most builders stop after "I found an endpoint." The Riley pattern is to ask:

```text
What system behavior does this endpoint expose, and what interface would make that behavior instantly visible?
```

## Technical Ability Stack

### 1. Public-Client Reconnaissance

This is the habit of treating a normal public website or app as a map of its own backend.

Safe version:

- Use the public interface as intended.
- Observe public network requests.
- Inspect response shapes, timestamps, pagination, and visible fields.
- Prefer official APIs, CSV exports, and public records when they exist.
- Stop at access-control boundaries.

What to notice:

- Fetch/XHR requests returning JSON.
- Pagination cursors.
- Embedded configuration.
- Public IDs and slugs.
- Response fields not shown in the UI.
- Vendor domains behind official clients.
- Freshness metadata such as timestamps, ETags, or last-modified headers.

What not to do:

- Do not bypass login walls.
- Do not replay private tokens.
- Do not enumerate identifiers at scale.
- Do not falsify identity to evade controls.
- Do not degrade the service.

The useful mental model:

```text
The browser is not just rendering a page. It is showing the contract between a public client and a data source.
```

### 2. Data Seam Detection

A data seam is a public interface behavior that exposes a deeper pattern than intended.

Common seam types:

- Predictable or low-entropy identifiers.
- Default filenames or default metadata.
- Public availability counters.
- Reservation inventory.
- Public profile metadata.
- Public records hidden in poor interfaces.
- Map listings and review objects.
- Public sensor or camera feeds.
- Live status or freshness endpoints.

The skill is not only seeing the seam. It is rating whether the seam is:

- Technically accessible.
- Legally usable.
- Ethically publishable.
- Culturally interesting.
- Stable enough for a prototype.
- Safe enough after aggregation/redaction.

### 3. State-Change Inference

Several projects work by observing a public value over time and interpreting a delta.

Pattern:

```text
public state at time T1 -> public state at time T2 -> difference -> inferred event
```

Examples:

- `Library Spy`: available copy count decreases, so infer a checkout.
- `Amtrak Right Now`: available seats compared to capacity, so infer occupancy.
- `Panama Playlists`: public listening/profile state changes, so infer media activity over time.
- `Weather Watching`: observed clothing categories over time, so infer perceived street-level weather.

Uncertainty rules:

- Deltas can have multiple causes.
- The observed signal is a proxy, not ground truth.
- False positives and false negatives must be documented.
- The UI must label the data as inferred.
- Sensitive deltas should be aggregated or delayed.

### 4. Hardware Client Wrapping

`Bop Spotter` shows a distinctive pattern: when the desired capability lives inside a consumer app or physical environment, wrap the public client in cheap hardware rather than building the hard model from scratch.

Pattern:

```text
cheap sensor -> commodity app/model -> derived metadata -> public feed
```

Publicly described components include:

- Old Android phone.
- Microphone.
- Solar panel.
- Protective box.
- Public Wi-Fi.
- Periodic audio upload/recognition workflow.
- Public song metadata feed and CSV export.

The deeper skill:

- Do not rebuild Shazam.
- Do not over-engineer custom hardware.
- Use commodity recognition as a black box.
- Extract only the derived metadata needed for the artifact.
- Build around physical-world failure: power, Wi-Fi, weather, theft, drift, reboot.

Safer adaptation:

- Store song metadata, not raw audio.
- Publish coarse timestamps if needed.
- Avoid exact hardware location when it creates tampering risk, while still disclosing method.
- Provide contact/takedown path.
- Review recording laws.

### 5. Creative Archival Mining

`IMG_0001` is not a normal search project. The important move is using default metadata as a time machine.

Pattern:

```text
old default naming convention -> massive public platform search -> low-view/old/short filters -> random archive UI
```

Technical signals:

- Default camera filename families.
- Platform upload era.
- Low view-count filter.
- Short duration filter.
- Randomized playback.
- Store metadata/index, not necessarily media files.

The deeper ability:

- Recognize that default metadata encodes human behavior.
- Use metadata to isolate an era or culture.
- Apply filters that preserve the emotional signal.
- Build a browsing interface that feels like discovery, not search.

Safety caveat:

Even public low-view videos can feel private when resurfaced. A safe adaptation needs takedown paths, content filtering, and careful avoidance of vulnerable content.

### 6. Vendor Backend Patterning

Several projects appear to rely on discovering vendor backends powering public sites:

- Library catalog vendor APIs.
- Transit web/mobile APIs.
- Reservation inventory systems.
- Public mapping and geospatial services.
- Public document release systems.

Safe analysis rule:

```text
Describe the backend category, response role, and inference pattern. Do not publish sensitive endpoint recipes or headers for replicating harmful collection.
```

What matters technically:

- He identifies structured data behind the public UI.
- He prefers direct structured responses over browser automation.
- He uses small Node scripts rather than heavy crawler frameworks.
- He adds batching, concurrency limits, and delays in longer-running collectors.
- He stores enough state to detect future changes.

### 7. Polite Persistence

The `nypl-scrape` style work shows more craft than "hit endpoint in loop."

Observed patterns:

- Batch sizes.
- Concurrency limits.
- Explicit delays.
- Idempotent upserts.
- Separate metadata and event tables.
- Environment variables for credentials/config.
- XML/JSON parsing by format-specific libraries.

This indicates a practical rule:

```text
For public data projects, the data collector is part of the social contract. It must avoid needless load and survive repeated runs.
```

### 8. Thin Productization

The projects become public because the output is shaped aggressively:

- Map for spatial systems.
- Feed for live events.
- Archive/shuffle for digital archaeology.
- Familiar UI clone for public records.
- Dashboard for aggregate inference.
- Game/leaderboard for physical scavenger hunts.

The technical ability is not just "collect data." It is "choose the interface that collapses the data into one visible claim."

## Project Technical Case Studies

### Find My Parking Cops

Technical pattern:

- Public payment/citation system.
- Predictable public identifiers.
- Efficient polling of likely new records.
- Geocoding or mapping of citation locations.
- Public map plus officer/location list.
- Static snapshot after source shutdown.

What is above-average:

- Seeing that citation IDs encode system tempo.
- Inferring that devices likely claim IDs in batches.
- Reducing the project to a single public question: where was the last ticket written?
- Shipping fast enough that the institutional reaction became part of the project.

Safety lesson:

This pattern is high-risk when it exposes worker location or enables interference. A safer version must delay, aggregate, remove identifiers, or treat the finding as a responsible disclosure instead of a public tool.

### Bop Spotter

Technical pattern:

- Physical sensor in public space.
- Commodity phone and microphone.
- Solar power and public Wi-Fi.
- Periodic upload or recognition loop.
- Music recognition service.
- Time-series metadata store.
- Public feed and CSV export.

What is above-average:

- Treating a consumer app as a sensor component.
- Making the deployment cheap enough to be a one-person experiment.
- Adding a public data artifact rather than only a gimmick.
- Framing the system honestly as "culture surveillance."

Safety lesson:

The safe transferable version publishes derived metadata only, avoids raw audio retention, and treats consent, location, and local recording law as first-class design constraints.

### IMG_0001

Technical pattern:

- Public YouTube search.
- Default camera filename query families.
- Low-view, short-duration, historical filters.
- Metadata index.
- Randomized viewer.

What is above-average:

- Recognizing a naming convention as an archival index.
- Expanding from one filename pattern into a broader class of device-default metadata.
- Using filters to preserve the emotional signal: low-view, raw, old, short, unedited.
- Building a tiny interface that turns search results into a time capsule.

Safety lesson:

Accidentally public does not mean ethically frictionless. Add takedown and avoid amplifying sensitive subjects.

### Library Spy

Technical pattern:

- Public catalog.
- Vendor-backed structured responses.
- Availability count polling.
- Inventory delta inference.
- MySQL persistence.
- Metadata enrichment.
- Live event feed.

What is above-average:

- Turning "available copies" into an event stream.
- Using conservative polling machinery.
- Separating book metadata from inferred checkout events.
- Exposing uncertainty through the project concept.

Safety lesson:

Reading habits are sensitive even when individual borrowers are not named. Safer versions aggregate, delay, and avoid branch-level targeting where it exposes a small community.

### Amtrak Right Now

Technical pattern:

- Public reservation inventory.
- Capacity versus availability inference.
- Train/route database.
- Map overlay.
- Protomaps/OpenStreetMap basemap.
- Caveats about undercounting.

What is above-average:

- Seeing inventory as a proxy for occupancy.
- Turning a booking workflow into a live operational view.
- Pairing inferred data with explicit limitations.

Safety lesson:

Transportation inference must be clearly labeled as estimate, rate-limited, and designed to avoid operational misuse.

### Weather Watching

Technical pattern:

- Public camera feed.
- Person detection.
- Best-frame selection.
- Multimodal model classification.
- Aggregated clothing/weather proxy.
- Dashboard output.

What is above-average:

- Combining edge vision, frame selection, and LLM interpretation into a lightweight inference pipeline.
- Asking a narrow proxy question instead of building a general vision system.
- Aggregating outputs into a simple public signal.

Safety lesson:

This is privacy-sensitive. Safer versions should avoid retaining identifiable frames, publish aggregates only, and include strict redaction and retention policies.

### Payphone Go

Technical pattern:

- Official public records request.
- Payphone location database.
- Map interface.
- Telephony verification through caller origin.
- Player IDs.
- Leaderboard and voicemail artifact.

What is above-average:

- Using the official "front door" for data acquisition.
- Bridging public records with physical-world verification.
- Turning infrastructure archaeology into a game.

Safety lesson:

Physical games need location safety, trespass warnings, stale-data handling, and moderation.

### Jmail

Technical pattern:

- Public document corpus.
- Parsing/OCR/normalization.
- Message/thread reconstruction.
- Search index.
- Familiar Gmail-like UI.

What is above-average:

- Recognizing that the interface, not the documents, is the bottleneck.
- Making a large public corpus browsable through a familiar mental model.
- Using UI mimicry as compression.

Safety lesson:

Sensitive records need provenance, redaction preservation, victim-protection rules, and sober framing. Do not gamify unredaction or turn sensitive material into entertainment.

## The "Can I Do This Too?" Answer

Yes, many individual technical steps are learnable:

- Inspecting public requests.
- Querying official APIs.
- Writing Node collectors.
- Storing rows in MySQL.
- Building maps and feeds.
- Using commodity AI APIs.

The rarer combination is:

1. Choosing a data source with cultural charge.
2. Finding the one inference that makes it legible.
3. Shipping before the idea dies.
4. Explaining the method plainly.
5. Making the first screenshot self-explanatory.
6. Accepting fragility without hiding it.
7. Turning public reaction into feedback.

The "second brain" should therefore model his technical instincts as decision functions, not as secret exploits.

## Technical Decision Functions

### Data Source Fit

```text
If the source is public/consented, structured or semi-structured, fresh enough to matter, and tied to a concrete cultural system, continue.
Otherwise, reject or seek a better source.
```

### Endpoint Discovery Fit

```text
If the public client already receives the data, observe and document the data contract.
If the source offers official export/API, prefer that.
If the idea requires bypassing a barrier, stop.
```

### Inference Fit

```text
If a state change maps plausibly to a real-world event, label it as inferred and document alternate explanations.
If false positives could harm people, aggregate or do not publish.
```

### Prototype Fit

```text
If one collector, one store, and one interface can prove the idea, build thin.
If the design needs a platform, accounts, or complex moderation before proving the idea, reduce scope.
```

### Public Launch Fit

```text
If the first screen explains the artifact and the method page explains the caveats, launch may be viable.
If publication would enable targeting, harassment, evasion, or social scoring, redesign or refuse.
```

## Source-Hunting Model

To go beyond obvious search results, use this source order:

1. First-party project pages and "how it works" sections.
2. Archived versions of project pages.
3. Public GitHub repositories and package manifests.
4. Public code comments, README files, deployment artifacts, and commit metadata.
5. Public CSV/data exports on project pages.
6. Public press quotes with direct technical details.
7. Hacker News/forum discussions where the creator or technical readers add details.
8. Official API documentation for services implicated by the projects.
9. Open-data portals and public records request references.
10. Secondary summaries only after cross-checking with the above.

For every source, capture:

```json
{
  "url": "source URL",
  "source_type": "first_party | archive | code | forum | press | official_docs",
  "claim": "technical claim supported",
  "evidence_strength": "high | medium | low",
  "reuse_constraints": "license or terms notes",
  "safety_notes": "risk if operationalized"
}
```

## Operator Model For Agents

When asked to "think technically like Riley," do this:

1. Name the data seam.
2. Name the public interface that exposes it.
3. Identify the state, metadata, or inventory signal.
4. Explain the inference in one sentence.
5. Choose the smallest collector.
6. Choose the smallest store.
7. Choose the interface shape.
8. Add methodology and provenance.
9. Add uncertainty.
10. Add safety redesign.
11. Decide: ship, archive, disclose, or reject.

## What To Avoid

Do not model him as:

- A generic full-stack engineer.
- A "scraper guy."
- A security researcher looking for exploits.
- A growth hacker.
- A product founder optimizing conversion.

The useful model is:

```text
public systems reader + data seam detector + thin prototype engineer + cultural interface designer
```

## Required Safety Gate

Any generated technical plan must include:

- Publicness analysis.
- Terms/legal review flag.
- PII/sensitive-data review.
- Load/rate plan.
- Source-down fallback.
- Uncertainty model.
- Kill switch.
- Non-affiliation disclaimer.

If the plan cannot satisfy those gates, return a safer analytical variant.
