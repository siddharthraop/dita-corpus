# Sphinx configuration for Set B: Cloud NAT sample pages in MyST Markdown.
# Adapted from the Google Cloud NAT documentation (CC BY 4.0) and modified.
# Values that appear on more than one page are MyST substitutions, defined once here.
# The Autonomous Author changes a value by editing this dictionary, not the pages.

project = "Cloud NAT (sample set)"
author = "Adapted by Siddharth Rao from Google Cloud documentation (CC BY 4.0)"
extensions = ["myst_parser"]
myst_enable_extensions = ["substitution", "colon_fence", "deflist"]
source_suffix = {".md": "markdown"}
exclude_patterns = ["_build"]
html_theme = "alabaster"

myst_substitutions = {
    "product": "Cloud NAT",
    # NAT timeouts, in seconds (source: Tune NAT configuration)
    "nat_udp_idle_timeout": "30",
    "nat_tcp_established_idle_timeout": "1200",
    "nat_tcp_transitory_idle_timeout": "30",
    "nat_tcp_time_wait_timeout": "120",
    "nat_icmp_idle_timeout": "30",
    # Ports
    "nat_max_ports_per_vm": "65536",
}
