import os
import sys

import requests
from colors import COLORS
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("GITHUB_USERNAME") or os.getenv("USERNAME")
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

BASE_HEADERS = {
    "User-Agent": "RepositoryScanner/1.0 (+https://github.com/mavantgarderc/RepositoryScanner)"
}
if TOKEN:
    BASE_HEADERS["Authorization"] = f"token {TOKEN}"


def lang_to_class(lang: str) -> str:
    return (
        lang.lower()
        .replace("#", "sharp")
        .replace("+", "plus")
        .replace(" ", "")
        .replace("-", "dash")
    )


def get_repos():
    if not TOKEN and not USERNAME:
        raise ValueError(
            "GITHUB_USERNAME or USERNAME environment variable must be set when "
            "GH_TOKEN is not provided"
        )

    repos = []
    page = 1
    per_page = 100

    if TOKEN:
        endpoint = f"{API}/user/repos"
        who = USERNAME or "<authenticated user>"
    else:
        endpoint = f"{API}/users/{USERNAME}/repos"
        who = USERNAME

    print(f"Fetching repositories for user: {who}")

    while True:
        params = {
            "per_page": per_page,
            "page": page,
            "type": "owner",
            "sort": "updated",
        }

        try:
            r = requests.get(endpoint, params=params, headers=BASE_HEADERS, timeout=30)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repositories page {page}: {e}")
            if page == 1:
                raise
            break

        batch = r.json()
        if not batch:
            break

        non_forks = [
            repo
            for repo in batch
            if not repo["fork"] and not repo.get("archived", False)
        ]
        repos.extend(non_forks)

        print(f"Page {page}: {len(batch)} repos, {len(non_forks)} non-forks (active)")
        page += 1

        if page > 50:  
            print("Warning: Reached maximum page limit (50)")
            break

    print(f"Total repositories found: {len(repos)}")
    return repos


