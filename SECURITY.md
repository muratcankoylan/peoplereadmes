# Security Policy

This repo ships structured persona context systems for public professional pattern analysis. The threat model is narrow but specific: every persona package is meant to study patterns from public evidence without becoming a tool for impersonation, surveillance, or harassment.

## In scope

Report any of the following:

- A persona package that leaks private information (location, contact, relationships, internal company work, unpublished material).
- A persona package or prompt that enables first-person impersonation or implies endorsement by the subject.
- A heuristic, prompt, or example that supports doxxing, harassment, real-time tracking of individuals, biometric or social scoring, credential misuse, anti-bot evasion, or access-control bypass.
- A schema, evidence map, or quote bank that misrepresents source provenance, fabricates citations, or hides uncertainty.
- A research file containing data scraped from sources that require consent or contradict the linked terms of service.

## Out of scope

- Disagreements about interpretation that fall within the evidence-bound analysis (open a regular issue).
- Subjective characterization of press coverage where the underlying citation is correct.
- Dependency vulnerabilities in tooling not used by this repository.

## Reporting

Open a private security advisory:

https://github.com/muratcankoylan/peoplereadmes/security/advisories/new

Include:

- The persona package and file paths involved.
- A short description of the concern and the safety category it violates.
- A suggested mitigation if you have one (redaction, removal, additional caveat, schema fix).

Do not file a public issue for sensitive concerns.

## Response

- Acknowledged within 7 days.
- Triage and mitigation timeline depends on severity.
- Persona packages or files that violate the safety boundaries may be redacted, rewritten, or removed without prior notice when the harm is active.

## Related

- Project-level safety design: `README.md` ("What This Is Not", "License And Ethics").
- Per-persona safety boundaries: `personas/<id>/context/safety-boundaries.md`.
- Schema constraints: `schemas/persona.schema.json`.
