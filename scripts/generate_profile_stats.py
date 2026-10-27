#!/usr/bin/env python3
"""Build every local profile graphic and render README.md from profile.yml."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import os
import random
import re
import sys
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

import requests
from jinja2 import Environment, FileSystemLoader, StrictUndefined
try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
GENERATED = ASSETS / "generated"
ICONS = ASSETS / "icons"
CACHE = GENERATED / "profile-data.json"
USERNAME = "MERCIA-lab"
API = "https://api.github.com"
PALETTE = {
    "bg": "#0d1117", "card": "#12161d", "border": "#1f2630",
    "text": "#c9d1d9", "heading": "#e6edf3", "green": "#2ea043",
    "bright": "#3fb950", "deep": "#1a7f37", "beige": "#d9d2c5",
    "muted": "#6e7681", "blue": "#8bb9d8", "white": "#f0f3f6",
}

# Compact 5x7 bitmap font. SVG text is rendered from rectangles, so images need
# no remote font, installed font, script, or browser font support.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
}

SKILL_META = {
    "HTML": ("html", "#e34f26"), "CSS": ("css", "#1572b6"), "JS": ("js", "#f1e05a"),
    "TS": ("ts", "#3178c6"), "React": ("react", "#61dafb"), "Next.js": ("N", "#c9d1d9"),
    "Tailwind": ("TW", "#38bdf8"), "Node.js": ("node", "#339933"), "Express": ("EX", "#c9d1d9"),
    "NestJS": ("N", "#e0234e"), "FastAPI": ("API", "#009688"), "C": ("C", "#659ad2"),
    "C++": ("C++", "#00599c"), "Python": ("PY", "#3776ab"), "PyTorch": ("PT", "#ee4c2c"),
    "TensorFlow": ("TF", "#ff6f00"), "OpenCV": ("CV", "#5c3ee8"), "PostgreSQL": ("PG", "#4169e1"),
    "MySQL": ("SQL", "#4479a1"), "MongoDB": ("MDB", "#47a248"), "Redis": ("R", "#dc382d"),
    "Docker": ("D", "#2496ed"), "AWS": ("AWS", "#ff9900"), "Git": ("G", "#f05032"),
    "GitHub": ("GH", "#c9d1d9"), "Linux": ("LX", "#fcc624"), "Bash": ("$_", "#4eaa25"),
    "VS Code": ("<>" , "#007acc"), "Figma": ("F", "#f24e1e"),
}
SKILL_ICON = {
    "HTML": "html5", "CSS": "css", "JS": "javascript", "TS": "typescript",
    "React": "react", "Next.js": "nextdotjs", "Tailwind": "tailwindcss",
    "Node.js": "nodedotjs", "Express": "express", "NestJS": "nestjs",
    "FastAPI": "fastapi", "C": "c", "C++": "cplusplus", "Python": "python",
    "PyTorch": "pytorch", "TensorFlow": "tensorflow", "OpenCV": "opencv",
    "PostgreSQL": "postgresql", "MySQL": "mysql", "MongoDB": "mongodb",
    "Redis": "redis", "Docker": "docker", "AWS": "amazonwebservices",
    "Git": "git", "GitHub": "github", "Linux": "linux", "Bash": "gnubash",
    "VS Code": "vscode", "Figma": "figma",
}
SOCIALS = [
    ("GitHub", "github", "#c9d1d9"), ("LinkedIn", "linkedin", "#0a66c2"),
    ("X (Twitter)", "x", "#e6edf3"), ("Gmail", "gmail", "#ea4335"),
    ("Portfolio", "portfolio", "#3fb950"),
]


def write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = content.rstrip() + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != value:
        path.write_text(value, encoding="utf-8", newline="\n")


def bitmap(text: str, x: int, y: int, cell: int, color: str, gap: int = 1) -> str:
    parts = []
    cursor = x
    for char in text.upper():
        if char == " ":
            cursor += cell * 4
            continue
        glyph = FONT.get(char)
        if glyph:
            for row, bits in enumerate(glyph):
                for col, bit in enumerate(bits):
                    if bit == "1":
                        parts.append(f'<rect x="{cursor + col * cell}" y="{y + row * cell}" width="{cell}" height="{cell}" fill="{color}"/>')
            cursor += cell * (5 + gap)
    return "".join(parts)


def iso_week_seed() -> tuple[int, str]:
    today = date.today()
    iso = today.isocalendar()
    seed = iso.year * 100 + iso.week
    return seed, f"{iso.year}-W{iso.week:02d}"


def pixel_mosaic(seed: int, x: int, y: int, cols: int, rows: int, cell: int) -> str:
    rng = random.Random(seed)
    palette = ["#1a7f37", "#2ea043", "#3fb950", "#7ee787", "#d9d2c5", "#c9d1d9", "#30363d"]
    weights = [24, 24, 20, 12, 9, 5, 6]
    parts = []
    for row in range(rows):
        for col in range(cols):
            if rng.random() < .11:
                continue
            color = rng.choices(palette, weights=weights, k=1)[0]
            parts.append(f'<rect x="{x + col * cell}" y="{y + row * cell}" width="{cell - 1}" height="{cell - 1}" fill="{color}" opacity="{rng.choice((".52", ".72", ".9", "1"))}"/>')
    return "".join(parts)


def banner_svg(name: str, handle: str, tagline: str, seed: int, light: bool = False) -> str:
    bg = "#f6f8fa" if light else PALETTE["bg"]
    card = "#ffffff" if light else PALETTE["card"]
    fg = "#18202a" if light else PALETTE["heading"]
    muted = "#57606a" if light else PALETTE["muted"]
    # Standard profile text, pixel-rendered name, pixel mosaic that changes by ISO week.
    title_a = name.upper().replace(" NUKURI", "")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="200" viewBox="0 0 900 200" role="img" aria-label="{escape(name)} — {escape(tagline)}">
<rect x=".5" y=".5" width="899" height="199" rx="8" fill="{card}" stroke="{PALETTE['border']}"/>
<text x="24" y="24" fill="{muted}" font-family="monospace" font-size="11">{escape(handle)} / README.md</text>
{bitmap(title_a, 25, 42, 4, fg)}
{bitmap('NUKURI', 25, 79, 4, fg)}
{pixel_mosaic(seed, 25, 119, 100, 6, 8)}
<rect x="25" y="172" width="850" height="1" fill="{PALETTE['border']}"/>
<text x="874" y="191" fill="{muted}" text-anchor="end" font-family="monospace" font-size="10">{escape(tagline)}</text>
</svg>'''


def glitch_svg(seed: int, width: int = 470, height: int = 20, start_x: int = 0) -> str:
    rng = random.Random(seed)
    colors = [PALETTE["green"], PALETTE["bright"], PALETTE["beige"], PALETTE["blue"], PALETTE["muted"]]
    rects = []
    for _ in range(36):
        x = rng.randint(start_x, width - 5)
        y = rng.choice((3, 7, 11, 15))
        w = rng.choice((4, 6, 8, 12, 16, 22))
        color = rng.choice(colors)
        opacity = max(.16, 1 - x / (width * 1.25))
        rects.append(f'<rect x="{x}" y="{y}" width="{w}" height="3" fill="{color}" opacity="{opacity:.2f}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><path d="M{start_x} 10H{width}" stroke="{PALETTE["border"]}"/>{"".join(rects)}</svg>'


def section_header_svg(text: str, seed: int) -> str:
    width, height = 900, 24
    heading_width = (len(text) * 14) + 12
    divider = glitch_svg(seed, width=width, height=height, start_x=heading_width + 18)
    root = ET.fromstring(divider)
    details = "".join(ET.tostring(child, encoding="unicode") for child in root)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(text)}">{bitmap(text, 3, 3, 2, PALETTE["heading"], 1)}{details}</svg>'


def heading_svg(text: str) -> str:
    width = max(150, len(text) * 15 + 16)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="24" viewBox="0 0 {width} 24" role="img" aria-label="{escape(text)}">{bitmap(text, 2, 2, 2, PALETTE["heading"], 1)}</svg>'


def icon_svg(label: str, color: str, initials: str = "") -> str:
    initials = initials or label[:3].upper()
    safe = escape(initials)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" role="img" aria-label="{escape(label)}">
<rect x="1" y="1" width="62" height="62" rx="5" fill="#0f141b" stroke="#1f2630"/>
<rect x="6" y="6" width="52" height="52" fill="{color}" opacity=".13"/>
<path d="M8 12h7M49 52h7" stroke="{color}" stroke-width="3"/>
<text x="32" y="38" text-anchor="middle" fill="{color}" font-family="monospace" font-size="{18 if len(initials) < 4 else 13}" font-weight="bold">{safe}</text>
</svg>'''


def social_icon_svg(label: str, key: str, color: str) -> str:
    if key == "linkedin":
        mark = '<path fill="#0a66c2" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.35V9h3.414v1.561h.049c.476-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 11.003-4.125 2.062 2.062 0 01-.003 4.125zM6.817 20.452H3.852V9h2.965v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.225 0z"/>'
    else:
        vendor_slug = {"github": "github", "x": "x", "gmail": "gmail"}.get(key, "")
        vendor = ICONS / "vendor" / f"{vendor_slug}.svg" if vendor_slug else None
        mark = ""
        if vendor and vendor.exists():
            root = ET.parse(vendor).getroot()
            viewbox = escape(root.attrib.get("viewBox", "0 0 24 24"))
            fill = escape(color if key in ("github", "x") else root.attrib.get("fill", color))
            children = [ET.tostring(child, encoding="unicode") for child in root
                        if child.tag.rsplit("}", 1)[-1].lower() != "title"]
            mark = f'<svg x="16" y="16" width="32" height="32" viewBox="{viewbox}" fill="{fill}" preserveAspectRatio="xMidYMid meet">{"".join(children)}</svg>'
        if not mark:
            initials = {"github": "GH", "x": "X", "gmail": "M"}.get(key, label[:2])
            mark = f'<text x="32" y="39" text-anchor="middle" fill="{color}" font-family="monospace" font-size="20" font-weight="bold">{escape(initials)}</text>'
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" role="img" aria-label="{escape(label)}"><rect x="1" y="1" width="62" height="62" rx="5" fill="#0f141b" stroke="#1f2630"/>{mark}</svg>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" role="img" aria-label="{escape(label)}"><rect x="1" y="1" width="62" height="62" rx="5" fill="#0f141b" stroke="#1f2630"/><svg x="16" y="16" width="32" height="32" viewBox="0 0 24 24">{mark}</svg></svg>'


def skill_icon_svg(label: str, color: str, initials: str = "") -> str:
    initials = initials or label[:3].upper()
    size = 10 if len(initials) > 3 else 13
    slug = SKILL_ICON.get(label, "")
    vendor = ICONS / "vendor" / f"{slug}.svg" if slug else None
    logo = ""
    if label == "VS Code":
        logo = '<path fill="#007acc" d="M17.2 2.1 9.3 9.5 4.2 5.6 2 6.8v10.4l2.2 1.3 5.1-3.9 7.9 7.4 4.8-2.4V4.5L17.2 2.1ZM4.6 7.1 8 12l-3.4 4.9V7.1ZM9.2 12l8.4-6.5v13L9.2 12Z"/>'
    elif vendor and vendor.exists():
        try:
            root = ET.parse(vendor).getroot()
            viewbox = root.attrib.get("viewBox", "0 0 24 24")
            source_color = root.attrib.get("fill", color)
            parts = []
            for child in root:
                if child.tag.rsplit("}", 1)[-1].lower() == "title":
                    continue
                part = ET.tostring(child, encoding="unicode")
                if label == "AWS":
                    part = part.replace("#252f3e", "#c9d1d9").replace("#232f3e", "#c9d1d9")
                parts.append(part)
            if parts:
                logo = f'<svg x="4" y="4" width="32" height="32" viewBox="{escape(viewbox)}" fill="{escape(source_color)}" preserveAspectRatio="xMidYMid meet">{"".join(parts)}</svg>'
        except ET.ParseError as exc:
            raise ValueError(f"Invalid local skill icon {vendor}: {exc}") from exc
    if not logo:
        logo = f'<text x="20" y="25" text-anchor="middle" fill="{color}" font-family="monospace" font-size="{size}" font-weight="bold">{escape(initials)}</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="40" height="56" viewBox="0 0 40 56" role="img" aria-label="{escape(label)}">
<rect x=".5" y=".5" width="39" height="39" rx="3" fill="#0f141b" stroke="#1f2630"/>
<rect x="4" y="4" width="32" height="32" fill="{color}" opacity=".15"/>
{logo}
<text x="20" y="51" text-anchor="middle" fill="{PALETTE['text']}" font-family="monospace" font-size="5">{escape(label[:11])}</text>
</svg>'''


def pixel_divider(seed: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="16" viewBox="0 0 900 16"><path d="M0 8H900" stroke="{PALETTE["border"]}"/>{pixel_mosaic(seed, 560, 1, 42, 2, 8)}</svg>'


def fallback_data() -> dict:
    return {"contributions": 0, "commits": 0, "issues": 0, "pulls": 0,
            "reviews": 0, "repos": 0, "stars": 0, "forks": 0,
            "followers": 0, "following": 0,
            "activity_available": False, "radar_available": False,
            "repository_data_available": False,
            "user_data_available": False,
            "days": [], "languages": [
                {"name": "TypeScript", "bytes": 331307, "color": "#3178c6", "percent": 51.8},
                {"name": "JavaScript", "bytes": 133083, "color": "#f1e05a", "percent": 20.8},
                {"name": "HTML", "bytes": 86433, "color": "#e34c26", "percent": 13.5},
                {"name": "Java", "bytes": 38044, "color": "#b07219", "percent": 6.0},
                {"name": "Python", "bytes": 33575, "color": "#3572a5", "percent": 5.3},
                {"name": "CSS", "bytes": 31636, "color": "#563d7c", "percent": 2.6},
            ], "selected_repos": []}


def fetch_public_contribution_calendar(session: requests.Session, data: dict) -> bool:
    """Use GitHub's public profile calendar when GraphQL is rate-limited."""
    try:
        response = session.get(
            f"https://github.com/users/{USERNAME}/contributions",
            headers={"User-Agent": "MERCIA-lab-profile-builder"}, timeout=25,
        )
        response.raise_for_status()
        markup = response.text
        cell_pattern = re.compile(
            r'<td\b(?=[^>]*data-date="([^"]+)")(?=[^>]*data-level="(\d+)")[^>]*>\s*</td>\s*<tool-tip\b[^>]*>(.*?)</tool-tip>',
            re.IGNORECASE | re.DOTALL,
        )
        days = []
        for day, _level, tooltip in cell_pattern.findall(markup):
            text = html.unescape(re.sub(r"<[^>]+>", " ", tooltip)).strip()
            count_match = re.search(r"(\d+)\s+contributions?", text, re.IGNORECASE)
            count = int(count_match.group(1)) if count_match else 0
            days.append((day, count))
        if not days:
            raise ValueError("GitHub's contribution calendar contained no daily cells")
        days.sort(key=lambda item: item[0])
        data["days"] = [count for _, count in days]
        heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", markup, re.IGNORECASE | re.DOTALL)
        heading_text = html.unescape(re.sub(r"<[^>]+>", " ", heading.group(1))) if heading else ""
        total_match = re.search(r"(\d+)\s+contributions?", heading_text, re.IGNORECASE)
        data["contributions"] = int(total_match.group(1)) if total_match else sum(data["days"])
        data["activity_available"] = True
        data["radar_available"] = False
        return True
    except (requests.RequestException, ValueError) as exc:
        print(f"GitHub public contribution calendar unavailable: {exc}", file=sys.stderr)
        return False


