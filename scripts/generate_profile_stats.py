#!/usr/bin/env python3
"""
generate_profile_stats.py
Queries GitHub GraphQL & REST APIs and generates self-hosted animated SVG cards
with CSS animations, gradients, glassmorphism styling, and responsive layout.
Zero third-party external service dependencies (no Vercel / Heroku).
"""

import os
import json
import math
import re
import urllib.request
import urllib.error
import textwrap
from datetime import datetime, timedelta, timezone
from html import escape

USERNAME = "MERCIA-lab"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

# Default / Fallback data from verified live API state
FALLBACK_DATA = {
    "total_stars": 5,
    "total_forks": 0,
    "total_commits": 54,
    "total_prs": 1,
    "total_issues": 0,
    "total_reviews": 0,
    "contributed_repos": 6,
    "total_contributions": 61,
    "current_streak": 3,
    "longest_streak": 4,
    "streak_range": "Aug 10 - Sep 03",
    "contribution_days": [],
    "languages": [
        {"name": "TypeScript", "bytes": 331307, "color": "#3178c6", "percent": 51.8},
        {"name": "JavaScript", "bytes": 133083, "color": "#f1e05a", "percent": 20.8},
        {"name": "HTML", "bytes": 86433, "color": "#e34c26", "percent": 13.5},
        {"name": "Java", "bytes": 38044, "color": "#b07219", "percent": 6.0},
        {"name": "Python", "bytes": 33575, "color": "#3572A5", "percent": 5.3},
        {"name": "CSS", "bytes": 31636, "color": "#563d7c", "percent": 2.6},
    ],
    "top_repos": [
        {"name": "Shipping-Tracking-System", "lang": "TypeScript", "color": "#3178c6", "stars": 1, "forks": 0},
        {"name": "daily-routine-tracker", "lang": "JavaScript", "color": "#f1e05a", "stars": 1, "forks": 0},
        {"name": "Financial-Advisor-System", "lang": "JavaScript", "color": "#f1e05a", "stars": 1, "forks": 0},
        {"name": "FreeMCue", "lang": "Python", "color": "#3572A5", "stars": 1, "forks": 0},
    ],
}

def fetch_live_github_data(token):
    """Attempts to fetch live statistics via GitHub GraphQL and REST API."""
    data = dict(FALLBACK_DATA)
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "MERCIA-lab-Profile-Updater",
        "Content-Type": "application/json"
    }
    headers["Authorization"] = f"Bearer {token}"

    graphql_query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          totalIssueContributions
          totalRepositoryContributions
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            name
            url
            description
            updatedAt
            isPrivate
            stargazerCount
            forkCount
            primaryLanguage {
              name
              color
            }
            languages(first: 10) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """

    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=365)
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({
                "query": graphql_query,
                "variables": {
                    "login": USERNAME,
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat(),
                },
            }).encode(),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            res_data = json.loads(res.read().decode())
            if res_data.get("errors"):
                raise RuntimeError(f"GitHub GraphQL query failed: {res_data['errors']}")
            user = res_data.get("data", {}).get("user")
            if not user:
                raise RuntimeError(f"GitHub user {USERNAME} was not found in the API response.")
            if user:
                cc = user.get("contributionsCollection", {})
                data["total_commits"] = cc.get("totalCommitContributions", data["total_commits"])
                data["total_prs"] = cc.get("totalPullRequestContributions", data["total_prs"])
                data["total_reviews"] = cc.get("totalPullRequestReviewContributions", data["total_reviews"])
                data["total_issues"] = cc.get("totalIssueContributions", data["total_issues"])
                data["contributed_repos"] = cc.get("totalRepositoryContributions", data["contributed_repos"])
                data["total_contributions"] = cc.get("contributionCalendar", {}).get("totalContributions", data["total_contributions"])
                data["streak_range"] = f"{start_date:%b %d, %Y} - {end_date:%b %d, %Y}"

                weeks = cc.get("contributionCalendar", {}).get("weeks", [])
                days = [d for w in weeks for d in w.get("contributionDays", [])]
                data["contribution_days"] = [
                    {
                        "date": day["date"],
                        "count": day.get("contributionCount", 0),
                        "week": week_index,
                        "weekday": day_index,
                    }
                    for week_index, week in enumerate(weeks)
                    for day_index, day in enumerate(week.get("contributionDays", []))
                ]
                cur_streak = 0
                max_streak = 0
                streak = 0
                for d in reversed(days):
                    if d.get("contributionCount", 0) > 0:
                        cur_streak += 1
                    elif cur_streak > 0:
                        break
                for d in days:
                    if d.get("contributionCount", 0) > 0:
                        streak += 1
                        if streak > max_streak:
                            max_streak = streak
                    else:
                        streak = 0
                data["current_streak"] = cur_streak
                data["longest_streak"] = max(max_streak, data["current_streak"])

                repos = [
                    repo for repo in user.get("repositories", {}).get("nodes", [])
                    if not repo.get("isPrivate", False)
                ]
                total_stars = sum(r.get("stargazerCount", 0) for r in repos)
                data["total_stars"] = total_stars
                data["total_forks"] = sum(r.get("forkCount", 0) for r in repos)
                data["top_repos"] = sorted(
                    (
                        {
                            "name": repo["name"],
                            "url": repo["url"],
                            "description": repo.get("description") or "",
                            "updated_at": repo.get("updatedAt", ""),
                            "is_private": repo.get("isPrivate", False),
                            "lang": (repo.get("primaryLanguage") or {}).get("name") or "Other",
                            "color": (repo.get("primaryLanguage") or {}).get("color") or "#8b949e",
                            "stars": repo.get("stargazerCount", 0),
                            "forks": repo.get("forkCount", 0),
                        }
                        for repo in repos
                    ),
                    key=lambda repo: (repo["stars"], repo["updated_at"]),
                    reverse=True,
                )[:8]

                lang_map = {}
                for r in repos:
                    for edge in r.get("languages", {}).get("edges", []):
                        lname = edge.get("node", {}).get("name")
                        lcolor = edge.get("node", {}).get("color") or "#8b949e"
                        lsize = edge.get("size", 0)
                        if lname not in lang_map:
                            lang_map[lname] = {"name": lname, "bytes": 0, "color": lcolor}
                        lang_map[lname]["bytes"] += lsize

                tot_bytes = sum(v["bytes"] for v in lang_map.values())
                sorted_langs = sorted(lang_map.values(), key=lambda x: x["bytes"], reverse=True)[:6]
                for language in sorted_langs:
                    language["percent"] = round((language["bytes"] / tot_bytes) * 100, 1) if tot_bytes else 0
                data["languages"] = sorted_langs
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
        raise RuntimeError(f"Unable to refresh live GitHub analytics: {err}") from err

    return data


def generate_typing_headline_svg():
    """Generates an animated neon typing headline SVG."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="850" height="70" viewBox="0 0 850 70" fill="none">
  <style>
    @keyframes neonGlow {
      0%, 100% {
        filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.9)) drop-shadow(0 0 20px rgba(56, 189, 248, 0.4));
      }
      50% {
        filter: drop-shadow(0 0 14px rgba(56, 189, 248, 1)) drop-shadow(0 0 30px rgba(99, 102, 241, 0.6));
      }
    }
    .headline-text {
      font-family: 'Righteous', 'Segoe UI', system-ui, -apple-system, sans-serif;
      font-size: 38px;
      font-weight: 700;
      fill: #38BDF8;
      animation: neonGlow 3s ease-in-out infinite;
      text-anchor: middle;
      dominant-baseline: middle;
    }
  </style>
  <rect width="850" height="70" fill="transparent"/>
  <text x="425" y="42" class="headline-text">Meek Dieu Merci NUKURI</text>
