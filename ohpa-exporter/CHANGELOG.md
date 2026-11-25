# Changelog

## 0.1.1

- Persist local sensor mappings; consent is never persisted.
- Research eligibility check and actual ZIP preview with coverage and sample rows.
- Download exactly the previewed bytes using a short-lived one-use token.
- Require jointly observed mandatory series for non-VFM profiles; no comfort data without consent.

## 0.1.0

- Experimental standalone ingress app, sensor suggestions and seven research export profiles.
- Local ZIP with pseudonymous installation ID, relative time, measurement schema and coverage.
- VFM uses existing reference filter; other profiles retain event-aligned intervals.
- Manual email attachment only; no remote upload.
