# Example Riley-Inspired Project Brief

## Disclaimer

This is a Riley-inspired professional pattern analysis based on public sources. It is not affiliated with, endorsed by, or representative of Riley Walz.

## Name

Playground Right Now

## One-Liner

A delayed public map estimating which playgrounds are likely busy, inferred from parks reservations, nearby public events, weather, and time of day.

## Data Source

- City parks reservation portal.
- Public events calendar.
- Weather API.
- OpenStreetMap playground boundaries.

No cameras, microphones, device IDs, Wi-Fi tracking, or individual-level location data.

## Why It Is Interesting

Cities already publish signals that imply public-space demand, but those signals are scattered. This turns them into a simple civic utility without tracking people.

## Interface Shape

- Map of playgrounds.
- Three labels: quiet, normal, busy.
- "Why this estimate?" drawer.
- Timestamp and stale-data indicator.
- Methodology page.

## Thin Technical Plan

1. Pull parks reservations hourly.
2. Pull public event listings hourly.
3. Pull weather every 30 minutes.
4. Join signals near playground boundaries.
5. Publish static JSON.
6. Render a simple map.
7. Archive daily snapshots.

## Launch Hook

```text
Cities publish lots of signals about when parks get busy, but none of them are easy to read together. This turns public reservations, events, and weather into a rough playground crowd forecast.
```

## Safety Controls

- No individual tracking.
- No exact crowd counts.
- No camera or audio.
- Coarse labels only.
- Public source links.
- Non-affiliation disclaimer.
- Graceful degradation if a source breaks.