</svg>"""


def generate_github_stats_svg(data):
    """Generates the native GitHub Stats overview card matching the sample preview."""
    stars = data["total_stars"]
    commits = data["total_commits"]
    prs = data["total_prs"]
    issues = data["total_issues"]
    contrib_repos = data["contributed_repos"]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" fill="none">
  <style>
    .card-bg {{
      fill: #0d1117;
      stroke: #30363d;
      stroke-width: 1.5;
      rx: 12px;
    }}
    .title {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      font-size: 14px;
      font-weight: 600;
      fill: #58a6ff;
    }}
    .label {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      font-size: 13px;
      font-weight: 400;
      fill: #c9d1d9;
    }}
    .value {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      font-size: 13px;
      font-weight: 700;
      fill: #f0f6fc;
    }}
    .icon {{
      fill: #38bdf8;
    }}
    .grade-circle-bg {{
      stroke: rgba(56, 189, 248, 0.15);
      stroke-width: 5;
      fill: none;
    }}
    .grade-circle-prog {{
      stroke: url(#cyanGrad);
      stroke-width: 5;
      stroke-linecap: round;
      stroke-dasharray: 220;
      stroke-dashoffset: 45;
      fill: none;
      animation: rotateRing 3s ease-in-out infinite alternate;
      transform-origin: 405px 105px;
    }}
    .grade-text {{
      font-family: 'Righteous', -apple-system, sans-serif;
      font-size: 24px;
      font-weight: 700;
      fill: #38bdf8;
      text-anchor: middle;
      dominant-baseline: middle;
    }}
    @keyframes rotateRing {{
      0% {{ stroke-dashoffset: 80; }}
      100% {{ stroke-dashoffset: 35; }}
    }}
  </style>

  <defs>
    <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="100%" stop-color="#818cf8" />
    </linearGradient>
  </defs>

  <rect width="495" height="195" class="card-bg" />

  <!-- Header Title -->
  <text x="25" y="32" class="title">{USERNAME}'s GitHub Stats</text>

  <!-- Metric 1: Total Stars -->
  <g transform="translate(25, 52)">
    <path class="icon" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
    <text x="24" y="12" class="label">Total Stars Earned:</text>
    <text x="195" y="12" class="value">{stars}</text>
  </g>

  <!-- Metric 2: Total Commits -->
  <g transform="translate(25, 78)">
    <path class="icon" d="M10.5 7.75a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm1.43.75a4.002 4.002 0 01-7.86 0H.75a.75.75 0 110-1.5h3.32a4.002 4.002 0 017.86 0h3.32a.75.75 0 110 1.5h-3.32z"/>
    <text x="24" y="12" class="label">Total Commits (2026):</text>
    <text x="195" y="12" class="value">{commits}</text>
  </g>

  <!-- Metric 3: Total PRs -->
  <g transform="translate(25, 104)">
    <path class="icon" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5zm0 1.5a.75.75 0 110 1.5.75.75 0 010-1.5zm0 6a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5zm0 1.5a.75.75 0 110 1.5.75.75 0 010-1.5z"/>
    <text x="24" y="12" class="label">Total PRs:</text>
    <text x="195" y="12" class="value">{prs}</text>
  </g>

  <!-- Metric 4: Total Issues -->
  <g transform="translate(25, 130)">
    <path class="icon" d="M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/>
    <text x="24" y="12" class="label">Total Issues:</text>
    <text x="195" y="12" class="value">{issues}</text>
  </g>

  <!-- Metric 5: Contributed to -->
  <g transform="translate(25, 156)">
    <path class="icon" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1h-8a1 1 0 00-1 1v6.708A2.486 2.486 0 014.5 9h8V1.5z"/>
    <text x="24" y="12" class="label">Contributed to (past year):</text>
    <text x="195" y="12" class="value">{contrib_repos}</text>
  </g>

  <!-- Circular Grade Badge -->
  <g transform="translate(405, 105)">
    <circle cx="0" cy="0" r="35" class="grade-circle-bg" />
    <circle cx="0" cy="0" r="35" class="grade-circle-prog" />
    <text x="0" y="2" class="grade-text">A+</text>
  </g>
</svg>"""


