#!/usr/bin/env python3
"""Deduplicate and filter learn.liferay.com/w/dxp URLs by capability.

Reads reports/dxp_urls.json (plain text, one URL per line despite the
extension) and produces per-capability URL lists under reports/filtered/,
ready for the content-extraction phase.
"""

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "reports" / "dxp_urls.json"
OUTPUT_DIR = ROOT / "reports" / "filtered"

CAPABILITIES = {
    "cloud": "/w/dxp/cloud",
    "search": "/w/dxp/search",
    "self-hosted": "/w/dxp/self-hosted-installation-and-upgrades",
    "sites": "/w/dxp/sites",
    "security": "/w/dxp/security-and-administration",
    "development": "/w/dxp/development",
}

OUT_OF_SCOPE_PREFIXES = [
    "/w/dxp/commerce",
    "/w/dxp/personalization",
    "/w/dxp/low-code",
    "/w/dxp/content-management-system",
    "/w/dxp/digital-asset-management",
    "/w/dxp/integration",
    "/w/dxp/ai",
    "/w/dxp/getting-started",
]

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
        capabilities (commerce, personalization, etc.) rather than being an
        unrecognized/"odd" URL worth flagging for manual review
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


def main() -> None:
    raw_lines = INPUT_FILE.read_text(encoding="utf-8").splitlines()
    seen = set()
    deduped = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        norm = normalize(line)
        if norm in seen:
            continue
        seen.add(norm)
        deduped.append(norm)

    buckets: dict[str, list[str]] = {name: [] for name in CAPABILITIES}
    pruned: list[tuple[str, str]] = []  # (url, reason)
    prune_counts = {label: 0 for label, _ in SELF_HOSTED_PRUNE_RULES}
    unmatched: list[str] = []

    for url in deduped:
        classification = classify_url(url)
        capability = classification["capability"]

        if capability is None:
            if not classification["known_out_of_scope"]:
                unmatched.append(url)
            continue

        if classification["prune_reason"] is not None:
            pruned.append((url, classification["prune_reason"]))
            prune_counts[classification["prune_reason"]] += 1
            continue

        buckets[capability].append(url)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, urls in buckets.items():
        out_file = OUTPUT_DIR / f"{name}_urls.txt"
        out_file.write_text("\n".join(sorted(urls)) + "\n", encoding="utf-8")

    pruned_file = OUTPUT_DIR / "self-hosted_pruned.txt"
    pruned_lines = [f"{url}\t# {reason}" for url, reason in sorted(pruned)]
    pruned_file.write_text("\n".join(pruned_lines) + ("\n" if pruned_lines else ""), encoding="utf-8")

    summary = {
        "capabilities": {
            name: {"unique_urls": len(urls)} for name, urls in buckets.items()
        },
        "self_hosted_pruned": {
            "total": len(pruned),
            "by_rule": prune_counts,
        },
        "total_in_scope": sum(len(urls) for urls in buckets.values()),
        "input_total_lines": len(raw_lines),
        "input_unique_lines": len(deduped),
        "unmatched_count": len(unmatched),
    }
    summary_file = OUTPUT_DIR / "summary.json"
    summary_file.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("Conteo por capability:")
    for name, urls in buckets.items():
        print(f"  {name:12s}: {len(urls)}")
    print(f"\nTotal (6 capabilities): {summary['total_in_scope']}")
    print(f"\nSelf-hosted podadas: {len(pruned)}")
    for label, count in prune_counts.items():
        print(f"  - {label}: {count}")

    if unmatched:
        print(f"\nURLs sin encajar en scope ni en descartadas ({len(unmatched)}):")
        for url in unmatched:
            print(f"  {url}")
    else:
        print("\nNo hay URLs raras fuera del scope conocido.")


if __name__ == "__main__":
    main()
