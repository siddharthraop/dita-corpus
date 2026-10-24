---
source: https://docs.cloud.google.com/nat/docs/release-notes
checked: 2026-10-24
licence: CC BY 4.0, adapted and modified
---

# {{ product }} release notes

This sample keeps only the entries that the docs-and-AI projects use.

## March 31, 2026

**Announcement**

The default TCP `TIME_WAIT` timeout for new {{ product }} gateways is changing from
{{ nat_tcp_time_wait_timeout_legacy }} seconds to {{ nat_tcp_time_wait_timeout }} seconds in
all regions. From June 30 to September 29, 2026, a new gateway gets either default,
depending on when the update reaches its region. On or after
{{ nat_time_wait_change_date }}, every new gateway gets {{ nat_tcp_time_wait_timeout }}
seconds.

Existing gateways keep their current default, and gateways with a custom `TIME_WAIT`
value are unaffected. To change the value, use the `--tcp-time-wait-timeout` flag.
