#!/usr/bin/env python3
"""Generate a dependency-free SVG activity panel from GitHub GraphQL data."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any

GRAPHQL_URL = "https://api.github.com/graphql"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 privacy: PUBLIC, orderBy: {field: UPDATED_AT, direction: DESC}) {
      totalCount
      nodes { stargazerCount primaryLanguage { name color } }
    }
  }
}
"""


def utc_window(now: datetime | None = None) -> tuple[str, str]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    start = current - timedelta(days=364)
    return f"{start.isoformat()}T00:00:00Z", f"{current.isoformat()}T23:59:59Z"


def fetch_profile(login: str, token: str) -> dict[str, Any]:
    start, end = utc_window()
    body = json.dumps(
        {"query": QUERY, "variables": {"login": login, "from": start, "to": end}}
    ).encode()
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-profile-readme",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {payload['errors']}")
    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user not found: {login}")
    return user


def calculate_streak(days: list[dict[str, Any]]) -> tuple[int, int]:
    longest = 0
    running = 0
    for day in days:
        if day["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    tail = days[:-1] if days and days[-1]["contributionCount"] == 0 else days
    current = 0
    for day in reversed(tail):
        if day["contributionCount"] == 0:
            break
        current += 1
    return current, longest


def summarise(user: dict[str, Any]) -> dict[str, Any]:
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = [week["contributionDays"] for week in calendar["weeks"]]
    days = [day for week in weeks for day in week]
    weekly = [sum(day["contributionCount"] for day in week) for week in weeks]
    current, longest = calculate_streak(days)
    repos = user["repositories"]["nodes"]
    languages = Counter(
        repo["primaryLanguage"]["name"]
        for repo in repos
        if repo.get("primaryLanguage")
    )
    colours = {
        repo["primaryLanguage"]["name"]: repo["primaryLanguage"].get("color") or "#2dd4bf"
        for repo in repos
        if repo.get("primaryLanguage")
    }
    return {
        "total": calendar["totalContributions"],
        "active_days": sum(day["contributionCount"] > 0 for day in days),
        "weekly": weekly,
        "current_streak": current,
        "longest_streak": longest,
        "repos": user["repositories"]["totalCount"],
        "stars": sum(repo["stargazerCount"] for repo in repos),
        "followers": user["followers"]["totalCount"],
        "languages": [(name, count, colours[name]) for name, count in languages.most_common(5)],
    }


def sparkline(values: list[int], x: float, y: float, width: float, height: float) -> str:
    points = values or [0]
    peak = max(points) or 1
    step = width / max(len(points) - 1, 1)
    coordinates = [
        (x + index * step, y + height - (value / peak) * height)
        for index, value in enumerate(points)
    ]
    path = " ".join(
        ("M" if index == 0 else "L") + f"{px:.1f},{py:.1f}"
        for index, (px, py) in enumerate(coordinates)
    )
    return f'<path d="{path}" fill="none" class="accent-stroke" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'


def activity_svg(summary: dict[str, Any]) -> str:
    stats = [
        (summary["total"], "contributions / year"),
        (summary["active_days"], "active days"),
        (summary["repos"], "public repositories"),
        (summary["stars"], "repository stars"),
    ]
    stat_nodes = []
    for index, (value, label) in enumerate(stats):
        x = 38 + index * 224
        stat_nodes.append(
            f'<text x="{x}" y="64" class="strong" font-size="30" font-weight="700">{value}</text>'
            f'<text x="{x}" y="87" class="muted" font-size="12">{escape(label)}</text>'
        )

    language_nodes = []
    languages = summary["languages"]
    maximum = max((count for _, count, _ in languages), default=1)
    for index, (name, count, colour) in enumerate(languages):
        y = 166 + index * 24
        bar_width = 180 * count / maximum
        language_nodes.append(
            f'<text x="650" y="{y + 10}" class="text" font-size="12">{escape(name)}</text>'
            f'<rect x="760" y="{y}" width="{bar_width:.1f}" height="10" rx="5" fill="{escape(colour)}" opacity=".88"/>'
            f'<text x="946" y="{y + 10}" class="muted" font-size="11" text-anchor="end">{count} repos</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="310" viewBox="0 0 960 310" role="img" aria-labelledby="title desc">
<title id="title">GitHub activity</title>
<desc id="desc">Public GitHub activity over the last 365 days.</desc>
<style>
  .panel{{fill:#f6f8fa;stroke:#d0d7de}} .strong{{fill:#1f2328}} .text{{fill:#30363d}}
  .muted{{fill:#656d76}} .rule{{stroke:#d8dee4}} .accent-stroke{{stroke:#0f9f8f}}
  @media(prefers-color-scheme:dark){{.panel{{fill:#0d1117;stroke:#30363d}}.strong{{fill:#f0f6fc}}
  .text{{fill:#c9d1d9}}.muted{{fill:#8b949e}}.rule{{stroke:#30363d}}.accent-stroke{{stroke:#2dd4bf}}}}
</style>
<rect x="1" y="1" width="958" height="308" rx="16" class="panel"/>
<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">
  {''.join(stat_nodes)}
  <line x1="38" y1="111" x2="922" y2="111" class="rule"/>
  <text x="38" y="146" class="muted" font-size="11" letter-spacing="1.5">WEEKLY CONTRIBUTIONS</text>
  {sparkline(summary['weekly'], 38, 166, 548, 92)}
  <text x="38" y="285" class="text" font-size="12">current streak  <tspan class="strong" font-weight="700">{summary['current_streak']} days</tspan></text>
  <text x="280" y="285" class="text" font-size="12">longest streak  <tspan class="strong" font-weight="700">{summary['longest_streak']} days</tspan></text>
  <text x="650" y="146" class="muted" font-size="11" letter-spacing="1.5">PRIMARY LANGUAGE BY REPOSITORY</text>
  {''.join(language_nodes)}
</g>
</svg>'''


def write_if_changed(path: Path, content: str) -> bool:
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2
    login = os.environ.get("GH_LOGIN", "prospeck")
    output = Path(os.environ.get("OUT_DIR", ".")) / "assets" / "activity.svg"
    summary = summarise(fetch_profile(login, token))
    changed = write_if_changed(output, activity_svg(summary))
    print(
        f"generated {output}: {summary['total']} contributions, "
        f"{summary['active_days']} active days, changed={changed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

