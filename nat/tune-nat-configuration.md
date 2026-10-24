---
source: https://docs.cloud.google.com/nat/docs/tune-nat-configuration
page_updated: 2026-10-22
checked: 2026-10-24
licence: CC BY 4.0, adapted and modified
subjects: [networking, egress]
---

# Tune NAT configuration

Change how a {{ product }} gateway allocates ports and how long it keeps idle
mappings, so that your VMs don't run out of ports or hold connections longer than
they need.

## Choose a minimum number of ports per VM

Set the minimum with `--min-ports-per-vm`. The maximum, set with
`--max-ports-per-vm`, defaults to {{ nat_max_ports_per_vm }}.

## Change the port allocation method

Turn dynamic port allocation on with `--enable-dynamic-port-allocation`, or off with
`--no-enable-dynamic-port-allocation`. When it's on:

- the minimum must be a power of 2 between 32 and 32768
- the maximum must be a power of 2 between 64 and 65536, and greater than the minimum

## Modify NAT timeouts

(nat-timeouts)=
### NAT timeouts

| Timeout | Default (seconds) | gcloud flag |
|---|---|---|
| UDP Mapping Idle Timeout | {{ nat_udp_idle_timeout }} | `--udp-idle-timeout` |
| TCP Established Connection Idle Timeout | {{ nat_tcp_established_idle_timeout }} | `--tcp-established-idle-timeout` |
| TCP Transitory Connection Idle Timeout | {{ nat_tcp_transitory_idle_timeout }} | `--tcp-transitory-idle-timeout` |
| TCP TIME_WAIT Timeout | {{ nat_tcp_time_wait_timeout }} | `--tcp-time-wait-timeout` |
| ICMP Mapping Idle Timeout (Public NAT only) | {{ nat_icmp_idle_timeout }} | `--icmp-idle-timeout` |

### Change NAT timeouts

```bash
gcloud compute routers nats update NAT_NAME \
    --router=ROUTER_NAME \
    --region=REGION \
    --tcp-time-wait-timeout=SECONDS
```

## What's next

- [{{ product }} overview](overview.md)
