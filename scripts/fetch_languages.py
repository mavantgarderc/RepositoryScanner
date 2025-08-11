import os
import requests
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

USERNAME = os.getenv("USERNAME")
TOKEN = os.getenv("GH_TOKEN")
TOP_N = 6
SVG_PATH = "assets/languages.svg"

# Read excluded langs from .env
EXCLUDED_LANGS_RAW = os.getenv("EXCLUDED_LANGS", "")
EXCLUDED_LANGS = set(
    lang.strip().lower() for lang in EXCLUDED_LANGS_RAW.split(",") if lang.strip()
)

if EXCLUDED_LANGS:
    print(f"Excluding languages (as written in .env): {EXCLUDED_LANGS_RAW}")
    print(f"Normalized for matching: {sorted(EXCLUDED_LANGS)}")

colors = {
    "bg_primary": "#1f1f28",
    "bg_secondary": "#2a2a37",
    "fg_primary": "#dcd7ba",
    "fg_secondary": "#c8c093",
    "border": "#54546d",
    "lang": {
        "JavaScript": "#dca561",
        "TypeScript": "#7e9cd8",
        "Python": "#98bb6c",
        "C#": "#76946a",
        "HTML": "#e82424",
        "CSS": "#957fb8",
        "SQL": "#d27e99",
        "Shell": "#6a9589",
        "Go": "#7fb4ca",
        "Rust": "#ffa066",
        "Java": "#e6c384",
        "C++": "#938aa9",
        "C": "#7aa89f",
        "PHP": "#d27e99",
        "Ruby": "#ff5d62",
        "Swift": "#ff9e3b",
        "Kotlin": "#957fb8",
        "Dart": "#7e9cd8",
    },
}

API = "https://api.github.com"


def get_repos():
    """Fetch all non-fork repositories for the user"""
    if not USERNAME:
        raise ValueError("USERNAME environment variable must be set")

    repos = []
    page = 1
    per_page = 100

    if TOKEN:
        endpoint = f"{API}/user/repos"
        headers = {"Authorization": f"token {TOKEN}"}
    else:
        endpoint = f"{API}/users/{USERNAME}/repos"
        headers = {}

    while True:
        params = {
            "per_page": per_page,
            "page": page,
            "type": "owner",
            "sort": "updated",
        }

        r = requests.get(endpoint, params=params, headers=headers)
        r.raise_for_status()

        batch = r.json()
        if not batch:
            break

        non_forks = [repo for repo in batch if not repo["fork"]]
        repos.extend(non_forks)

        print(f"  Page {page}: {len(batch)} repos, {len(non_forks)} non-forks")
        page += 1

    return repos


def get_language_data(repo):
    """Get language data for a specific repository"""
    r = requests.get(repo["languages_url"], headers={"Authorization": f"token {TOKEN}"})
    r.raise_for_status()
    return r.json()


def aggregate_languages():
    """Aggregate language statistics across all repositories"""
    repos = get_repos()
    totals = {}

    print(f"Processing {len(repos)} repositories...")

    for repo in repos:
        try:
            langs = get_language_data(repo)
            for lang, lines in langs.items():
                if lang.lower() in EXCLUDED_LANGS:
                    continue
                totals[lang] = totals.get(lang, 0) + lines
        except requests.exceptions.RequestException as e:
            print(f"Error fetching languages for {repo['name']}: {e}")
            continue

    return totals


langs = aggregate_languages()
total_lines = sum(langs.values())

if total_lines == 0:
    print("No language data found!")
    exit(1)

top_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:TOP_N]

print(f"Top {TOP_N} languages:")
for lang, lines in top_langs:
    percent = (lines / total_lines) * 100
    print(f"  {lang}: {lines:,} lines ({percent:.1f}%)")

svg_parts = [
    '<svg width="600" height="400" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">',
    "<defs>",
    "<style>",
    f'.bg-primary {{ fill: {colors["bg_primary"]}; }}',
    f'.bg-secondary {{ fill: {colors["bg_secondary"]}; }}',
    f'.fg-primary {{ fill: {colors["fg_primary"]}; }}',
    f'.fg-secondary {{ fill: {colors["fg_secondary"]}; }}',
    f'.border {{ stroke: {colors["border"]}; }}',
    ".font-title { font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; }",
    ".font-lang { font-family: 'Courier New', monospace; font-size: 14px; }",
    ".font-percent { font-family: 'Courier New', monospace; font-size: 12px; }",
    ".font-footer { font-family: 'Courier New', monospace; font-size: 10px; }",
]

for lang, lines in top_langs:
    class_name = (
        lang.lower().replace("#", "sharp").replace("+", "plus").replace(" ", "")
    )
    color = colors["lang"].get(lang, colors["fg_primary"])
    svg_parts.append(f".{class_name} {{ fill: {color}; }}")

svg_parts.extend(["</style>", "</defs>"])

svg_parts.append(
    f'<rect width="600" height="400" fill="{colors["bg_primary"]}" rx="12"/>'
)
svg_parts.append(
    f'<rect x="8" y="8" width="584" height="384" fill="none" stroke="{colors["border"]}" stroke-width="2" rx="8"/>'
)

svg_parts.append(
    f'<text x="300" y="40" text-anchor="middle" fill="{colors["fg_primary"]}" class="font-title">Most Used Languages</text>'
)

bar_width = 400
bar_height = 8
start_x = 60
start_y = 80

for i, (lang, lines) in enumerate(top_langs):
    percent = (lines / total_lines) * 100
    bar_len = max((percent / 100) * bar_width, 2)
    class_name = (
        lang.lower().replace("#", "sharp").replace("+", "plus").replace(" ", "")
    )

    y_pos = start_y + i * 40

    svg_parts.append(f'<g transform="translate({start_x}, {y_pos})">')

    svg_parts.append(f'<circle cx="8" cy="0" r="6" class="{class_name}"/>')

    svg_parts.append(f'<text x="25" y="4" class="fg-primary font-lang">{lang}</text>')

    svg_parts.append(
        f'<text x="460" y="4" class="fg-secondary font-percent">{percent:.1f}%</text>'
    )

    svg_parts.append(
        f'<rect x="25" y="12" width="{bar_width}" height="{bar_height}" fill="{colors["border"]}" rx="4"/>'
    )

    svg_parts.append(
        f'<rect x="25" y="12" width="{bar_len}" height="{bar_height}" class="{class_name}" rx="4">'
    )
    svg_parts.append(
        f'  <animate attributeName="width" from="0" to="{bar_len}" dur="1.5s" begin="{0.2 + i*0.1}s" fill="freeze"/>'
    )
    svg_parts.append("</rect>")

    svg_parts.append("</g>")

footer_y = start_y + len(top_langs) * 40 + 20
svg_parts.append(
    f'<line x1="60" y1="{footer_y}" x2="540" y2="{footer_y}" stroke="{colors["border"]}" stroke-width="1"/>'
)

if USERNAME:
    svg_parts.append(
        f'<text x="300" y="{footer_y + 25}" text-anchor="middle" class="fg-secondary font-footer">Based on repository analysis • github.com/{USERNAME}</text>'
    )

svg_parts.append(
    f'<text x="300" y="{footer_y + 40}" text-anchor="middle" class="fg-secondary font-footer" opacity="0.7">Kanagawa Theme • Updated automatically</text>'
)

svg_parts.append("</svg>")

os.makedirs(os.path.dirname(SVG_PATH), exist_ok=True)
with open(SVG_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(svg_parts))

print(f"SVG successfully written to {SVG_PATH}")
