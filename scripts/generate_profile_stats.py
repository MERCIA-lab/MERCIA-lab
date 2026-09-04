#!/usr/bin/env python3
"""
generate_profile_stats.py
Queries GitHub GraphQL & REST APIs and generates self-hosted animated SVG cards
with CSS animations, gradients, glassmorphism styling, and responsive layout.
Zero third-party external service dependencies (no Vercel / Heroku).
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

USERNAME = "MERCIA-lab"
DISPLAY_NAME = "Meek Dieu Merci NUKURI"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

# Default / Fallback data from verified live API state
FALLBACK_DATA = {
    "total_stars": 5,
    "total_commits": 54,
    "total_prs": 1,
    "total_issues": 0,
    "contributed_repos": 6,
    "total_contributions": 61,
    "current_streak": 3,
    "longest_streak": 4,
    "streak_range": "Aug 10 - Sep 03",
    "languages": [
        {"name": "TypeScript", "bytes": 331307, "color": "#3178c6", "percent": 51.8},
        {"name": "JavaScript", "bytes": 133083, "color": "#f1e05a", "percent": 20.8},
        {"name": "HTML", "bytes": 86433, "color": "#e34c26", "percent": 13.5},
        {"name": "Java", "bytes": 38044, "color": "#b07219", "percent": 6.0},
        {"name": "Python", "bytes": 33575, "color": "#3572A5", "percent": 5.3},
        {"name": "CSS", "bytes": 31636, "color": "#563d7c", "percent": 2.6},
    ],
    "top_repos": [
        {"name": "Shipping-Tracking-System", "lang": "TypeScript", "color": "#3178c6", "stars": 1, "contribs": 38},
        {"name": "daily-routine-tracker", "lang": "JavaScript", "color": "#f1e05a", "stars": 1, "contribs": 12},
        {"name": "Financial-Advisor-System", "lang": "JavaScript", "color": "#f1e05a", "stars": 1, "contribs": 6},
        {"name": "FreeMCue", "lang": "Python/AI", "color": "#3572A5", "stars": 1, "contribs": 5},
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

    graphql_query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
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
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            name
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
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": graphql_query, "variables": {"login": USERNAME}}).encode(),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            res_data = json.loads(res.read().decode())
            user = res_data.get("data", {}).get("user")
            if user:
                cc = user.get("contributionsCollection", {})
                data["total_commits"] = cc.get("totalCommitContributions", data["total_commits"])
                data["total_prs"] = cc.get("totalPullRequestContributions", data["total_prs"])
                data["total_issues"] = cc.get("totalIssueContributions", data["total_issues"])
                data["contributed_repos"] = cc.get("totalRepositoryContributions", data["contributed_repos"])
                data["total_contributions"] = cc.get("contributionCalendar", {}).get("totalContributions", data["total_contributions"])

                weeks = cc.get("contributionCalendar", {}).get("weeks", [])
                days = [d for w in weeks for d in w.get("contributionDays", [])]
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
                data["current_streak"] = max(cur_streak, 1)
                data["longest_streak"] = max(max_streak, data["current_streak"])

                repos = user.get("repositories", {}).get("nodes", [])
                total_stars = sum(r.get("stargazerCount", 0) for r in repos)
                data["total_stars"] = max(total_stars, data["total_stars"])

                lang_map = {}
                for r in repos:
                    for edge in r.get("languages", {}).get("edges", []):
                        lname = edge.get("node", {}).get("name")
                        lcolor = edge.get("node", {}).get("color") or "#8b949e"
                        lsize = edge.get("size", 0)
                        if lname not in lang_map:
                            lang_map[lname] = {"name": lname, "bytes": 0, "color": lcolor}
                        lang_map[lname]["bytes"] += lsize

                if lang_map:
                    tot_bytes = sum(v["bytes"] for v in lang_map.values())
                    sorted_langs = sorted(lang_map.values(), key=lambda x: x["bytes"], reverse=True)[:6]
                    for l in sorted_langs:
                        l["percent"] = round((l["bytes"] / tot_bytes) * 100, 1) if tot_bytes > 0 else 0
                    data["languages"] = sorted_langs
    except Exception as err:
        print(f"Note: Using cached fallback analytics ({err})", file=sys.stderr)

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
  <text x="425" y="38" class="headline-text">Meek Dieu Merci here 🔥 !</text>
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
    <text x="0" y="153" class="stat-sub">🔥 Active streak</text>
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

    for idx, r in enumerate(repos):
        badge_color = "#38bdf8" if idx == 0 else "#58a6ff"
        rows.append(f"""
    <g transform="translate(25, {y_pos})">
      <!-- Repo Icon -->
      <path fill="#8b949e" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1h-8a1 1 0 00-1 1v6.708A2.486 2.486 0 014.5 9h8V1.5z"/>
      <!-- Repo Name -->
      <text x="22" y="12" class="repo-name">{r['name']}</text>
      <!-- Commits/Contrib Badge -->
      <rect x="390" y="-2" width="50" height="20" rx="10" fill="rgba(56, 189, 248, 0.12)" stroke="#38bdf8" stroke-width="0.8"/>
      <text x="415" y="12" class="repo-count">{r['contribs']}</text>
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
  <text x="25" y="32" class="header-title">{USERNAME}'s GitHub Contribution Stats</text>
  <text x="47" y="52" class="header-col">Repository</text>
  <text x="400" y="52" class="header-col">Commits</text>
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
    """Generates high-fidelity project showcase cards for flagship repositories."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="900" height="220" viewBox="0 0 900 220" fill="none">
  <style>
    .card {
      fill: #0d1117;
      stroke: #30363d;
      stroke-width: 1.5;
      rx: 12px;
    }
    .card-title {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 16px;
      font-weight: 700;
      fill: #38bdf8;
    }
    .card-desc {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 12px;
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
    <rect width="435" height="220" class="card" />
    <circle cx="28" cy="30" r="4" class="status-dot" />
    <text x="40" y="34" class="card-title">Shipping-Tracking-System</text>

    <!-- Tag -->
    <rect x="340" y="18" width="70" height="20" rx="10" fill="rgba(56, 189, 248, 0.15)" stroke="#38bdf8" stroke-width="0.8"/>
    <text x="375" y="32" fill="#38bdf8" text-anchor="middle" class="badge">FLAGSHIP</text>

    <!-- Description -->
    <text x="28" y="70" class="card-desc">Cloud-based enterprise logistics ecosystem covering</text>
    <text x="28" y="90" class="card-desc">parcel dispatch, cargo freight, dynamic warehouse</text>
    <text x="28" y="110" class="card-desc">queues, and real-time WebSocket fleet monitoring.</text>

    <!-- Tech Badges -->
    <rect x="28" y="135" width="75" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="65" y="150" fill="#3178c6" text-anchor="middle" class="badge">TypeScript</text>

    <rect x="110" y="135" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="142" y="150" fill="#e0234e" text-anchor="middle" class="badge">NestJS</text>

    <rect x="182" y="135" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="214" y="150" fill="#38bdf8" text-anchor="middle" class="badge">Next.js</text>

    <rect x="254" y="135" width="80" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="294" y="150" fill="#336791" text-anchor="middle" class="badge">PostgreSQL</text>

    <!-- Stats footer -->
    <path fill="#8b949e" transform="translate(28, 180)" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
    <text x="48" y="192" fill="#8b949e" class="badge">1 Star</text>

    <path fill="#8b949e" transform="translate(100, 180)" d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5A2.25 2.25 0 006.5 6.25h-.75a.75.75 0 01-.75-.75v-.128z"/>
    <text x="120" y="192" fill="#8b949e" class="badge">1 Fork</text>

    <text x="405" y="192" fill="#58a6ff" text-anchor="end" class="badge">Public • Production</text>
  </g>

  <!-- Card 2: FreeMCue (macOS AI Copilot) -->
  <g transform="translate(465, 0)">
    <rect width="435" height="220" class="card" />
    <circle cx="28" cy="30" r="4" class="status-dot" />
    <text x="40" y="34" class="card-title">FreeMCue</text>

    <!-- Tag -->
    <rect x="330" y="18" width="80" height="20" rx="10" fill="rgba(168, 85, 247, 0.15)" stroke="#a855f7" stroke-width="0.8"/>
    <text x="370" y="32" fill="#a855f7" text-anchor="middle" class="badge">AI COPILOT</text>

    <!-- Description -->
    <text x="28" y="70" class="card-desc">Open-source macOS AI assistant that floats over your screen,</text>
    <text x="28" y="90" class="card-desc">observes meeting audio/video context, and remains fully</text>
    <text x="28" y="110" class="card-desc">invisible from screen shares. Bring-your-own-API-key.</text>

    <!-- Tech Badges -->
    <rect x="28" y="135" width="70" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="63" y="150" fill="#3572A5" text-anchor="middle" class="badge">Python</text>

    <rect x="105" y="135" width="60" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="135" y="150" fill="#f1e05a" text-anchor="middle" class="badge">AI / ML</text>

    <rect x="172" y="135" width="65" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="204" y="150" fill="#a855f7" text-anchor="middle" class="badge">macOS</text>

    <rect x="244" y="135" width="75" height="22" rx="6" fill="#161b22" stroke="#30363d"/>
    <text x="281" y="150" fill="#22c55e" text-anchor="middle" class="badge">Real-Time</text>

    <!-- Stats footer -->
    <path fill="#8b949e" transform="translate(28, 180)" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
    <text x="48" y="192" fill="#8b949e" class="badge">Open Source</text>

    <text x="405" y="192" fill="#58a6ff" text-anchor="end" class="badge">Public • Active</text>
  </g>
</svg>"""


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN")

    print(f"Fetching GitHub data for user {USERNAME}...")
    data = fetch_live_github_data(token) if token else FALLBACK_DATA

    files_to_generate = {
        "typing-headline.svg": generate_typing_headline_svg(),
        "github-stats.svg": generate_github_stats_svg(data),
        "streak-stats.svg": generate_streak_stats_svg(data),
        "languages.svg": generate_languages_svg(data),
        "top-repos.svg": generate_top_repos_svg(data),
        "dev-quote.svg": generate_dev_quote_svg(),
        "project-showcase.svg": generate_project_showcase_svg(),
    }

    for filename, content in files_to_generate.items():
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"  ✓ Generated: {filepath} ({len(content)} bytes)")

    print(f"\nAll {len(files_to_generate)} SVG profile analytics assets generated successfully.")


if __name__ == "__main__":
    main()