def get_language_data(repo):
    repo_name = repo.get("name", "<unknown>")

    try:
        r = requests.get(repo["languages_url"], headers=BASE_HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch languages for {repo_name}: {e}")
        return {}


def aggregate_languages():
    repos = get_repos()
    totals = {}

    print(f"Processing {len(repos)} repositories...")

    for i, repo in enumerate(repos, 1):
        repo_name = repo["name"]
        print(f"Processing {i}/{len(repos)}: {repo_name}")

        try:
            langs = get_language_data(repo)
            for lang, size in langs.items():
                if lang.lower() in EXCLUDED_LANGS:
                    print(f"  Excluding {lang} from {repo_name}")
                    continue
                totals[lang] = totals.get(lang, 0) + size

        except Exception as e:
            print(f"Error processing {repo_name}: {e}")
            continue

    print(f"Language aggregation complete. Found {len(totals)} languages.")
    return totals


def generate_svg(top_langs, total_size):
    svg_width = 600
    svg_height = 280

    svg_parts = [
        f'<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">',
        "<defs>",
        "<style>",
        f'.bg-primary {{ fill: {COLORS["bg_primary"]}; }}',
        f'.bg-secondary {{ fill: {COLORS["bg_secondary"]}; }}',
        f'.fg-primary {{ fill: {COLORS["fg_primary"]}; }}',
        f'.fg-secondary {{ fill: {COLORS["fg_secondary"]}; }}',
        f'.border {{ stroke: {COLORS["border"]}; }}',
        ".font-title { font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; }",
        ".font-lang { font-family: 'Courier New', monospace; font-size: 13px; }",
        ".font-percent { font-family: 'Courier New', monospace; font-size: 12px; }",
        ".font-footer { font-family: 'Courier New', monospace; font-size: 10px; }",
    ]

    for lang, _ in top_langs:
        class_name = lang_to_class(lang)
        color = COLORS["languages"].get(
            lang, COLORS.get("accent", COLORS["fg_primary"])
        )
        svg_parts.append(f".{class_name} {{ fill: {color}; }}")

    svg_parts.extend(["</style>", "</defs>"])

    svg_parts.append(
        f'<rect width="{svg_width}" height="{svg_height}" fill="{COLORS["bg_primary"]}" rx="12"/>'
    )
    svg_parts.append(
        f'<rect x="8" y="8" width="{svg_width-16}" height="{svg_height-16}" fill="none" stroke="{COLORS["border"]}" stroke-width="2" rx="8"/>'
    )

    svg_parts.append(
        f"""
        <text x="{svg_width/2}" y="35" text-anchor="middle" fill="{COLORS['fg_primary']}" class="font-title">
            <tspan x="{svg_width/2}" dy="0">Most Used Languages</tspan>
            <tspan x="{svg_width/2}" dy="1.2em">(Public and Private Repositories)</tspan>
        </text>
        """
    )

    bar_width = 480
    bar_height = 24
    bar_x = (svg_width - bar_width) / 2
    bar_y = 85

    raw_widths = []
    for _, size in top_langs:
        percent = (size / total_size) * 100
        segment_width = (percent / 100) * bar_width

        if 0 < segment_width < 2:
            segment_width = 2

        raw_widths.append(segment_width)

    total_segment_width = sum(raw_widths)
    if total_segment_width > 0 and abs(total_segment_width - bar_width) > 0.01:
        scale = bar_width / total_segment_width
        widths = [w * scale for w in raw_widths]
    else:
        widths = raw_widths

    current_x = bar_x
    svg_parts.append('<g id="language-bar">')

    for i, ((lang, _), segment_width) in enumerate(zip(top_langs, widths)):
        class_name = lang_to_class(lang)

        if i == 0:
            svg_parts.append(
                f'<rect x="{current_x}" y="{bar_y}" width="{segment_width}" height="{bar_height}" '
                f'class="{class_name}" rx="4" ry="4" style="border-radius: 4px 0 0 4px;"/>'
            )
        elif i == len(top_langs) - 1:
            svg_parts.append(
                f'<rect x="{current_x}" y="{bar_y}" width="{segment_width}" height="{bar_height}" '
                f'class="{class_name}" rx="4" ry="4" style="border-radius: 0 4px 4px 0;"/>'
            )
        else:
            svg_parts.append(
                f'<rect x="{current_x}" y="{bar_y}" width="{segment_width}" height="{bar_height}" '
                f'class="{class_name}"/>'
            )

        current_x += segment_width

    svg_parts.append("</g>")

    svg_parts.append(
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" '
        f'fill="{COLORS["bg_primary"]}" rx="4">'
    )
    svg_parts.append(
        f'  <animate attributeName="width" from="{bar_width}" to="0" dur="1.2s" fill="freeze"/>'
    )
    svg_parts.append("</rect>")

    legend_start_y = bar_y + bar_height + 25
    col_width = bar_width / 2
    items_per_col = (len(top_langs) + 1) // 2

    for i, (lang, size) in enumerate(top_langs):
        percent = (size / total_size) * 100
        class_name = lang_to_class(lang)

        col = i // items_per_col
        row = i % items_per_col

        x_pos = bar_x + (col * col_width)
        y_pos = legend_start_y + (row * 22)

        svg_parts.append(f'<g transform="translate({x_pos}, {y_pos})">')
        svg_parts.append(f'<circle cx="6" cy="-3" r="5" class="{class_name}"/>')
        svg_parts.append(
            f'<text x="18" y="0" class="fg-primary font-lang">{lang}</text>'
        )
        svg_parts.append(
            f'<text x="180" y="0" class="fg-secondary font-percent" text-anchor="end">{percent:.1f}%</text>'
        )
        svg_parts.append("</g>")

    footer_y = legend_start_y + (items_per_col * 22) + 15
    svg_parts.append(
        f'<line x1="60" y1="{footer_y}" x2="{svg_width-60}" y2="{footer_y}" stroke="{COLORS["border"]}" stroke-width="1"/>'
    )

    if USERNAME:
        svg_parts.append(
            f'<text x="{svg_width/2}" y="{footer_y + 18}" text-anchor="middle" class="fg-secondary font-footer">Based on repository analysis • github.com/{USERNAME}</text>'
        )

    svg_parts.append(
        f'<text x="{svg_width/2}" y="{footer_y + 33}" text-anchor="middle" class="fg-secondary font-footer" opacity="0.7">Kanagawa Theme • Updated automatically</text>'
    )
    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def main():
    print("Starting language statistics generation...")

    if not TOKEN:
        print(
            "Warning: GH_TOKEN not provided. "
            "Only public repositories will be analyzed and GitHub rate limits will be lower."
        )
        if not USERNAME:
            print(
                "Error: Either GH_TOKEN (recommended) or GITHUB_USERNAME/USERNAME "
                "must be provided"
            )
            return 1

    try:
        langs = aggregate_languages()
        total_size = sum(langs.values())

        if total_size == 0:
            print("Error: No language data found!")
            return 1

        top_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:TOP_N]

        print(f"\nTop {TOP_N} languages (by byte size):")
        for lang, size in top_langs:
            percent = (size / total_size) * 100
            print(f"  {lang}: {size:,} bytes ({percent:.1f}%)")

        svg_content = generate_svg(top_langs, total_size)

        os.makedirs(os.path.dirname(SVG_PATH), exist_ok=True)

        with open(SVG_PATH, "w", encoding="utf-8") as f:
            f.write(svg_content)

        print(f"\nSVG successfully written to {SVG_PATH}")
        print(f"Total code size analyzed (bytes): {total_size:,}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
