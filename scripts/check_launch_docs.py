"""Validate public launch copy without adding documentation dependencies."""

from __future__ import annotations

import re
import json
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
POST_PATH = ROOT / "docs" / "launch" / "linkedin-release-post.md"
DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "docs" / "commercial-readiness.md",
    POST_PATH,
    ROOT / "docs" / "launch" / "founding-10-outreach-kit.md",
    ROOT / "docs" / "launch" / "owner-launch-decisions.md",
)
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def validate_post() -> int:
    text = POST_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"^## Post\s*\n(.*?)\n## Suggested first comment\s*$",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise SystemExit("LinkedIn post section could not be isolated")

    post = match.group(1).strip()
    length = len(post)
    if length > 2_800:
        raise SystemExit(
            f"LinkedIn post is {length} characters; keep it at or below 2,800 "
            "to retain headroom under the platform's 3,000-character limit"
        )
    if "**" in post:
        raise SystemExit("LinkedIn post body contains Markdown bold markers")
    version = json.loads(
        (ROOT / "apps" / "web" / "package.json").read_text(encoding="utf-8")
    )["version"]
    release_url = "https://project-hope-charities.vercel.app/#download"
    if release_url not in post:
        raise SystemExit("LinkedIn post must point to the direct website download")
    if f"Project Hope {version}" not in post:
        raise SystemExit(f"LinkedIn post does not identify version {version}")
    if "FOUNDING 10" not in post:
        raise SystemExit(
            "LinkedIn post is missing the private Founding 10 call to action"
        )
    return length


def validate_local_links() -> None:
    missing: list[str] = []
    for document in DOCUMENTS:
        text = document.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative_target = unquote(target.split("#", maxsplit=1)[0])
            resolved = (document.parent / relative_target).resolve()
            if not resolved.exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    if missing:
        raise SystemExit("Missing local documentation links:\n" + "\n".join(missing))


if __name__ == "__main__":
    post_length = validate_post()
    validate_local_links()
    print(
        f"Launch documentation checks passed ({post_length}-character LinkedIn post)."
    )