def generate_streak_stats_svg(data):
    """Generates the Streak Stats card with animated flame and streak rings."""
    tot_contribs = data["total_contributions"]
    cur_streak = data["current_streak"]
    long_streak = data["longest_streak"]
    streak_range = data["streak_range"]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" fill="none">
  <style>
    .card-bg {{
      fill: #0d1117;
      stroke: #30363d;
      stroke-width: 1.5;
      rx: 12px;
    }}
    .stat-number {{
      font-family: 'Righteous', -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 26px;
      font-weight: 700;
      fill: #f0f6fc;
      text-anchor: middle;
    }}
    .stat-label {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 13px;
      font-weight: 600;
      fill: #58a6ff;
      text-anchor: middle;
    }}
    .stat-sub {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 11px;
      fill: #8b949e;
      text-anchor: middle;
    }}
    .flame-icon {{
      fill: url(#flameGrad);
      animation: flamePulse 2s ease-in-out infinite;
      transform-origin: 247px 55px;
    }}
    .streak-ring-bg {{
      stroke: rgba(249, 115, 22, 0.2);
      stroke-width: 4;
      fill: none;
    }}
    .streak-ring-prog {{
      stroke: url(#flameGrad);
      stroke-width: 4;
      stroke-linecap: round;
      stroke-dasharray: 180;
      stroke-dashoffset: 40;
      fill: none;
      animation: glowRing 3s ease-in-out infinite alternate;
      transform-origin: 247px 88px;
    }}
    @keyframes flamePulse {{
      0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 4px rgba(249, 115, 22, 0.8)); }}
      50% {{ transform: scale(1.08); filter: drop-shadow(0 0 10px rgba(239, 68, 68, 1)); }}
    }}
    @keyframes glowRing {{
      0% {{ stroke-dashoffset: 60; }}
      100% {{ stroke-dashoffset: 20; }}
    }}
    .divider {{
      stroke: #21262d;
      stroke-width: 1;
    }}
  </style>

  <defs>
    <linearGradient id="flameGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f97316" />
      <stop offset="100%" stop-color="#ef4444" />
    </linearGradient>
  </defs>

  <rect width="495" height="195" class="card-bg" />

  <!-- Column 1: Total Contributions -->
  <g transform="translate(85, 45)">
    <text x="0" y="35" class="stat-number">{tot_contribs}</text>
    <text x="0" y="65" class="stat-label">Total Contributions</text>
    <text x="0" y="85" class="stat-sub">{streak_range}</text>
  </g>

  <!-- Vertical Divider 1 -->
  <line x1="170" y1="30" x2="170" y2="165" class="divider" />

  <!-- Column 2: Current Streak (Centered with Flame & Ring) -->
  <g transform="translate(247, 0)">
    <!-- Streak Ring -->
    <circle cx="0" cy="85" r="32" class="streak-ring-bg" />
    <circle cx="0" cy="85" r="32" class="streak-ring-prog" />

    <!-- Flame Icon in center -->
    <path class="flame-icon" transform="translate(-10, 60)" d="M5.05 13.95c.55-.3 1.15-.75 1.4-1.35.35-.85.1-1.85-.35-2.65-.5-1-.95-2-1-3.15 0-.15 0-.3.05-.45.05.3.15.6.3.85.45.85 1.25 1.55 1.9 2.3.9 1 1.7 2.15 1.65 3.55 0 .25-.05.5-.1.75.65-.6 1.1-1.4 1.2-2.3.15-1.15-.35-2.35-.95-3.35-.65-1.05-1.45-2.05-1.95-3.2-.45-1-.65-2.15-.45-3.25.3.35.65.65 1.05.9 1.35.85 2.25 2.3 2.7 3.8.55 1.8.35 3.85-.7 5.45-.45.7-.95 1.35-1.4 2.05-.2.3-.3.65-.25 1 .05.35.25.65.55.85 1.15.7 2.65.45 3.5-.6 1.05-1.25 1.35-2.95 1.1-4.55-.25-1.6-.9-3.1-1.65-4.55-.4-.75-.8-1.5-1.25-2.2-.15-.25-.3-.55-.35-.85.1-.05.2-.05.3-.05 1.5.1 2.9.85 3.9 1.95 1.35 1.5 1.95 3.6 1.75 5.65-.2 2.15-1.25 4.15-2.9 5.55-1.75 1.5-4.2 2.15-6.45 1.75-2.65-.45-4.85-2.35-5.6-4.9-.45-1.5-.2-3.1.6-4.4z"/>

    <!-- Streak number inside -->
    <text x="0" y="100" class="stat-number">{cur_streak}</text>
    <text x="0" y="135" class="stat-label">Current Streak</text>
    <text x="0" y="153" class="stat-sub">Active Cadence</text>
  </g>

  <!-- Vertical Divider 2 -->
  <line x1="325" y1="30" x2="325" y2="165" class="divider" />

  <!-- Column 3: Longest Streak -->
  <g transform="translate(410, 45)">
    <text x="0" y="35" class="stat-number">{long_streak}</text>
    <text x="0" y="65" class="stat-label">Longest Streak</text>
    <text x="0" y="85" class="stat-sub">Personal Best</text>
  </g>
