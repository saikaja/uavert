# Next steps: where to pick up

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Written:** 2026-10-01 19:20  ·  **Demo:** Tuesday, October 6, 2026

Start here in the next session. The full picture is in [status-goals-and-pending.md](status-goals-and-pending.md), and the formal record is in [README.md](README.md).

## Where things stand
- **Building is finished, and every build and test document is approved.** The last two, for fairer scores, crowds and heat, were approved on 2026-10-01 at 19:16.
- **Hosted site:** https://uavert.vercel.app has the latest code. It was deployed from `feature/backend-foundation` at commit `cd33e12`, and the acceptance check passed 26 of 26 against it after the deploy.
- **Only phase 6 is left:** Sai's end-to-end testing in [06-e2e-signoff.md](06-e2e-signoff.md). All 34 rows are still "Not tested".

## What to do next, in order

### 1. Get Sai's test results
Ask Sai for results against the checklist in [06-e2e-signoff.md](06-e2e-signoff.md), and record only what Sai reports. The rows that matter most:

| Row | What | When |
|---|---|---|
| 23 | Hosted site on laptop **and phone**: repeat rows 2, 5, 6 and 7 | Before the demo |
| 30 | Walk from Union Station to 125 Blue Jays Way. Does 53 Elevated feel right? | Any time |
| 22 | Is the ranking with StatCan weights acceptable to show? ([csi-vs-demo-ranking.md](csi-vs-demo-ranking.md)) | Before the demo |
| 33 | Nuit Blanche: search `100 Queen St W`; the Crowds bar should show 35 | **Saturday, October 3, evening only** |
| 27–28 | GitHub Actions "Refresh data" runs hourly with green ticks, and the "collected" times are recent | From October 2 |
| 34 | Heat warning reason | Only during a real heat alert; can stay "Not tested" |

Rows 18, 21 and 26 need the local server: `.\.venv\Scripts\python.exe -m uavert serve`, then open http://localhost:8000.

### 2. Fix anything that fails
Fix it, re-test, redeploy, and hand it back to Sai as "Round 2" in 06-e2e-signoff.md.

### 3. Close out after Sai signs off (ask before each step)
1. Merge `feature/backend-foundation` into `main`. At the conflict on `vercel.json`, keep the branch's version, which turns deploys from `main` back on.
2. Delete the GitHub Actions variable `DATA_BRANCH`. After the merge, the refresh runs from `main`.
3. Optionally, delete the empty `fresh_check` database on the Neon `test` branch. Neon deletions always need Sai's permission.

### 4. Offered but not requested yet
- A short demo deck for Tuesday.
- **Soften the night effect:** City Hall scores 100 at 2 am, and the walk from Union Station to Kensington scores 87 High because of one block. This may look alarming in the demo.
- Draft permission emails to the York, Durham and Peel police for GTA data ([gta-expansion-notes.md](gta-expansion-notes.md)).

## How things are done here
- **Deploy:** run `vercel deploy --prod --yes` from the feature branch, then check with `.\.venv\Scripts\python.exe scripts\acceptance_check.py https://uavert.vercel.app`, which should end with "26 of 26 checks passed".
- **Don't push to `main`** until the merge in step 3; Vercel deploys `main` to production.
- **Git identity:** fixed on 2026-10-01. The global `user.email` is now set to saikaja99@gmail.com, so commits work normally.
- **Commands:** run them as `python -m uavert` from `.venv`. Windows Smart App Control blocks `uavert.exe`.
- **Edits:** use Write or Edit instead of shell heredocs, and keep LF line endings.
- **Wording:** a higher score means riskier, and nothing is ever labelled "safe".
