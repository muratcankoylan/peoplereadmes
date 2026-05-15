# Project Patterns

## 1. Public Data Seam To Map

Representative projects:

- `Find My Parking Cops`
- `Amtrak Right Now`
- `Fast Food Index`
- `Looksmapping`

Reusable pattern:

```text
public/semi-public data -> normalization -> geographic view -> caveat
```

Safer version:

- Delay sensitive data.
- Aggregate by area.
- Remove individual identifiers.
- Avoid raw exports for sensitive data.

## 2. Ambient Sensor To Feed

Representative projects:

- `Bop Spotter`
- `Weather Watching`

Reusable pattern:

```text
cheap sensor -> derived signal -> live feed -> public explanation
```

Safer version:

- Publish derived metadata only.
- Avoid raw audio or identifiable images.
- Do not infer identity or sensitive traits.

## 3. Digital Archaeology

Representative projects:

- `IMG_0001`
- `Papers`
- `Payphone Go`

Reusable pattern:

```text
old artifact pattern -> public search/crawl -> curated viewer -> nostalgia frame
```

Safer version:

- Provide takedown paths.
- Avoid spotlighting vulnerable people.
- Preserve source context.

## 4. Familiar Interface For Public Records

Representative projects:

- `Jmail`
- `Jamazon`

Reusable pattern:

```text
public records -> parse/index -> familiar UI metaphor -> search and exploration
```

Safer version:

- Preserve provenance.
- Redact vulnerable parties.
- Avoid official-looking deception.
- Include non-affiliation language.

## 5. Platform Arbitrage And Consumer Data

Representative projects:

- `Postal Arbitrage`
- `Fast Food Index`
- `Panama Playlists`
- `Lunches.fyi`

Reusable pattern:

```text
platform data -> comparison -> ranking/index -> shareable insight
```

Safer version:

- Prefer business or aggregate data.
- Avoid private account data.
- Timestamp and caveat all scraped or inferred data.

## Case Study Lessons

### Find My Parking Cops

High signal, high risk. Useful lesson: real-time operational data becomes safety-sensitive when made legible at scale.

### Bop Spotter

Strong concept with cheap hardware. Useful lesson: "culture surveillance" framing drives discussion but also forces consent questions.

### IMG_0001

Strong archival pattern. Useful lesson: metadata quirks can reveal cultural history, but resurfacing personal media requires recourse.

### Looksmapping

Use as an anti-pattern. Useful lesson: AI social scoring of real people creates privacy, bias, and dignity harms.

### Jmail

Powerful interface reframing. Useful lesson: making public records accessible increases both civic value and ethical burden.