</svg>"""


def generate_languages_svg(data):
    """Generates the Most Used Languages segmented bar and legend."""
    langs = data["languages"]
    total_pct = sum(l["percent"] for l in langs) or 100

    x_offset = 25
    bar_width = 445
    segments_svg = []
    legend_left = []
    legend_right = []

    for idx, l in enumerate(langs):
        w = round((l["percent"] / total_pct) * bar_width, 1)
        w = max(w, 4)
        rx = "4" if idx == 0 or idx == len(langs) - 1 else "0"
        segments_svg.append(f'<rect x="{x_offset}" y="60" width="{w}" height="10" fill="{l["color"]}" rx="{rx}" />')
        x_offset += w

        legend_item = f"""
        <g transform="translate(0, {len(legend_left) * 22 if idx % 2 == 0 else len(legend_right) * 22})">
          <circle cx="5" cy="5" r="5" fill="{l['color']}" />
          <text x="16" y="9" class="lang-label">{l['name']}</text>
          <text x="140" y="9" class="lang-pct">{l['percent']}%</text>
        </g>
        """
        if idx % 2 == 0:
            legend_left.append(legend_item)
        else:
            legend_right.append(legend_item)

    segments_str = "\n".join(segments_svg)
    left_str = "\n".join(legend_left)
    right_str = "\n".join(legend_right)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="175" viewBox="0 0 495 175" fill="none">
  <style>
    .card-bg {{
      fill: #0d1117;
      stroke: #30363d;
      stroke-width: 1.5;
      rx: 12px;
    }}
    .title {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      font-size: 14px;
      font-weight: 600;
      fill: #58a6ff;
      text-anchor: middle;
    }}
    .lang-label {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      font-size: 12px;
      font-weight: 500;
      fill: #c9d1d9;
    }}
    .lang-pct {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 600;
      fill: #8b949e;
    }}
  </style>

  <rect width="495" height="175" class="card-bg" />

  <text x="247" y="35" class="title">Most Used Languages</text>

  <!-- Progress Bar Track Background -->
  <rect x="25" y="60" width="445" height="10" fill="#21262d" rx="5" />

  <!-- Segmented Progress Bar -->
  <g>
    {segments_str}
  </g>

  <!-- Legend (2 Columns) -->
  <g transform="translate(45, 95)">
    {left_str}
  </g>
  <g transform="translate(285, 95)">
    {right_str}
  </g>
</svg>"""


def generate_top_repos_svg(data):
    """Generates the Top-Contributed Repositories card matching the sample preview."""
    repos = data["top_repos"]
    rows = []
    y_pos = 65

    for idx, r in enumerate(repos[:4]):
        badge_color = "#38bdf8" if idx == 0 else "#58a6ff"
        rows.append(f"""
    <g transform="translate(25, {y_pos})">
      <!-- Repo Icon -->
      <path fill="#8b949e" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1h-8a1 1 0 00-1 1v6.708A2.486 2.486 0 014.5 9h8V1.5z"/>
      <!-- Repo Name -->
      <text x="22" y="12" class="repo-name">{escape(r['name'])}</text>
      <!-- Stars Badge -->
      <rect x="390" y="-2" width="50" height="20" rx="10" fill="rgba(56, 189, 248, 0.12)" stroke="#38bdf8" stroke-width="0.8"/>
      <text x="415" y="12" class="repo-count">{r.get('stars', 0)}</text>
    </g>
    <line x1="25" y1="{y_pos + 26}" x2="470" y2="{y_pos + 26}" stroke="#21262d" stroke-width="0.8" />
        """)
        y_pos += 36

    rows_str = "\n".join(rows)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="225" viewBox="0 0 495 225" fill="none">
  <style>
    .card-bg {{
      fill: #0d1117;
      stroke: #30363d;
      stroke-width: 1.5;
      rx: 12px;
    }}
    .header-title {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 14px;
      font-weight: 600;
      fill: #58a6ff;
    }}
    .header-col {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 11px;
      font-weight: 600;
      fill: #8b949e;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .repo-name {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 12.5px;
      font-weight: 600;
      fill: #c9d1d9;
    }}
    .repo-count {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      fill: #38bdf8;
      text-anchor: middle;
    }}
  </style>

  <rect width="495" height="225" class="card-bg" />

  <!-- Card Header -->
  <text x="25" y="32" class="header-title">{USERNAME}'s Top Repositories</text>
  <text x="47" y="52" class="header-col">Repository</text>
  <text x="400" y="52" class="header-col">Stars</text>
  <line x1="25" y1="58" x2="470" y2="58" stroke="#30363d" stroke-width="1" />

  {rows_str}
</svg>"""


def generate_dev_quote_svg():
    """Generates the Random Dev Quote card matching the preview."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="495" height="225" viewBox="0 0 495 225" fill="none">
  <style>
    .card-bg {
      fill: #0d1117;
      stroke: #30363d;
      stroke-width: 1.5;
      rx: 12px;
    }
    .quote-mark {
      font-family: Georgia, serif;
      font-size: 42px;
      fill: #38bdf8;
      opacity: 0.6;
      text-anchor: middle;
    }
    .quote-line {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      font-size: 13.5px;
      font-style: italic;
      fill: #c9d1d9;
      text-anchor: middle;
    }
    .quote-author {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 12px;
      font-weight: 600;
      fill: #58a6ff;
      text-anchor: middle;
    }
    .quote-tag {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10.5px;
      fill: #8b949e;
      text-anchor: middle;
    }
  </style>

  <rect width="495" height="225" class="card-bg" />

  <!-- Quotation Mark -->
  <text x="247" y="50" class="quote-mark">“</text>

  <!-- Quote Lines -->
  <text x="247" y="82" class="quote-line">“Simplicity is prerequisite for reliability.”</text>
  <text x="247" y="105" class="quote-line">“Computer science is no more about computers</text>
  <text x="247" y="127" class="quote-line">than astronomy is about telescopes.”</text>

  <!-- Divider -->
  <line x1="180" y1="145" x2="315" y2="145" stroke="#30363d" stroke-width="1" />

  <!-- Author & Tag -->
  <text x="247" y="168" class="quote-author">Edsger W. Dijkstra</text>
  <text x="247" y="188" class="quote-tag">Turing Award Laureate &amp; Computing Pioneer</text>
