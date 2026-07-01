#!/usr/bin/env python3
"""Shared URL/capability utilities for the crawl4ai pipeline's docs.

Capability classification (matching learn.liferay.com/w/dxp URLs to one of
the 14 capabilities listed on /w/dxp/index, plus the self-hosted prune
rules), the URL->filename/frontmatter helpers used when writing pages to
raw/{capability}/*.md, and resolve_docs_dir() -- the one place that decides
where that raw/ docs folder actually lives on disk.
"""

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

CAPABILITIES = {
    "cloud": "/w/dxp/cloud",
    "search": "/w/dxp/search",
    "self-hosted": "/w/dxp/self-hosted-installation-and-upgrades",
    "sites": "/w/dxp/sites",
    "security": "/w/dxp/security-and-administration",
    "development": "/w/dxp/development",
    "commerce": "/w/dxp/commerce",
    "personalization": "/w/dxp/personalization",
    "low-code": "/w/dxp/low-code",
    "content-management-system": "/w/dxp/content-management-system",
    "digital-asset-management": "/w/dxp/digital-asset-management",
    "integration": "/w/dxp/integration",
    "ai": "/w/dxp/ai",
    "getting-started": "/w/dxp/getting-started",
}

# All 14 capabilities listed on https://learn.liferay.com/w/dxp/index are in
# scope now; nothing under /w/dxp is deliberately excluded anymore.
OUT_OF_SCOPE_PREFIXES: list[str] = []

# (rule label, substring whose presence -- followed by more path -- excludes the URL)
SELF_HOSTED_PRUNE_RULES = [
    (
        "deprecations-and-breaking-changes-reference subpage",
        "/upgrading-liferay/deprecations-and-breaking-changes-reference/",
    ),
    (
        "installing-earlier-liferay-versions-on-application-servers subpage",
        "/installing-earlier-liferay-versions-on-application-servers/",
    ),
    (
        "cne-aws-ready subpage",
        "/cloud-native-experience/cne-cloud-provider-ready/cne-aws-ready/",
    ),
    (
        "cne-gcp-ready subpage",
        "/cloud-native-experience/cne-cloud-provider-ready/cne-gcp-ready/",
    ),
]


def normalize(url: str) -> str:
    """Strip a trailing slash from the path, keep everything else as-is."""
    parsed = urlparse(url)
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return parsed._replace(path=path).geturl()


def matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def prune_reason(path: str) -> str | None:
    for label, substr in SELF_HOSTED_PRUNE_RULES:
        if substr in path:
            return label
    return None


def classify_url(url: str) -> dict:
    """Classify a single (already-normalized) URL for the capability pipeline.

    Returns a dict with:
      - capability: matched capability name, or None if out of scope
      - prune_reason: self-hosted prune rule label, or None
      - known_out_of_scope: True if it matches one of the known-excluded
        capabilities rather than being an unrecognized/"odd" URL worth
        flagging for manual review
    """
    path = urlparse(url).path
    matched_capability = None
    for name, prefix in CAPABILITIES.items():
        if matches_prefix(path, prefix):
            matched_capability = name
            break

    if matched_capability is None:
        known_out_of_scope = any(matches_prefix(path, prefix) for prefix in OUT_OF_SCOPE_PREFIXES)
        return {"capability": None, "prune_reason": None, "known_out_of_scope": known_out_of_scope}

    reason = prune_reason(path) if matched_capability == "self-hosted" else None
    return {"capability": matched_capability, "prune_reason": reason, "known_out_of_scope": False}


def slugify(url: str, prefix: str) -> str:
    """URL path (with the capability prefix stripped) -> a flat filename stem."""
    path = urlparse(url).path
    remainder = path[len(prefix):].strip("/")
    if not remainder:
        return "index"
    return remainder.replace("/", "-")


def build_frontmatter(url: str, capability: str, markdown: str) -> str:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    lines = [
        "---",
        f'url: "{url}"',
        f"capability: {capability}",
        f'fetched_at: "{fetched_at}"',
        f'content_hash: "sha256:{content_hash}"',
        "---",
        "",
    ]
    return "\n".join(lines)


def _default_data_dir() -> Path:
    """Per-user app-data directory, one convention per OS, so the docs
    live in the same predictable place regardless of which project you
    happen to be running the scraper or the skill from."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "liferay-docs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "liferay-docs"
    # Linux and other Unix-likes: XDG Base Directory spec
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "liferay-docs"


def resolve_docs_dir() -> Path:
    """Where the local docs (raw/, reports/filtered/) live: $LIFERAY_DOCS_DIR
    if set, otherwise the OS-appropriate default data directory. The same
    shared docs regardless of the current project, unless explicitly
    overridden -- see _default_data_dir() for the per-OS default."""
    override = os.environ.get("LIFERAY_DOCS_DIR")
    if override:
        return Path(override).expanduser()
    return _default_data_dir()
