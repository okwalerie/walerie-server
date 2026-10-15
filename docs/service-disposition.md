# Service disposition — one decision record

Canonical decision ownership: GitHub issue #8. Route/TLS execution consumes these decisions in #4; backup contracts consume them in #3. A failed probe, inactive process or unavailable image is **not** retirement approval.

| Source service label | Confirmed intent | Next decision/check |
|---|---|---|
| lofsite | Paused; canonical definition and data retained | Choose reproducible image recovery or explicit retirement; do not unmask while image is missing |
| GSB | Not established | Identify exact origin/declaration and intended state; don't infer an application from the label |
| Buzz | Offline observed, not retirement approval | Confirm PostgreSQL/object/git recovery and expected route |
| Cockpit | TLS route repair requested | Verify certificate identity and exact access path; never disable verification to hide mismatch |
| Rama | Running cluster continuity required | Reconcile existing local runtime image with reproducible build reference without rebuilding/replacing live workloads blindly |
| Hermes identity proxy | Existing issue #8 says obsolete/intentionally not revived | Preserve that decision; do not restart the old proxy to make a historical failed unit green |

## Deleted 2026-10-15

Retired and deleted at owner direction (Valerie): Frappe, Nextcloud, Forgejo, supermemory, deepwiki-open/demos, opendeepwiki, Elendil auth/nginx/showcase, home109 public/repowiki, litho-book, valeriekim-blog (moving to GitHub Pages), Zulip. Quadlets, units, private env files, images, local service data and the `frappe.waler.ie`, `cloud.waler.ie`, `valeriekim.ca`, `www.valeriekim.ca` tunnel routes were removed. No local data was retained; earlier copies exist only in the off-host restic snapshots until retention expires them.

Review every remaining unclassified captured application in `services.json`, not only this initial named matrix. Build/network/pod resources need semantic dependency/recreation contracts; inactive successful helper units are not automatic pauses or outages.

Use exact deployed identifiers when implementing each row; source labels above are retained as supplied and are not claims of equivalent Quadlet names. Decisions require a reason, data-retention/backup contract, monitoring/ingress treatment and rollback/resume procedure. Retiring source is separate from deleting data or remote backups.
