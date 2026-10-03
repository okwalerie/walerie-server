# Service disposition — one decision record

Canonical decision ownership: GitHub issue #8. Route/TLS execution consumes these decisions in #4; backup contracts consume them in #3. A failed probe, inactive process or unavailable image is **not** retirement approval.

| Source service label | Confirmed intent | Next decision/check |
|---|---|---|
| lofsite | Paused; canonical definition and data retained | Choose reproducible image recovery or explicit retirement; do not unmask while image is missing |
| deepwiki-open | Not established | Restore/rebuild versus retain paused/retire; existing mask must be preserved |
| home109-public | Not established | Same lifecycle/image decision; preserve existing mask |
| litho-book | Not established | Same lifecycle/image decision; preserve existing mask |
| opendeepwiki-api | Not established | Classify app stack and image/data recovery before activation |
| opendeepwiki-web | Not established | Coordinate with API/pod, no isolated blanket startup |
| supermemory | Not established | Decide restore/rebuild vs retirement; local image was missing at prior inspection |
| Frappe | Offline observed, not retirement approval | Confirm recovery/retention and active/dormant intent before routes or logical backup requirements change |
| Nextcloud | Offline observed, not retirement approval | Same; preserve cold database and application data, no first-run bootstrap |
| GSB | Not established | Identify exact origin/declaration and intended state; don't infer an application from the label |
| Buzz | Offline observed, not retirement approval | Confirm PostgreSQL/object/git recovery and expected route |
| Forgejo | Not established | Confirm expected service, image/data and route before activation |
| Cockpit | TLS route repair requested | Verify certificate identity and exact access path; never disable verification to hide mismatch |
| Rama | Running cluster continuity required | Reconcile existing local runtime image with reproducible build reference without rebuilding/replacing live workloads blindly |
| Hermes identity proxy | Existing issue #8 says obsolete/intentionally not revived | Preserve that decision; do not restart the old proxy to make a historical failed unit green |
| Zulip | Existing persistent masks/offline state retained | Decide retained pause vs explicit retirement and cold-data recovery; no database activation just to satisfy backups |
| Elendil auth/nginx | Existing masks retained | Confirm intended stack lifecycle, auth/data/route custody; no blanket unmask |
| DeepWiki demos | Existing mask retained | Confirm lifecycle and image/source custody before changing monitoring |
| home109 repository wiki | Existing mask retained | Confirm lifecycle and source/image/data custody |

Review every remaining unclassified captured application in `services.json`, not only this initial named matrix. Build/network/pod resources need semantic dependency/recreation contracts; inactive successful helper units are not automatic pauses or outages.

Use exact deployed identifiers when implementing each row; source labels above are retained as supplied and are not claims of equivalent Quadlet names. Decisions require a reason, data-retention/backup contract, monitoring/ingress treatment and rollback/resume procedure. Retiring source is separate from deleting data or remote backups.
