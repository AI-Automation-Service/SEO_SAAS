"""
Download all SKILL.md files from the claude-seo repository into skills/.

Run once after cloning:
    python scripts/download_skills.py
"""

import sys
from pathlib import Path

import httpx

REPO_BASE = "https://raw.githubusercontent.com/AgricIDaniel/claude-seo/main/skills"

SKILLS = [
    "seo-audit",
    "seo-backlinks",
    "seo-cluster",
    "seo-competitor-pages",
    "seo-content-brief",
    "seo-content",
    "seo-dataforseo",
    "seo-drift",
    "seo-ecommerce",
    "seo-flow",
    "seo-geo",
    "seo-google",
    "seo-hreflang",
    "seo-image-gen",
    "seo-images",
    "seo-local",
    "seo-maps",
    "seo-page",
    "seo-plan",
    "seo-programmatic",
    "seo-schema",
    "seo-sitemap",
    "seo-sxo",
    "seo-technical",
]

SKILLS_DIR = Path(__file__).parent.parent / "skills"


def download_skill(client: httpx.Client, skill: str) -> bool:
    url = f"{REPO_BASE}/{skill}/SKILL.md"
    target = SKILLS_DIR / skill / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = client.get(url, timeout=15)
    except httpx.RequestError as e:
        print(f"  [NETWORK ERROR] {skill}: {e}")
        return False

    if response.status_code == 404:
        print(f"  [NOT FOUND]    {skill} — skipping")
        return False

    if response.status_code != 200:
        print(f"  [HTTP {response.status_code}]    {skill} — skipping")
        return False

    target.write_text(response.text, encoding="utf-8")
    print(f"  [OK]           {skill}")
    return True


def main() -> None:
    print(f"Downloading {len(SKILLS)} skills from claude-seo...\n")
    ok = 0
    with httpx.Client(follow_redirects=True) as client:
        for skill in SKILLS:
            if download_skill(client, skill):
                ok += 1

    print(f"\nDone: {ok}/{len(SKILLS)} skills downloaded to skills/")
    if ok < len(SKILLS):
        print("Some skills failed. Check your internet connection and retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