def fetch_profile_data(profile: dict, cached: dict, offline: bool = False) -> dict:
    data = {**fallback_data(), **cached}
    if offline:
        if not data["selected_repos"]:
            data["selected_repos"] = [
                dict(item, description=item["fallback"], language="—", stars="—",
                     url=f"https://github.com/{USERNAME}/{item['name']}")
                for item in profile["selected_repos"]
            ]
        return data
    session = requests.Session()
    session.headers.update({"Accept": "application/vnd.github+json", "User-Agent": "MERCIA-lab-profile-builder"})
    token = os.getenv("GITHUB_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    try:
        response = session.get(f"{API}/users/{USERNAME}/repos", params={"per_page": 100, "type": "owner"}, timeout=20)
        response.raise_for_status()
        repositories = response.json()
        user_response = session.get(f"{API}/users/{USERNAME}", timeout=20)
        user_response.raise_for_status()
        user = user_response.json()
        data["followers"] = user.get("followers", 0)
        data["following"] = user.get("following", 0)
        data["user_data_available"] = True
        data["stars"] = sum(repo.get("stargazers_count", 0) for repo in repositories)
        data["forks"] = sum(repo.get("forks_count", 0) for repo in repositories)
        data["repository_data_available"] = True
        language_totals: dict[str, dict] = {}
        for repo in repositories:
            repo_languages = {}
            try:
                lang_response = session.get(repo.get("languages_url") or f"{API}/repos/{USERNAME}/{repo['name']}/languages", timeout=20)
                lang_response.raise_for_status()
                repo_languages = lang_response.json()
            except requests.RequestException:
                primary = repo.get("language")
                if primary:
                    repo_languages = {primary: max(1, repo.get("size", 1))}
            for lang, size in repo_languages.items():
                entry = language_totals.setdefault(lang, {"name": lang, "bytes": 0, "color": language_color(lang)})
                entry["bytes"] += size
        total = sum(item["bytes"] for item in language_totals.values()) or 1
        data["languages"] = sorted(
            [dict(item, percent=100 * item["bytes"] / total) for item in language_totals.values()],
            key=lambda item: item["bytes"], reverse=True,
        )[:5]
        repo_by_name = {repo["name"].lower(): repo for repo in repositories}
        for item in profile["selected_repos"]:
            repo = repo_by_name.get(item["name"].lower())
            if repo is None:
                repo_resp = session.get(f"{API}/repos/{USERNAME}/{item['name']}", timeout=20)
                if repo_resp.status_code == 200:
                    repo = repo_resp.json()
            data["selected_repos"].append({
                **item,
                "description": (repo or {}).get("description") or item["fallback"],
                "language": (repo or {}).get("language") or "—",
                "stars": (repo or {}).get("stargazers_count", 0),
                "url": (repo or {}).get("html_url") or f"https://github.com/{USERNAME}/{item['name']}",
            })
    except requests.RequestException as exc:
        print(f"GitHub repositories API unavailable; using the saved public-data cache: {exc}", file=sys.stderr)

    try:
        query = """query($login:String!){user(login:$login){contributionsCollection{
          totalCommitContributions totalPullRequestContributions totalIssueContributions
          totalPullRequestReviewContributions totalRepositoryContributions
          contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}
        }}}"""
        response = session.post(f"{API}/graphql", json={"query": query, "variables": {"login": USERNAME}}, timeout=20)
        response.raise_for_status()
        result = response.json()
        if result.get("errors"):
            raise requests.HTTPError("GitHub GraphQL returned: " + "; ".join(error.get("message", "unknown error") for error in result["errors"]))
        collection = result.get("data", {}).get("user", {}).get("contributionsCollection", {})
        data["commits"] = collection.get("totalCommitContributions", 0)
        data["pulls"] = collection.get("totalPullRequestContributions", 0)
        data["issues"] = collection.get("totalIssueContributions", 0)
        data["reviews"] = collection.get("totalPullRequestReviewContributions", 0)
        data["repos"] = collection.get("totalRepositoryContributions", 0)
        data["activity_available"] = True
        data["radar_available"] = True
        calendar = collection.get("contributionCalendar", {})
        data["contributions"] = calendar.get("totalContributions", 0)
        data["days"] = [day.get("contributionCount", 0)
                         for week in calendar.get("weeks", [])
                         for day in week.get("contributionDays", [])]
    except requests.RequestException as exc:
        print(f"GitHub GraphQL unavailable; falling back to the public calendar: {exc}", file=sys.stderr)
        fetch_public_contribution_calendar(session, data)
    if not data["selected_repos"]:
        data["selected_repos"] = [dict(item, description=item["fallback"], language="—", stars="—",
                                       url=f"https://github.com/{USERNAME}/{item['name']}")
                                  for item in profile["selected_repos"]]
    return data


def language_color(language: str) -> str:
    return {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572a5",
            "HTML": "#e34c26", "CSS": "#563d7c", "Java": "#b07219", "C#": "#178600",
            "C++": "#f34b7d", "Go": "#00add8", "Rust": "#dea584"}.get(language, "#8b949e")


def radar_panel(data: dict, cx: int, cy: int, radius: int) -> str:
    labels = [("Commit", data["commits"]), ("Issue", data["issues"]), ("PullReq", data["pulls"]),
              ("Review", data["reviews"]), ("Repo", data["repos"])]
    peak = max([value for _, value in labels] + [1])
    points = []
    result = []
    for ring in (0.25, 0.5, 0.75, 1):
        coords = []
        for index in range(5):
            angle = -math.pi / 2 + index * 2 * math.pi / 5
            coords.append(f"{cx + math.cos(angle)*radius*ring:.1f},{cy + math.sin(angle)*radius*ring:.1f}")
        result.append(f'<polygon points="{" ".join(coords)}" fill="none" stroke="#29313a"/>')
    for index, (name, value) in enumerate(labels):
        angle = -math.pi / 2 + index * 2 * math.pi / 5
        length = radius * (0.12 + 0.88 * value / peak)
        px, py = cx + math.cos(angle) * length, cy + math.sin(angle) * length
        points.append(f"{px:.1f},{py:.1f}")
        lx, ly = cx + math.cos(angle) * (radius + 20), cy + math.sin(angle) * (radius + 20)
        result.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + math.cos(angle)*radius:.1f}" y2="{cy + math.sin(angle)*radius:.1f}" stroke="#29313a"/>')
        result.append(f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{PALETTE["muted"]}" font-family="monospace" font-size="10" text-anchor="middle">{name}</text>')
    result.append(f'<polygon points="{" ".join(points)}" fill="#3fb950" fill-opacity=".35" stroke="#3fb950" stroke-width="2"/>')
    return "".join(result)


def donut(data: dict, cx: int, cy: int, radius: int) -> str:
    langs = data.get("languages", []) or [{"name": "No data", "percent": 100, "color": "#30363d"}]
    total = sum(lang["percent"] for lang in langs) or 100
    circumference = 2 * math.pi * radius
    offset = 0.0
    pieces = [f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#1f2630" stroke-width="22"/>']
    for lang in langs:
        part = circumference * lang["percent"] / total
        pieces.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{lang["color"]}" stroke-width="22" stroke-dasharray="{part:.2f} {circumference-part:.2f}" stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>')
        offset += part
    for index, lang in enumerate(langs):
        y = cy - 42 + index * 18
        pieces.append(f'<rect x="{cx + 44}" y="{y-9}" width="8" height="8" fill="{lang["color"]}"/><text x="{cx + 58}" y="{y}" fill="{PALETTE["text"]}" font-family="monospace" font-size="10">{escape(lang["name"])} {lang["percent"]:.0f}%</text>')
    return "".join(pieces)


def stats_panel(data: dict, light: bool = False) -> str:
    bg = "#f6f8fa" if light else PALETTE["bg"]
    card = "#ffffff" if light else PALETTE["card"]
    fg = "#24292f" if light else PALETTE["heading"]
    muted = "#57606a" if light else PALETTE["muted"]
    # Draw a contribution calendar as an isometric plane with deterministic heights.
    days = data.get("days", [])[-371:]
    if len(days) < 371:
        days = [0] * (371 - len(days)) + days
    origin_x, origin_y = 110, 82
    bars = []
    cells = []
    colors = ("#1a7f37", "#2ea043", "#3fb950", "#7ee787")
    for index, count in enumerate(days):
        week, weekday = divmod(index, 7)
        x = origin_x + week * 15 - weekday * 15
        y = origin_y + week * 4.5 + weekday * 4.5
        # Isometric calendar tiles form a long, shallow contribution ladder.
        cells.append(f'<polygon points="{x:.1f},{y:.1f} {x+7.5:.1f},{y+4.5:.1f} {x:.1f},{y+9:.1f} {x-7.5:.1f},{y+4.5:.1f}" fill="#202833" stroke="#303943" stroke-width=".45"/>')
        if count:
            height = min(28, 4 + int(math.log2(count + 1) * 5))
            color = colors[min(3, int(math.log2(count + 1) / 2))]
            bars.append(f'<polygon points="{x:.1f},{y-height:.1f} {x+7.5:.1f},{y+4.5-height:.1f} {x:.1f},{y+9-height:.1f} {x-7.5:.1f},{y+4.5-height:.1f}" fill="{color}" stroke="#0d1117" stroke-width=".5"/>')
            bars.append(f'<polygon points="{x+7.5:.1f},{y+4.5-height:.1f} {x+7.5:.1f},{y+4.5:.1f} {x:.1f},{y+9:.1f} {x:.1f},{y+9-height:.1f}" fill="#1a7f37"/>')
            bars.append(f'<polygon points="{x-7.5:.1f},{y+4.5-height:.1f} {x:.1f},{y+9-height:.1f} {x:.1f},{y+9:.1f} {x-7.5:.1f},{y+4.5:.1f}" fill="#14532d"/>')
    iso = date.today().isocalendar()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="480" viewBox="0 0 900 480" role="img" aria-label="GitHub contributions, languages, and activity stats">
<rect x="1" y="1" width="898" height="478" rx="9" fill="{card}" stroke="{PALETTE['border']}"/>
<text x="24" y="30" fill="{fg}" font-family="monospace" font-size="12">{USERNAME} / DAILY CONTRIBUTION LADDER</text>
<text x="875" y="30" fill="{muted}" text-anchor="end" font-family="monospace" font-size="10">UPDATED {iso.year}-W{iso.week:02d}</text>
<path d="M18 42H882" stroke="{PALETTE['border']}"/>
{"".join(cells)}{"".join(bars)}
<text x="610" y="68" fill="{muted}" font-family="monospace" font-size="10">{"ACTIVITY RADAR" if data['radar_available'] else "RADAR / TYPE DATA PENDING"}</text>
{radar_panel(data, 720, 160, 62)}
<text x="30" y="340" fill="{muted}" font-family="monospace" font-size="10">LANGUAGE MIX</text>
{donut(data, 78, 402, 28)}
<path d="M24 440H876" stroke="{PALETTE['border']}"/>
<text x="45" y="464" fill="{PALETTE['bright']}" font-family="monospace" font-size="12">{data['contributions'] if data['activity_available'] else "—"}</text><text x="90" y="464" fill="{muted}" font-family="monospace" font-size="10">CONTRIBUTIONS</text>
<text x="390" y="464" fill="{PALETTE['beige']}" font-family="monospace" font-size="12">{data['stars'] if data['repository_data_available'] else "—"}</text><text x="420" y="464" fill="{muted}" font-family="monospace" font-size="10">STARS</text>
<text x="650" y="464" fill="{PALETTE['blue']}" font-family="monospace" font-size="12">{data['forks'] if data['repository_data_available'] else "—"}</text><text x="680" y="464" fill="{muted}" font-family="monospace" font-size="10">FORKS</text>
</svg>'''


def project_showcase(data: dict, width: int) -> str:
    item = data["selected_repos"][0]
    height = 192 if width < 500 else 150
    left = 20 if width < 500 else 30
    usable = width - left * 2
    chars = max(30, int(usable / (6.2 if width < 500 else 7.2)))
    lines, current = [], ""
    for word in item["description"].split():
        if current and len(current) + len(word) + 1 > chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    description = "".join(f'<text x="{left}" y="{88 + i * 17}" fill="#9da7b3" font-family="monospace" font-size="{10 if width < 500 else 12}">{escape(line)}</text>' for i, line in enumerate(lines[:3]))
    title_size = 14 if width < 500 else 19
    meta_y = 132 if width < 500 else 100
    language = str(item["language"] or "").strip()
    stars = str(item["stars"] or "").strip()
    language = "N/A" if not language.isascii() or language in ("-", "") else language
    stars = "N/A" if not stars.isascii() or stars in ("-", "") else stars
    cta_y = meta_y + 50 if width < 500 else meta_y + 34
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Featured project: {escape(item["name"])}"><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="8" fill="#12161d" stroke="#303943"/><text x="{left}" y="29" fill="#8b949e" font-family="monospace" font-size="10">FEATURED PROJECT / 01</text><text x="{left}" y="58" fill="#3fb950" font-family="monospace" font-size="{title_size}">{escape(item["name"])}</text>{description}<path d="M{left} {meta_y+13}H{width-left}" stroke="#303943"/><text x="{left}" y="{meta_y+34}" fill="#d9d2c5" font-family="monospace" font-size="10">{escape(language)}  |  STARS {escape(stars)}</text><text x="{left if width < 500 else width-left}" y="{cta_y}" fill="#58a6ff" text-anchor="{'start' if width < 500 else 'end'}" font-family="monospace" font-size="10">OPEN REPOSITORY</text></svg>'

def skills_grid_svg(profile: dict, columns: int, width: int) -> str:
    names = [name for row in profile["skills"] for name in row]
    rows = max(1, math.ceil(len(names) / columns))
    cell_width = width / columns
    cell_height = 78
    cells = []
    for index, name in enumerate(names):
        col, row = index % columns, index // columns
        x, y = col * cell_width, row * cell_height
        cell_fill = "#0f141b"
        cells.append(f'<rect x="{x:.2f}" y="{y}" width="{cell_width - 1:.2f}" height="{cell_height - 1}" fill="{cell_fill}" stroke="{PALETTE["border"]}"/>')
        icon_name = ""
        if name:
            initials, color = SKILL_META.get(name, (re.sub(r"[^A-Za-z0-9]", "", name)[:3].upper() or "?", "#6e7681"))
            icon_name = SKILL_ICON.get(name, re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"))
            icon_svg = skill_icon_svg(name, color, initials)
            write_if_changed(ICONS / f"{icon_name}.svg", icon_svg)
            icon_root = ET.fromstring(icon_svg)
            icon_parts = [ET.tostring(child, encoding="unicode") for child in icon_root
                          if child.tag.rsplit("}", 1)[-1].lower() != "text"]
            nested_x = x + (cell_width - 40) / 2
            cells.append(f'<svg x="{nested_x:.2f}" y="{y + 5}" width="40" height="40" viewBox="0 0 40 40">{"".join(icon_parts)}</svg>')
            cells.append(f'<text x="{x + cell_width / 2:.2f}" y="{y + 64}" fill="{PALETTE["text"]}" text-anchor="middle" font-family="monospace" font-size="10">{escape(name)}</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{rows * cell_height}" viewBox="0 0 {width} {rows * cell_height}" role="img" aria-label="Technical skills icon grid">{"".join(cells)}</svg>'


def social_bar(profile: dict, sha: str) -> str:
    links = profile["links"]
    cells_head, cells_body = [], []
    for label, key, color in SOCIALS:
        target = links.get(key, "")
        if not target and key == "portfolio":
            continue
        cells_head.append(f'<td align="center" bgcolor="#12161d">{label}</td>')
        filename = f"social-{key}.svg"
        icon_content = social_icon_svg(label, key, color)
        write_if_changed(ICONS / filename, icon_content)
        safe_target = html.escape(target, quote=True)
        cells_body.append(f'<td align="center" bgcolor="#0f141b"><a href="{safe_target}"><img src="assets/icons/{filename}?v={sha}" width="48" height="48" alt="{label}"/></a></td>')
    return '<table cellpadding="2" border="0"><tr>' + "".join(cells_head) + "</tr><tr>" + "".join(cells_body) + "</tr></table>"


def parse_profile_yaml(content: str) -> dict:
    """Read the deliberately small YAML subset used by profile.yml if PyYAML is absent."""
    profile: dict = {}
    section = ""

    def scalar(value: str) -> str:
        value = value.strip()
        if value.startswith('"'):
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid quoted YAML value: {value}") from exc
        return value

    for line_number, raw in enumerate(content.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0:
            match = re.fullmatch(r"([a-z_]+):(?:\s*(.*))?", line)
            if not match:
                raise ValueError(f"invalid top-level YAML at line {line_number}")
            key, value = match.group(1), match.group(2) or ""
            section = key if not value else ""
            if value:
                profile[key] = scalar(value)
            elif key == "links":
                profile[key] = {}
            elif key in ("selected_repos", "skills"):
                profile[key] = []
            else:
                profile[key] = ""
        elif section == "links" and indent == 2:
            match = re.fullmatch(r"([a-z_]+):\s*(.*)", line)
            if not match:
                raise ValueError(f"invalid link at line {line_number}")
            profile[section][match.group(1)] = scalar(match.group(2))
        elif section == "selected_repos" and indent == 2:
            match = re.fullmatch(r"-\s*name:\s*(.*)", line)
            if not match:
                raise ValueError(f"invalid repository at line {line_number}")
            profile[section].append({"name": scalar(match.group(1))})
        elif section == "selected_repos" and indent == 4:
            match = re.fullmatch(r"([a-z_]+):\s*(.*)", line)
            if not match or not profile[section]:
                raise ValueError(f"invalid repository field at line {line_number}")
            profile[section][-1][match.group(1)] = scalar(match.group(2))
        elif section == "skills" and indent == 2:
            match = re.fullmatch(r"-\s*\[(.*)\]", line)
            if not match:
                raise ValueError(f"invalid skill row at line {line_number}")
            profile[section].append([item.strip() for item in match.group(1).split(",")])
        else:
            raise ValueError(f"unsupported profile.yml structure at line {line_number}")
    return profile


def main() -> None:
    try:
        profile_text = (ROOT / "profile.yml").read_text(encoding="utf-8")
        profile = yaml.safe_load(profile_text) if yaml else parse_profile_yaml(profile_text)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Unable to read profile.yml: {exc}") from exc
    if not isinstance(profile, dict) or not profile.get("name") or not profile.get("selected_repos"):
        raise SystemExit("profile.yml needs a name and at least one selected repository")

    ASSETS.mkdir(exist_ok=True)
    GENERATED.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    cached_data = {}
    if CACHE.exists():
        try:
            cached_data = json.loads(CACHE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Ignoring unreadable cached GitHub data at {CACHE}: {exc}", file=sys.stderr)
    if "--calendar-only" in sys.argv[1:]:
        data = {**fallback_data(), **cached_data}
        if not data.get("languages"):
            data["languages"] = fallback_data()["languages"]
        public_session = requests.Session()
        public_session.headers.update({"User-Agent": "MERCIA-lab-profile-builder"})
        fetch_public_contribution_calendar(public_session, data)
    else:
        data = fetch_profile_data(profile, cached_data, offline="--offline" in sys.argv[1:])
        if not data.get("languages"):
            data["languages"] = fallback_data()["languages"]
    seed, iso_week = iso_week_seed()
    cache_state = json.dumps({"profile": profile, "data": data, "week": iso_week}, sort_keys=True, ensure_ascii=False)
    sha = os.getenv("PROFILE_SHA") or hashlib.sha256(cache_state.encode("utf-8")).hexdigest()[:7]
    write_if_changed(ASSETS / "pixel-banner.svg", banner_svg(profile["name"], profile["handle"], profile["tagline"], seed))
    write_if_changed(ASSETS / "pixel-banner-light.svg", banner_svg(profile["name"], profile["handle"], profile["tagline"], seed, True))
    write_if_changed(ASSETS / "pixel-divider.svg", pixel_divider(seed))
    headings = {"who-i-am": "WHO I AM", "what-i-do": "WHAT I DO", "vision": "VISION", "beyond-code": "BEYOND CODE", "featured-project": "FEATURED PROJECT", "skill-set": "SKILL SET"}
    for index, (slug, title) in enumerate(headings.items()):
        write_if_changed(GENERATED / f"heading-{slug}.svg", heading_svg(title))
        write_if_changed(GENERATED / f"divider-{slug}.svg", glitch_svg(seed + index * 197, 470))
        write_if_changed(GENERATED / f"section-header-{slug}.svg", section_header_svg(title, seed + index * 197))
    write_if_changed(GENERATED / "stats-panel.svg", stats_panel(data))
    write_if_changed(GENERATED / "stats-panel-light.svg", stats_panel(data, True))
    write_if_changed(CACHE, json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2))
    write_if_changed(ASSETS / "project-showcase.svg", project_showcase(data, 900))
    write_if_changed(ASSETS / "project-showcase-mobile.svg", project_showcase(data, 360))
    write_if_changed(GENERATED / "pixel-strip.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="280" height="18" viewBox="0 0 280 18">{pixel_mosaic(seed + 991, 0, 1, 35, 2, 8)}</svg>')
    write_if_changed(GENERATED / "skills-grid.svg", skills_grid_svg(profile, 8, 900))
    write_if_changed(GENERATED / "skills-grid-mobile.svg", skills_grid_svg(profile, 4, 360))
    socials_html = social_bar(profile, sha)
    write_if_changed(ICONS / "social-pixels-left.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="40" viewBox="0 0 16 40">{pixel_mosaic(seed + 71, 0, 0, 2, 5, 8)}</svg>')
    write_if_changed(ICONS / "social-pixels-right.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="40" viewBox="0 0 16 40">{pixel_mosaic(seed + 107, 0, 0, 2, 5, 8)}</svg>')

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), undefined=StrictUndefined,
                      autoescape=False, keep_trailing_newline=True)
    template = env.get_template("README.md.j2")
    rendered = template.render(profile=profile, featured_repo=data["selected_repos"][0], iso_week=iso_week,
                               sha=sha,
                               profile_stats={
                                   **data,
                                   "followers_display": data["followers"] if data["user_data_available"] else "—",
                                   "following_display": data["following"] if data["user_data_available"] else "—",
                               },
                               socials_html=socials_html)
    write_if_changed(ROOT / "README.md", rendered)
    print(f"Profile build complete for {USERNAME} ({iso_week}); README and local assets are current.")


if __name__ == "__main__":
    main()
