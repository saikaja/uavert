# Uavert backend foundation and Toronto web demo

Build the first real Uavert backend (Neon Postgres + PostGIS/H3, Python ingestion, scoring engine, FastAPI) and a simple web map on top of it, ready to demo on Tuesday, October 6, 2026.

| Phase | Document | Status | Approved |
|---|---|---|---|
| 1. Define the work | [01-definition.md](01-definition.md) | Approved | 2026-10-01 11:59 |
| 2. Review the design | [02-design.md](02-design.md); revision [02-design.r2.md](02-design.r2.md) (downtown fix) | Approved; built and tested; r2 approved 2026-10-01 12:57; r3 [02-design.r3.md](02-design.r3.md) (foot traffic) approved 2026-10-01 13:00 | 2026-10-01 |
| 3. Start the work | [03-plan.md](03-plan.md) | Approved | 2026-10-01 12:18 |
| 4. Do the work | [04-implementation.md](04-implementation.md) | Approved (includes r2 + r3) | 2026-10-01 13:15 |
| 1–3 (addition). Time of day | [01-03-time-of-day.md](01-03-time-of-day.md) | Approved; built: [04-implementation.time-of-day.md](04-implementation.time-of-day.md) approved 2026-10-01 13:33 | 2026-10-01 13:21 |
| 5. Test the work | [05-test-report.md](05-test-report.md) | Approved | 2026-10-01 13:52 |
| 1–3 (addition). Solidify + Vercel | [01-03-solidify.md](01-03-solidify.md); built: [04-implementation.solidify.md](04-implementation.solidify.md), tested: [05-test-report.solidify.md](05-test-report.solidify.md) (both approved 2026-10-01 18:07) | Approved; built and tested | 2026-10-01 14:05 |
| 1–3 (addition). Fairer scores, crowds, heat | [01-03-calibration-crowds-heat.md](01-03-calibration-crowds-heat.md); built: [04-implementation.calibration-crowds-heat.md](04-implementation.calibration-crowds-heat.md), tested: [05-test-report.calibration-crowds-heat.md](05-test-report.calibration-crowds-heat.md) (both approved 2026-10-01 19:16) | Approved; built and tested | 2026-10-01 18:39 |
| 1–3 (addition). Odds alongside the score | [01-03-odds.md](01-03-odds.md); revision [01-03-odds.r2.md](01-03-odds.r2.md) (leave out jail incidents) | Approved; r2 approved 2026-10-07 15:44; built: [04-implementation.odds.md](04-implementation.odds.md) approved 2026-10-07 15:49; tested: [05-test-report.odds.md](05-test-report.odds.md) approved 2026-10-07 15:56; E2E rows 35-38 | 2026-10-07 15:22 |
| 1–3 (addition). Crime trendlines | [01-03-trends.md](01-03-trends.md); built: [04-implementation.trends.md](04-implementation.trends.md) approved 2026-10-08 11:53; tested: [05-test-report.trends.md](05-test-report.trends.md) approved 2026-10-08 11:58 | Approved; built and tested locally on `feature/trends`; hosted preview waiting for Vercel Preview settings | 2026-10-08 11:30 |
| 6. End-to-end testing | [06-e2e-signoff.md](06-e2e-signoff.md) | Waiting for your test results (merged to `main` 2026-10-07 at Sai's request, before testing) | |

**Next steps (start here):** [next-steps.md](next-steps.md): where to pick up and what to do next (as of 2026-10-01 19:20).

**Status snapshot:** [status-goals-and-pending.md](status-goals-and-pending.md): goals, what's done, and what's still pending (as of 2026-10-01).

**Notes:** [gta-expansion-notes.md](gta-expansion-notes.md): crime data and permissions for York, Durham, Peel and Halton (checked 2026-10-01; permissions needed before any GTA build).
