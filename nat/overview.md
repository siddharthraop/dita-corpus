---
source: https://docs.cloud.google.com/nat/docs/overview
page_updated: 2026-10-22
checked: 2026-10-24
licence: CC BY 4.0, adapted and modified
subjects: [networking, egress]
---

# {{ product }} overview

{{ product }} provides network address translation for resources that have no
external IP address, so they can make outbound connections without being reachable
from the internet.

## Types of {{ product }}

Public NAT
: Lets resources without external IPv4 addresses connect to IPv4 destinations on the
  internet. The VMs share a set of external IP addresses, and the gateway assigns an
  external IP address and source ports to each VM for its outbound connections.
  {{ product }} doesn't rely on proxy VMs.

Private NAT
: Translates addresses between private networks, for example between VPC networks.

## Supported resources

{{ product }} supports these resource types:

- Compute Engine VM instances
- Google Kubernetes Engine (GKE) clusters
- Cloud Run instances
- Cloud Run functions instances
- App Engine standard environment instances
- Regional internet network endpoint groups (NEGs), with Public NAT only

## What's next

- [Tune NAT configuration](tune-nat-configuration.md)
