# Approvals ledger (started 19 Oct 2026; review D-04, docs/16 §6 rule 6)

One row per decision Rafid (R) has made that the agents rely on. Add a row **before** acting on a new approval:
- the date (UTC);
- R's words, quoted, or the relay that carried them;
- the scope;
- the files or stages it covers.

An approval that isn't here doesn't exist. Ask instead.

| Date | Decision | R's words / source | Scope | Covers |
|---|---|---|---|---|
| 14 Oct | Rules and IP first; iMEMORY patent not filed | "Rules and IP come first... If any rule would require disclosing it, stop and flag it." | Whole project | docs/01; iMEMORY stays out of the final unless counsel signs off |
| 14 Oct | Box read-only | "Read-only on Box. Don't move, rename, or delete files." | All agents | `rclone copy box:` only |
| 14 Oct | No public upload of iMEMORY | "Never upload iMEMORY weights, code, or proprietary data anywhere public, except what the rules require and I approve." | All agents | Only `gdrive:VCC2026/checkpoints_private` |
| 14 Oct | Collaborator and confidential folders **not approved** | "Don't use data from collaborator or confidential folders (e.g., the IAB_Shalek_Lab, Jordi-RQ, and Mariana-RQ shared drives, and anything marked Confidential) without my written confirmation" | All agents | Not to be used until a row here says otherwise |
| 14 Oct | Downloads go to Google Drive (5 TB) | "if any downloads need to happen, it should happen on the google drive. the limit is 5TB." | Curation and runbook | Ask before > 300 GB (CLAUDE.md) |
| 14 Oct | Instances | "You do not launch instances. I launch them when you ask." Budget $7,000; warnings at 50/75/90% | Compute | docs/05 |
| 15 Oct | X-Atlas/Orion and X-Atlas/Pisces (CC BY-NC-SA 4.0) may be used | Recorded in docs/03 L34 and docs/13 §0. Planning flagged NC/SA for a company entry, and R accepted. | Data | Every NC dataset is tagged `licence` in `loco.json`; the final is scored with and without NC (R4-09). **Final NC choice still open (21 Oct).** |
| (unrecorded) | H1 subset overwritten in place | The agent wrote "approved by R"; no quote or date found (review D-04) | — | Treat as unverified; don't repeat |
| 18 Oct | Execute the round-4 plan | R asked planning to "propose and plan the solutions ... upload to the repo for the agent to execute" | Runbook E044–E049 | LB entries only under docs/16 §3 |
| 2026-10-19 ~08:00 UTC | Rafid: "Continue" (in reply to the E045 stop on the H1-R400 retro FAIL, with option 1 = continue to E046 treating H1 retro as the one-line bracket the runbook anticipates) | Run E046 despite the H1-R400 retro FAIL in E045; H1 still enforces docs/16 §3 rule 2. Does not cover E046c, E047+ or Phase B. |
| 2026-10-20 ~02:00 UTC | Rafid: "I approve this batch: log it in docs/APPROVALS.md, then run E047a → E050 → E047b in order without waiting for me between stages. Stop only on a V* retro FAIL (including the new like-for-like retro) or a verify FAIL. An H1-R400 retro FAIL is informational, not a stop." | 20 Oct batch (docs/16 §9, runbook "▶ 20 Oct batch"): 2 LB entries on 20 Oct UTC (E047a = ENS_E021B5_w55; E047b per the runbook rule), E050 sweep. Does not cover E048 (needs the NC decision). |