</svg>"""


def generate_project_showcase_svg():
    """Generates high-fidelity project showcase cards for all flagship repositories."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="900" height="425" viewBox="0 0 900 425" fill="none">
  <style>
    .card {
      fill: #0d1117;
      stroke: #30363d;
      stroke-width: 1.5;
      rx: 12px;
    }
    .card-title {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 15px;
      font-weight: 700;
      fill: #38bdf8;
    }
    .card-desc {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 11.5px;
      fill: #8b949e;
    }
    .badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 600;
    }
    .status-dot {
      fill: #238636;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
  </style>

  <!-- Card 1: Shipping-Tracking-System -->
  <g transform="translate(0, 0)">
    <rect width="435" height="200" class="card" />
    <circle cx="28" cy="28" r="4" class="status-dot" />
    <text x="40" y="32" class="card-title">Shipping-Tracking-System</text>
    <rect x="340" y="16" width="70" height="20" rx="10" fill="rgba(56, 189, 248, 0.15)" stroke="#38bdf8" stroke-width="0.8"/>
    <text x="375" y="30" fill="#38bdf8" text-anchor="middle" class="badge">FLAGSHIP</text>

    <text x="28" y="62" class="card-desc">Cloud-based enterprise logistics platform covering parcel</text>
    <text x="28" y="80" class="card-desc">dispatch, freight tracking, dynamic warehouse queues,</text>
    <text x="28" y="98" class="card-desc">and real-time WebSocket fleet telematics monitoring.</text>

    <rect x="28" y="120" width="75" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="65" y="135" fill="#3178c6" text-anchor="middle" class="badge">TypeScript</text>
    <rect x="110" y="120" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="142" y="135" fill="#e0234e" text-anchor="middle" class="badge">NestJS</text>
    <rect x="182" y="120" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="214" y="135" fill="#38bdf8" text-anchor="middle" class="badge">Next.js</text>
    <rect x="254" y="120" width="80" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="294" y="135" fill="#336791" text-anchor="middle" class="badge">PostgreSQL</text>

    <path fill="#8b949e" transform="translate(28, 162)" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
    <text x="48" y="174" fill="#8b949e" class="badge">38 Commits</text>
    <text x="405" y="174" fill="#58a6ff" text-anchor="end" class="badge">Public • Production</text>
  </g>

  <!-- Card 2: FreeMCue -->
  <g transform="translate(465, 0)">
    <rect width="435" height="200" class="card" />
    <circle cx="28" cy="28" r="4" class="status-dot" />
    <text x="40" y="32" class="card-title">FreeMCue</text>
    <rect x="330" y="16" width="80" height="20" rx="10" fill="rgba(168, 85, 247, 0.15)" stroke="#a855f7" stroke-width="0.8"/>
    <text x="370" y="30" fill="#a855f7" text-anchor="middle" class="badge">AI COPILOT</text>

    <text x="28" y="62" class="card-desc">macOS AI teleprompter &amp; meeting copilot overlaying</text>
    <text x="28" y="80" class="card-desc">real-time conversational context while staying completely</text>
    <text x="28" y="98" class="card-desc">invisible from screen shares. Privacy-first architecture.</text>

    <rect x="28" y="120" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="60" y="135" fill="#3572A5" text-anchor="middle" class="badge">Python</text>
    <rect x="100" y="120" width="60" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="130" y="135" fill="#f1e05a" text-anchor="middle" class="badge">AI/ML</text>
    <rect x="167" y="120" width="60" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="197" y="135" fill="#a855f7" text-anchor="middle" class="badge">macOS</text>
    <rect x="234" y="120" width="75" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="271" y="135" fill="#22c55e" text-anchor="middle" class="badge">Real-Time</text>

    <path fill="#8b949e" transform="translate(28, 162)" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
    <text x="48" y="174" fill="#8b949e" class="badge">Open Source</text>
    <text x="405" y="174" fill="#58a6ff" text-anchor="end" class="badge">Public • Active</text>
  </g>

  <!-- Card 3: Financial-Advisor-System -->
  <g transform="translate(0, 220)">
    <rect width="435" height="200" class="card" />
    <circle cx="28" cy="28" r="4" class="status-dot" />
    <text x="40" y="32" class="card-title">Financial-Advisor-System</text>
    <rect x="335" y="16" width="75" height="20" rx="10" fill="rgba(34, 197, 94, 0.15)" stroke="#22c55e" stroke-width="0.8"/>
    <text x="372" y="30" fill="#22c55e" text-anchor="middle" class="badge">FINTECH</text>

    <text x="28" y="62" class="card-desc">Automated financial planning &amp; investment intelligence</text>
    <text x="28" y="80" class="card-desc">platform providing algorithmic risk evaluation, spending</text>
    <text x="28" y="98" class="card-desc">pattern analytics, and asset allocation modeling.</text>

    <rect x="28" y="120" width="75" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="65" y="135" fill="#f1e05a" text-anchor="middle" class="badge">JavaScript</text>
    <rect x="110" y="120" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="142" y="135" fill="#339933" text-anchor="middle" class="badge">Node.js</text>
    <rect x="182" y="120" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="214" y="135" fill="#38bdf8" text-anchor="middle" class="badge">Express</text>
    <rect x="254" y="120" width="75" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="291" y="135" fill="#a855f7" text-anchor="middle" class="badge">Analytics</text>

    <path fill="#8b949e" transform="translate(28, 162)" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
    <text x="48" y="174" fill="#8b949e" class="badge">6 Commits</text>
    <text x="405" y="174" fill="#58a6ff" text-anchor="end" class="badge">Public • Core</text>
  </g>

  <!-- Card 4: daily-routine-tracker -->
  <g transform="translate(465, 220)">
    <rect width="435" height="200" class="card" />
    <circle cx="28" cy="28" r="4" class="status-dot" />
    <text x="40" y="32" class="card-title">daily-routine-tracker</text>
    <rect x="315" y="16" width="95" height="20" rx="10" fill="rgba(234, 179, 8, 0.15)" stroke="#eab308" stroke-width="0.8"/>
    <text x="362" y="30" fill="#eab308" text-anchor="middle" class="badge">PRODUCTIVITY</text>

    <text x="28" y="62" class="card-desc">High-efficiency routine execution &amp; habits system designed</text>
    <text x="28" y="80" class="card-desc">to monitor cadence consistency, optimize daily focus blocks,</text>
    <text x="28" y="98" class="card-desc">and record velocity analytics with lightweight sync.</text>

    <rect x="28" y="120" width="75" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="65" y="135" fill="#f1e05a" text-anchor="middle" class="badge">JavaScript</text>
    <rect x="110" y="120" width="60" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="140" y="135" fill="#1572B6" text-anchor="middle" class="badge">CSS3</text>
    <rect x="177" y="120" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="209" y="135" fill="#38bdf8" text-anchor="middle" class="badge">Full-Stack</text>
    <rect x="249" y="120" width="80" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="289" y="135" fill="#22c55e" text-anchor="middle" class="badge">Automation</text>

    <path fill="#8b949e" transform="translate(28, 162)" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
    <text x="48" y="174" fill="#8b949e" class="badge">12 Commits</text>
    <text x="405" y="174" fill="#58a6ff" text-anchor="end" class="badge">Public • Active</text>
  </g>
</svg>"""


def generate_live_project_showcase_svg(data):
    """Render current public repository metadata as a responsive portfolio diagram."""
    repos = data.get("top_repos", [])[:6]
    card_height = 150
    height = max(card_height + 20, len(repos) * card_height + 20)
    max_stars = max((repo.get("stars", 0) for repo in repos), default=0)
    max_forks = max((repo.get("forks", 0) for repo in repos), default=0)
    cards = []

    for index, repo in enumerate(repos):
        y = 10 + index * card_height
        name = escape(textwrap.shorten(repo.get("name", "Repository"), width=30, placeholder="..."))
        url = escape(repo.get("url") or f"https://github.com/{USERNAME}/{repo.get('name', '')}", quote=True)
        description = repo.get("description") or "No repository description has been added yet."
        lines = textwrap.wrap(description, width=44)[:2]
        if not lines:
            lines = ["No repository description has been added yet."]
        description_svg = "\n".join(
            f'<text x="38" y="{y + 70 + line_index * 18}" class="description">{escape(line)}</text>'
            for line_index, line in enumerate(lines)
        )
        language = escape(textwrap.shorten(repo.get("lang", "Other"), width=22, placeholder="..."))
        language_color = escape(repo.get("color", "#8b949e"), quote=True)
        updated = escape((repo.get("updated_at") or "Unknown")[:10])
        stars = repo.get("stars", 0)
        forks = repo.get("forks", 0)
        star_height = max(6, round(52 * stars / max_stars)) if max_stars else 6
        fork_height = max(6, round(52 * forks / max_forks)) if max_forks else 6
        visibility = "PUBLIC"
        cards.append(f"""
  <a href="{url}">
    <g transform="translate(0, {y})">
      <rect x="15" y="14" width="475" height="126" rx="16" class="card-shadow"/>
      <rect x="10" y="8" width="475" height="126" rx="16" class="card"/>
      <path d="M26 9h260l-30 5H26z" fill="url(#edge)" opacity=".9"/>
      <rect x="26" y="25" width="5" height="88" rx="2.5" fill="{language_color}"/>
      <text x="42" y="48" class="title">{name}</text>
      <rect x="372" y="25" width="94" height="22" rx="11" class="status"/>
      <text x="419" y="40" text-anchor="middle" class="badge">{visibility}</text>
      {description_svg}
      <circle cx="43" cy="116" r="5" fill="{language_color}"/>
      <text x="55" y="120" class="meta">{language}</text>
      <text x="166" y="120" class="meta">Updated {updated}</text>
      <g transform="translate(330, 110)">
        <path d="M0 { -star_height}l10-6h48l-10 6z" fill="#86efac"/>
        <path d="M48 { -star_height}l10-6v{star_height}l-10 6z" fill="#166534"/>
        <rect x="0" y="{ -star_height}" width="48" height="{star_height}" fill="url(#starBar)"/>
        <text x="28" y="18" text-anchor="middle" class="metric">{stars} stars</text>
      </g>
      <g transform="translate(415, 110)">
        <path d="M0 { -fork_height}l10-6h48l-10 6z" fill="#bbf7d0"/>
        <path d="M48 { -fork_height}l10-6v{fork_height}l-10 6z" fill="#14532d"/>
        <rect x="0" y="{ -fork_height}" width="48" height="{fork_height}" fill="url(#forkBar)"/>
        <text x="28" y="18" text-anchor="middle" class="metric">{forks} forks</text>
      </g>
    </g>
  </a>""")

    content = "\n".join(cards) or """
  <text x="450" y="95" text-anchor="middle" class="title">No public repositories found</text>
"""
    return f"""    <svg xmlns="http://www.w3.org/2000/svg" width="495" height="{height}" viewBox="0 0 495 {height}" preserveAspectRatio="xMidYMin meet" fill="none">
  <style>
    .card {{ fill: url(#panel); stroke: #1f6f38; stroke-width: 1.2; }}
    .card-shadow {{ fill: #020617; opacity: .7; }}
    .title {{ font: 700 17px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #bbf7d0; }}
    .description {{ font: 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #a7f3b4; }}
    .meta {{ font: 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #6b9c76; }}
    .metric {{ font: 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #cbd5e1; }}
    .badge {{ font: 700 9px 'JetBrains Mono', monospace; fill: #86efac; }}
    .status {{ fill: #052e16; stroke: #166534; }}
    a {{ text-decoration: none; }}
    @media (max-width: 600px) {{
      .title {{ font-size: 20px; }}
      .description {{ font-size: 14px; }}
      .meta {{ font-size: 12px; }}
    }}
  </style>
  <defs>
    <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#102317"/>
      <stop offset=".55" stop-color="#08130b"/>
      <stop offset="1" stop-color="#0a1b10"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="#4ade80"/>
      <stop offset="1" stop-color="#14532d" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="starBar" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#4ade80"/>
      <stop offset="1" stop-color="#15803d"/>
    </linearGradient>
    <linearGradient id="forkBar" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#bbf7d0"/>
      <stop offset="1" stop-color="#166534"/>
    </linearGradient>
  </defs>
{content}
</svg>"""


def generate_pixel_banner_svg():
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="240" viewBox="0 0 1200 240">
  <rect width="1200" height="240" rx="8" fill="#07110b"/>
  <path d="M0 190h1200v50H0z" fill="#0a1b10"/>
  <g fill="#12371f">
    <path d="M50 40h24v24H50zM74 64h24v24H74zM98 88h24v24H98zM50 112h24v24H50z"/>
    <path d="M1060 35h24v24h-24zM1084 59h24v24h-24zM1108 83h24v24h-24zM1060 107h24v24h-24z"/>
    <path d="M150 160h18v18h-18zM174 160h18v18h-18zM198 160h18v18h-18zM222 160h18v18h-18z"/>
    <path d="M930 160h18v18h-18zM954 160h18v18h-18zM978 160h18v18h-18zM1002 160h18v18h-18z"/>
  </g>
  <path d="M270 48h660v2H270zM270 184h660v2H270z" fill="#1f6f38"/>
  <text x="600" y="105" text-anchor="middle" fill="#b7f7c4"
        font-family="'Courier New', monospace" font-size="38" font-weight="700"
        letter-spacing="3">MEEK DIEU MERCI NUKURI</text>
  <text x="600" y="148" text-anchor="middle" fill="#4ade80"
        font-family="'Courier New', monospace" font-size="18" font-weight="700"
        letter-spacing="2">COMPUTER SCIENCE | AI &amp; ML | SOFTWARE ENGINEERING</text>
  <text x="600" y="215" text-anchor="middle" fill="#4b7657"
        font-family="'Courier New', monospace" font-size="12" letter-spacing="3">BUILDING WITH CURIOSITY AND PURPOSE</text>
</svg>"""


def generate_pixel_divider_svg():
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="22" viewBox="0 0 1200 22">
  <path d="M0 9h1200v4H0z" fill="#14351e"/>
  <path d="M28 5h64v4H28zM104 13h42v4h-42zM1110 5h62v4h-62zM1050 13h42v4h-42z" fill="#4ade80"/>
  <path d="M180 5h18v4h-18zM220 13h26v4h-26zM980 5h18v4h-18zM940 13h26v4h-26z" fill="#22c55e"/>
  <path d="M540 5h120v12H540z" fill="#07110b" stroke="#1f6f38"/>
  <path d="M560 9h12v4h-12zM580 9h12v4h-12zM600 9h12v4h-12zM620 9h12v4h-12z" fill="#4ade80"/>
</svg>"""


def generate_profile_overview_svg(data):
    metrics = [
        ("CONTRIBUTIONS", data["total_contributions"]),
        ("STARS", data["total_stars"]),
        ("FORKS", data.get("total_forks", 0)),
    ]
    cards = []
    for index, (label, value) in enumerate(metrics):
        x = 10 + index * 300
        cards.append(f"""
  <g transform="translate({x}, 8)">
    <rect x="4" y="6" width="286" height="100" rx="12" fill="#020804" opacity=".65"/>
    <rect width="286" height="100" rx="12" fill="url(#card)" stroke="#1f6f38"/>
    <path d="M12 1h180l-12 3H12z" fill="#4ade80" opacity=".7"/>
    <text x="143" y="38" text-anchor="middle" class="label">{label}</text>
    <text x="143" y="79" text-anchor="middle" class="value">{value}</text>
  </g>""")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="125" viewBox="0 0 900 125">
  <style>
    .label {{ font: 700 12px 'Courier New', monospace; letter-spacing: 2px; fill: #86efac; }}
    .value {{ font: 700 30px 'Courier New', monospace; fill: #dcfce7; }}
  </style>
  <defs>
    <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#102317"/><stop offset="1" stop-color="#08130b"/>
    </linearGradient>
  </defs>
{"".join(cards)}
</svg>"""


def generate_isometric_contributions_svg(data):
    days = data.get("contribution_days", [])
    blocks = []
    colors = ["#12351e", "#14532d", "#15803d", "#22c55e", "#4ade80"]
    ordered_days = sorted(days, key=lambda day: (day["week"] + day["weekday"], day["week"]))

    for day in ordered_days:
        count = day.get("count", 0)
        level = min(count, len(colors) - 1)
        x = 175 + (day["week"] - day["weekday"]) * 11
        base_y = 76 + (day["week"] + day["weekday"]) * 4.5
        block_height = 2 + min(count, 8) * 2
        top_y = base_y - block_height
        color = colors[level]
        date = escape(day.get("date", ""))
        blocks.append(f"""
  <g>
    <title>{date}: {count} contributions</title>
    <path d="M{x} {top_y}l5-3 10 0-5 3z" fill="#86efac"/>
    <path d="M{x + 10} {top_y}l5-3v{block_height}l-5 3z" fill="#166534"/>
    <path d="M{x} {top_y}h10v{block_height}H{x}z" fill="{color}"/>
  </g>""")

    if not blocks:
        blocks.append('<text x="450" y="230" text-anchor="middle" class="empty">Contribution data will appear after the first successful refresh.</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="430" viewBox="0 0 900 430">
  <style>
    .heading {{ font: 700 18px 'Courier New', monospace; fill: #bbf7d0; letter-spacing: 1px; }}
    .subheading {{ font: 12px 'Courier New', monospace; fill: #6b9c76; }}
    .empty {{ font: 14px 'Courier New', monospace; fill: #86efac; }}
  </style>
  <defs>
    <linearGradient id="floor" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#0d2816"/><stop offset="1" stop-color="#07110b"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="896" height="426" rx="14" fill="url(#floor)" stroke="#1f6f38"/>
  <text x="28" y="38" class="heading">CONTRIBUTION MATRIX // LAST 12 MONTHS</text>
  <text x="28" y="58" class="subheading">{data["total_contributions"]} contributions | each raised block represents a contribution day</text>
  <g opacity=".82">
{"".join(blocks)}
  </g>
  <g transform="translate(330, 390)" class="subheading">
    <text x="0" y="0">LESS</text>
    <rect x="48" y="-12" width="14" height="10" fill="#12351e"/>
    <rect x="68" y="-12" width="14" height="10" fill="#14532d"/>
    <rect x="88" y="-12" width="14" height="10" fill="#15803d"/>
    <rect x="108" y="-12" width="14" height="10" fill="#22c55e"/>
    <rect x="128" y="-12" width="14" height="10" fill="#4ade80"/>
    <text x="152" y="0">MORE</text>
  </g>
</svg>"""


def generate_activity_radar_svg(data):
    metrics = [
        ("Commits", data.get("total_commits", 0)),
        ("Issues", data.get("total_issues", 0)),
        ("Pull requests", data.get("total_prs", 0)),
        ("Reviews", data.get("total_reviews", 0)),
        ("Repositories", data.get("contributed_repos", 0)),
    ]
    center_x, center_y, radius = 450, 235, 132

    def point(angle, scale):
        radians = math.radians(angle)
        return (
            round(center_x + math.cos(radians) * radius * scale, 1),
            round(center_y + math.sin(radians) * radius * scale, 1),
        )

    angles = [-90 + index * 72 for index in range(len(metrics))]
    maximum = max((value for _, value in metrics), default=0) or 1
    grid = []
    for scale in (0.25, 0.5, 0.75, 1):
        points = " ".join(f"{x},{y}" for x, y in (point(angle, scale) for angle in angles))
        grid.append(f'<polygon points="{points}" class="grid"/>')

    data_points = " ".join(
        f"{x},{y}" for x, y in (
            point(angle, value / maximum) for angle, (_, value) in zip(angles, metrics)
        )
    )
    axes = []
    labels = []
    for angle, (label, value) in zip(angles, metrics):
        x, y = point(angle, 1)
        label_x, label_y = point(angle, 1.22)
        axes.append(f'<line x1="{center_x}" y1="{center_y}" x2="{x}" y2="{y}" class="axis"/>')
        labels.append(
            f'<text x="{label_x}" y="{label_y}" text-anchor="middle" class="label">{escape(label)}: {value}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="470" viewBox="0 0 900 470">
  <style>
    .heading {{ font: 700 18px 'Courier New', monospace; fill: #bbf7d0; letter-spacing: 1px; }}
    .grid {{ fill: none; stroke: #1f6f38; stroke-width: 1; }}
    .axis {{ stroke: #27663a; stroke-width: 1; }}
    .shape {{ fill: #22c55e; fill-opacity: .24; stroke: #4ade80; stroke-width: 3; }}
    .label {{ font: 12px 'Courier New', monospace; fill: #a7f3b4; }}
  </style>
  <rect x="2" y="2" width="896" height="466" rx="14" fill="#08130b" stroke="#1f6f38"/>
  <text x="28" y="38" class="heading">ACTIVITY RADAR // LAST 12 MONTHS</text>
{"".join(grid)}
{"".join(axes)}
  <polygon points="{data_points}" class="shape"/>
{"".join(labels)}
</svg>"""


def generate_language_donut_svg(data):
    languages = sorted(data.get("languages", []), key=lambda language: language.get("bytes", 0), reverse=True)
    leading = languages[:4]
    remainder = languages[4:]
    if remainder:
        other_bytes = sum(language.get("bytes", 0) for language in remainder)
        leading.append({"name": "Other", "bytes": other_bytes, "color": "#86efac"})
    total_bytes = sum(language.get("bytes", 0) for language in leading)
    circumference = 2 * math.pi * 91
    circles = []
    legend = []
    offset = 0

    for index, language in enumerate(leading):
        value = language.get("bytes", 0)
        share = value / total_bytes if total_bytes else 0
        segment = circumference * share
        color = language.get("color", "#22c55e")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            color = "#22c55e"
        circles.append(
            f'<circle cx="245" cy="190" r="91" fill="none" stroke="{color}" stroke-width="25" '
            f'stroke-dasharray="{segment:.2f} {circumference - segment:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 245 190)"/>'
        )
        percent = round(share * 100, 1)
        name = escape(textwrap.shorten(language.get("name", "Other"), width=24, placeholder="..."))
        legend.append(
            f'<g transform="translate(500, {104 + index * 42})">'
            f'<circle cx="0" cy="0" r="6" fill="{color}"/>'
            f'<text x="18" y="5" class="label">{name}</text>'
            f'<text x="330" y="5" text-anchor="end" class="value">{percent}%</text></g>'
        )
        offset += segment

    center_label = "TOP LANGUAGES" if total_bytes else "NO DATA"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="390" viewBox="0 0 900 390">
  <style>
    .heading {{ font: 700 18px 'Courier New', monospace; fill: #bbf7d0; letter-spacing: 1px; }}
    .label {{ font: 14px 'Courier New', monospace; fill: #bbf7d0; }}
    .value {{ font: 700 13px 'Courier New', monospace; fill: #4ade80; }}
    .center {{ font: 700 12px 'Courier New', monospace; fill: #86efac; }}
  </style>
  <rect x="2" y="2" width="896" height="386" rx="14" fill="#08130b" stroke="#1f6f38"/>
  <text x="28" y="38" class="heading">LANGUAGE MIX // PUBLIC REPOSITORIES</text>
  <circle cx="245" cy="190" r="91" fill="none" stroke="#12351e" stroke-width="25"/>
{"".join(circles)}
  <text x="245" y="194" text-anchor="middle" class="center">{center_label}</text>
{"".join(legend)}
</svg>"""


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN")

    print(f"Fetching GitHub data for user {USERNAME}...")
    if token:
        data = fetch_live_github_data(token)
    else:
        print("GITHUB_TOKEN not set; generating assets with bundled fallback analytics.")
        data = FALLBACK_DATA

    files_to_generate = {
        "pixel-banner.svg": generate_pixel_banner_svg(),
        "pixel-divider.svg": generate_pixel_divider_svg(),
        "profile-overview.svg": generate_profile_overview_svg(data),
        "contribution-isometric.svg": generate_isometric_contributions_svg(data),
        "activity-radar.svg": generate_activity_radar_svg(data),
        "language-donut.svg": generate_language_donut_svg(data),
        "typing-headline.svg": generate_typing_headline_svg(),
        "github-stats.svg": generate_github_stats_svg(data),
        "streak-stats.svg": generate_streak_stats_svg(data),
        "languages.svg": generate_languages_svg(data),
        "top-repos.svg": generate_top_repos_svg(data),
        "dev-quote.svg": generate_dev_quote_svg(),
        "project-showcase.svg": generate_live_project_showcase_svg(data),
    }

    for filename, content in files_to_generate.items():
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"  ✓ Generated: {filepath} ({len(content)} bytes)")

    print(f"\nAll {len(files_to_generate)} SVG profile analytics assets generated successfully.")


if __name__ == "__main__":
    main()
