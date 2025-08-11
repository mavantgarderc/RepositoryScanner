import os
import requests
from dotenv import load_dotenv
from colors import COLORS

load_dotenv()

USERNAME = os.getenv("USERNAME")
TOKEN = os.getenv("GH_TOKEN")
TOP_N = 6
SVG_PATH = "assets/languages.svg"

EXCLUDED_LANGS_RAW = os.getenv("EXCLUDED_LANGS", "")
EXCLUDED_LANGS = set(
    lang.strip().lower() for lang in EXCLUDED_LANGS_RAW.split(",") if lang.strip()
)

if EXCLUDED_LANGS:
    print(f"Excluding languages: {EXCLUDED_LANGS_RAW}")

API = "https://api.github.com"


def get_repos():
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

        print(f"Page {page}: {len(batch)} repos, {len(non_forks)} non-forks")
        page += 1

    return repos


def get_language_data(repo):
    r = requests.get(repo["languages_url"], headers={"Authorization": f"token {TOKEN}"})
    r.raise_for_status()
    return r.json()


def aggregate_languages():
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


def generate_svg(top_langs, total_lines):
    svg_parts = [
        '<svg width="600" height="400" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">',
        "<defs>",
        "<style>",
        f'.bg-primary {{ fill: {COLORS["bg_primary"]}; }}',
        f'.bg-secondary {{ fill: {COLORS["bg_secondary"]}; }}',
        f'.fg-primary {{ fill: {COLORS["fg_primary"]}; }}',
        f'.fg-secondary {{ fill: {COLORS["fg_secondary"]}; }}',
        f'.border {{ stroke: {COLORS["border"]}; }}',
        ".font-title { font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; }",
        ".font-lang { font-family: 'Courier New', monospace; font-size: 14px; }",
        ".font-percent { font-family: 'Courier New', monospace; font-size: 12px; }",
        ".font-footer { font-family: 'Courier New', monospace; font-size: 10px; }",
    ]

    for lang, lines in top_langs:
        class_name = (
            lang.lower().replace("#", "sharp").replace("+", "plus").replace(" ", "")
        )
        color = COLORS["languages"].get(lang, COLORS["fg_primary"])
        svg_parts.append(f".{class_name} {{ fill: {color}; }}")

    svg_parts.extend(["</style>", "</defs>"])

    svg_parts.append(
        f'<rect width="600" height="400" fill="{COLORS["bg_primary"]}" rx="12"/>'
    )
    svg_parts.append(
        f'<rect x="8" y="8" width="584" height="384" fill="none" stroke="{COLORS["border"]}" stroke-width="2" rx="8"/>'
    )
    svg_parts.append(
        f'<text x="300" y="40" text-anchor="middle" fill="{COLORS["fg_primary"]}" class="font-title">Most Used Languages</text>'
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
        svg_parts.append(
            f'<text x="25" y="4" class="fg-primary font-lang">{lang}</text>'
        )
        svg_parts.append(
            f'<text x="460" y="4" class="fg-secondary font-percent">{percent:.1f}%</text>'
        )
        svg_parts.append(
            f'<rect x="25" y="12" width="{bar_width}" height="{bar_height}" fill="{COLORS["border"]}" rx="4"/>'
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
        f'<line x1="60" y1="{footer_y}" x2="540" y2="{footer_y}" stroke="{COLORS["border"]}" stroke-width="1"/>'
    )

    if USERNAME:
        svg_parts.append(
            f'<text x="300" y="{footer_y + 25}" text-anchor="middle" class="fg-secondary font-footer">Based on repository analysis • github.com/{USERNAME}</text>'
        )

    svg_parts.append(
        f'<text x="300" y="{footer_y + 40}" text-anchor="middle" class="fg-secondary font-footer" opacity="0.7">Kanagawa Theme • Updated automatically</text>'
    )
    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def main():
    if not TOKEN:
        raise ValueError("GH_TOKEN environment variable must be set")

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

    svg_content = generate_svg(top_langs, total_lines)

    os.makedirs(os.path.dirname(SVG_PATH), exist_ok=True)
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"SVG successfully written to {SVG_PATH}")


if __name__ == "__main__":
    main()
