# Idea Engine

This file converts Riley Walz's public project patterns into reusable, non-impersonating ideation machinery. It is for generating Riley-inspired project concepts, not predicting Riley Walz's future work or speaking as him.

## Base Loop

```text
seed observation -> public data residue -> one surprising inference -> minimal interface -> public hook -> methodology -> safety review -> launch/archive decision
```

## Source Categories

### Personal Need Sources

Use when the idea starts from a repeated personal behavior, annoyance, or curiosity.

Evidence anchors:

- `Routeshuffle`: route generation for personal running training.
- `Bop Spotter`: fixed-location Shazam curiosity.
- Parking projects: friends' and city residents' friction with parking tickets.

Questions:

- What repeated personal behavior touches a public system?
- What do friends complain about repeatedly?
- What personal habit produces a trace?
- What would be useful even if no one else used it?

### Platform Quirk Sources

Use when a platform emits predictable artifacts.

Patterns:

- Sequential IDs.
- Default names.
- Public profile metadata.
- Review objects.
- Availability counters.
- Reservation inventory.
- Public playlists.
- Map listings.
- Verification dependencies.

Questions:

- What field looks accidental but stable?
- What default behavior creates an archive?
- What does the platform expose for ordinary users?
- What hidden state can be inferred without private access?
- What breaks if this becomes legible?

### Civic And Urban Sources

Use when the public environment contains operational data.

Patterns:

- Citations.
- Transit feeds.
- Reservation systems.
- Public cameras.
- Public maps.
- Library inventory.
- Street audio.
- Municipal meetings.

Questions:

- What city system has a public portal?
- What operational behavior is visible only one record at a time?
- What live public system would be interesting as a map or feed?
- What data is technically public but practically invisible?

### Nostalgia And Digital Archaeology Sources

Use when old digital artifacts have emotional residue.

Patterns:

- Default filenames.
- Low-view public videos.
- Old social platform conventions.
- Unedited uploads.
- Forgotten web pages.
- Public archives that are hard to browse.

Questions:

- What old platform behavior accidentally captured a time period?
- What ordinary artifact now feels emotionally strange?
- What corpus is public but buried by modern search and feeds?
- What would feel like a time machine if shuffled?

### Social Stunt Sources

Use only with strict safety review.

Patterns:

- Fake listings.
- Coordinated mass actions.
- Platform policy probes.
- Real-world event transformations.

Questions:

- What platform or institution depends on a brittle social assumption?
- Can the probe be harmless, reversible, and legal?
- Can it avoid impersonation, fraud, service disruption, and harassment?
- Can it be documented without encouraging harmful replication?

## Idea Heuristics

### Enumerable Portal

Trigger:

- A public portal shows records by ID.
- IDs appear sequential or predictable.
- Records are created shortly after real-world events.

Interface:

- Map, feed, or timeline.

Safer adaptation:

- Delay the feed.
- Aggregate geographically.
- Remove officer/person identifiers.
- Publish trends, not real-time traces.

Reject if:

- It enables stalking or real-time interference with workers.
- It requires authentication bypass.
- It creates a direct evasion tool.

### Inventory Inference

Trigger:

- A booking system exposes remaining inventory.
- Capacity is known or inferable.
- Changes over time reveal occupancy or demand.

Interface:

- Map, line chart, route table, live status board.

Safer adaptation:

- Label as inferred.
- Add uncertainty bands.
- Avoid sensitive routes/events.
- Cache and rate-limit.

### Ambient Culture Sensor

Trigger:

- A public place emits an ambient signal.
- Commodity recognition tools can classify it.
- The output is metadata, not raw personal content.

Interface:

- Live feed, playlist, dashboard, archive.

Safer adaptation:

- Publish only derived metadata.
- Do not store raw audio/video.
- Blur or aggregate visual data.
- Avoid exact hardware location if it creates vandalism risk, but disclose the general method.

Reject if:

- It captures private conversations or identifiable images.
- It violates local recording laws.

### Accidental Archive

Trigger:

- A default field or naming convention creates a large public corpus.
- The corpus has emotional, historical, or cultural texture.

Interface:

- Shuffle player, archive viewer, TV/radio metaphor, randomizer.

Safer adaptation:

- Provide takedown path.
- Avoid surfacing vulnerable individuals.
- Avoid ranking people.

### Familiar UI Reframe

Trigger:

- Public records are hard to read in their original format.
- A familiar interface would make them legible.

Interface:

- Inbox, chat log, calendar, map, store, feed.

Safer adaptation:

- Preserve provenance.
- Mark public source.
- Redact victims or vulnerable parties.
- Avoid entertainment framing for sensitive records.

### Platform Policy Probe

Trigger:

- A platform has a rule, verification pipeline, or operational assumption that can be tested without private access.

Interface:

- Demonstration, public writeup, postmortem.

Safer adaptation:

- Do not impersonate real people.
- Avoid election, health, finance, or safety-critical deception.
- Coordinate disclosure where appropriate.

## Project Choice Score

Use a 1-5 score for each field.

```json
{
  "data_seam": 5,
  "one_screen_payoff": 5,
  "weekend_feasibility": 4,
  "cultural_hook": 5,
  "methodology_explainability": 4,
  "safety_viability": 3,
  "ephemerality_tolerance": 5
}
```

Interpretation:

- `data_seam` below 4 means the idea is probably generic.
- `one_screen_payoff` below 4 means the interface is too broad.
- `safety_viability` below 3 means the idea should be rejected or transformed.
- `weekend_feasibility` below 3 means it is not Riley-pattern-aligned unless it is a rare sustained product.

## Idea Generation Prompt

```text
Generate 10 Riley-inspired project ideas for [domain].

Constraints:
- Use public or consented data only.
- Do not propose real-time tracking of identifiable people.
- Do not propose non-consensual biometric or attractiveness scoring.
- Do not bypass authentication or access controls.
- Each idea must have one data seam, one interface shape, one launch hook, and one safety redesign.

For each idea, output:
1. Name.
2. One-line concept.
3. Public/consented data source.
4. Hidden quirk or residue.
5. Minimal interface.
6. Weekend prototype plan.
7. Why it is culturally interesting.
8. Safety risks.
9. Safer version.
10. Evidence analogy from Riley Walz's public projects.
```

## Process Prompt

```text
Take this idea and convert it into a Riley-inspired weekend prototype plan.

Required output:
- One-sentence project frame.
- Data source and publicness analysis.
- Feasibility probe.
- Minimal architecture.
- First-screen UX.
- Launch copy in third-person analytical style.
- Methodology page outline.
- Risk score.
- Kill-switch/fallback plan.
- Decision: ship, redesign, or reject.
```

## Anti-Generic Test

An idea fails if it can be described as:

- "An AI app for X."
- "A dashboard for Y."
- "A chatbot that helps with Z."
- "A social network for people who like..."

It passes only if it has a concrete public residue:

```text
This specific system emits this specific artifact, and showing it this specific way changes how people understand it.
```

## Safer Transformation Examples

### From Risky To Safer: Worker Tracking

Risky:

```text
Show exact live locations of individual enforcement workers.
```

Safer:

```text
Show delayed neighborhood-level enforcement density without individual identifiers.
```

### From Risky To Safer: Audio Surveillance

Risky:

```text
Record public street audio and store raw clips.
```

Safer:

```text
Store only song IDs, timestamps rounded to the hour, and source uncertainty.
```

### From Risky To Safer: Biometric Ranking

Risky:

```text
Score real people's attractiveness from public profile photos.
```

Safer:

```text
Use synthetic or consented data to demonstrate how biased social scoring systems behave, without ranking real people.
```

### From Risky To Safer: Public Records Voyeurism

Risky:

```text
Turn sensitive records into entertainment.
```

Safer:

```text
Provide a provenance-preserving research interface with redactions, victim-protection rules, and context notes.
```

## Output Standard

Every generated idea must include:

- Evidence analogy.
- Data-source note.
- Non-affiliation disclaimer.
- Risk rating.
- Safety mitigation.
- Confidence level.

Do not generate an idea that cannot include those fields.
