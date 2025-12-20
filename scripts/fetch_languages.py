import os
import sys

import requests
from colors import COLORS
from dotenv import load_dotenv

load_dotenv()


def _get_top_n(default: int = 6) -> int:
    """Read TOP_LANGS from env, falling back to default (strictly backwards-compatible)."""
    raw = os.getenv("TOP_LANGS", "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        if value <= 0:
            print(
                f"Warning: TOP_LANGS must be positive, got {raw!r}. Falling back to {default}."
            )
            return default
        return value
    except ValueError:
        print(f"Warning: invalid TOP_LANGS value {raw!r}. Falling back to {default}.")
        return default


# Prefer explicit GitHub-specific variable, but support USERNAME for backwards compatibility
USERNAME = os.getenv("GITHUB_USERNAME") or os.getenv("USERNAME")
TOKEN = os.getenv("GH_TOKEN")
TOP_N = _get_top_n(6)
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
    """Normalize a language name into a safe CSS class name."""
    return (
        lang.lower()
        .replace("#", "sharp")
        .replace("+", "plus")
        .replace(" ", "")
        .replace("-", "dash")
    )


def get_repos():
    """Fetch all repositories for the configured user.

    When GH_TOKEN is set, uses the authenticated /user/repos endpoint.
    When GH_TOKEN is not set, uses /users/{USERNAME}/repos and only public repos
    are available.
    """
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

        # Filter out forks and archived repositories
        non_forks = [
            repo
            for repo in batch
            if not repo["fork"] and not repo.get("archived", False)
        ]
        repos.extend(non_forks)

        print(f"Page {page}: {len(batch)} repos, {len(non_forks)} non-forks (active)")
        page += 1

        # Safety check to avoid infinite loops
        if page > 50:  # Assuming no user has more than 5000 repos
            print("Warning: Reached maximum page limit (50)")
            break

    print(f"Total repositories found: {len(repos)}")
    return repos


def get_language_data(repo):
    """Fetch language data for a specific repository.

    Works with or without GH_TOKEN. Without a token, only public repositories
    are available and GitHub's unauthenticated rate limit will apply.
    """
    repo_name = repo.get("name", "<unknown>")

    try:
        r = requests.get(repo["languages_url"], headers=BASE_HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch languages for {repo_name}: {e}")
        return {}


def aggregate_languages():
    """Aggregate language statistics across all repositories."""
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
    """Generate SVG visualization with a single stacked bar.

    top_langs: list of (language, size_in_bytes) tuples.
    total_size: total size in bytes across all languages.
    """
    svg_width = 600
    svg_height = 280

    # Bar geometry (defined early so we can use it in <defs>)
    bar_width = 480
    bar_height = 24
    bar_x = (svg_width - bar_width) // 2  # integer for crisp alignment
    bar_y = 85

    # --- <svg>, <defs>, styles, clipPath ------------------------------------
    style_lines = [
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

    # Color classes for each language
    for lang, _ in top_langs:
        class_name = lang_to_class(lang)
        color = COLORS["languages"].get(lang, COLORS.get("accent", COLORS["fg_primary"]))
        style_lines.append(f".{class_name} {{ fill: {color}; }}")

    svg_parts = [
        f'<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" '
        f'xmlns="http://www.w3.org/2000/svg">',
        "<defs>",
        "<style>",
        *style_lines,
        "</style>",
        # One rounded rect clipPath for the whole bar → no per‑segment rounding seams
        f'<clipPath id="barClip">'
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="4" ry="4"/>'
        f'</clipPath>',
        "</defs>",
    ]

    # --- Background ----------------------------------------------------------
    svg_parts.append(
        f'<rect width="{svg_width}" height="{svg_height}" '
        f'fill="{COLORS["bg_primary"]}" rx="12"/>'
    )
    svg_parts.append(
        f'<rect x="8" y="8" width="{svg_width-16}" height="{svg_height-16}" '
        f'fill="none" stroke="{COLORS["border"]}" stroke-width="2" rx="8"/>'
    )

    # --- Title ---------------------------------------------------------------
    svg_parts.append(
        f"""
        <text x="{svg_width/2}" y="35" text-anchor="middle"
              fill="{COLORS['fg_primary']}" class="font-title">
            <tspan x="{svg_width/2}" dy="0">Most Used Languages</tspan>
            <tspan x="{svg_width/2}" dy="1.2em">(Public and Private Repositories)</tspan>
        </text>
        """
    )

    # --- Pixel-perfect widths for the stacked bar ---------------------------
    if total_size <= 0:
        int_widths = [0] * len(top_langs)
    else:
        raw_widths = []
        for _, size in top_langs:
            proportion = size / total_size
            raw = proportion * bar_width
            raw_widths.append(raw)

        # Start with rounded widths, min 1px if >0
        int_widths = []
        for raw in raw_widths:
            if raw <= 0:
                int_widths.append(0)
            else:
                w_int = int(round(raw))
                if w_int < 1:
                    w_int = 1
                int_widths.append(w_int)

        total_int = sum(int_widths)
        diff = bar_width - total_int

        # Adjust so sum(int_widths) == bar_width
        if diff != 0 and len(int_widths) > 0:
            fracs = [rw - iw for rw, iw in zip(raw_widths, int_widths)]
            if diff > 0:
                # Need to add pixels → to biggest positive fractional parts
                order = sorted(range(len(int_widths)), key=lambda i: fracs[i], reverse=True)
                for idx in order:
                    if diff <= 0:
                        break
                    if int_widths[idx] > 0:
                        int_widths[idx] += 1
                        diff -= 1
            else:  # diff < 0
                # Need to remove pixels → from most negative fractional parts
                order = sorted(range(len(int_widths)), key=lambda i: fracs[i])
                for idx in order:
                    if diff >= 0:
                        break
                    if int_widths[idx] > 1:
                        int_widths[idx] -= 1
                        diff += 1
                # If |diff| still > 0, bar ends up slightly < bar_width; visually fine.

    # --- Stacked bar using clipPath (no rounded corners per segment) --------
    current_x = bar_x
    svg_parts.append(
        f'<g id="language-bar" clip-path="url(#barClip)" shape-rendering="crispEdges">'
    )

    for (lang, _), segment_width in zip(top_langs, int_widths):
        if segment_width <= 0:
            continue

        class_name = lang_to_class(lang)

        svg_parts.append(
            f'<rect x="{current_x}" y="{bar_y}" width="{segment_width}" '
            f'height="{bar_height}" class="{class_name}"/>'
        )

        current_x += segment_width

    svg_parts.append("</g>")

    # --- Curtain animation over the whole bar -------------------------------
    svg_parts.append(
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" '
        f'fill="{COLORS["bg_primary"]}" rx="4">'
    )
    svg_parts.append(
        f'  <animate attributeName="width" from="{bar_width}" to="0" '
        f'dur="1.2s" fill="freeze"/>'
    )
    svg_parts.append("</rect>")

    # --- Legend (same layout you have now) ----------------------------------
    legend_start_y = bar_y + bar_height + 25
    col_width = bar_width / 2
    row_height = 22
    items_per_col = (len(top_langs) + 1) // 2

    for i, (lang, size) in enumerate(top_langs):
        percent = (size / total_size) * 100 if total_size else 0.0
        class_name = lang_to_class(lang)

        col = i // items_per_col
        row = i % items_per_col

        x_col_left = bar_x + (col * col_width)
        y = legend_start_y + (row * row_height)

        svg_parts.append(f'<g transform="translate({x_col_left}, {y})">')
        svg_parts.append(
            f'<circle cx="8" cy="-3" r="5" class="{class_name}"/>'
        )
        svg_parts.append(
            f'<text x="24" y="0" class="fg-primary font-lang">{lang}</text>'
        )
        svg_parts.append(
            f'<text x="{col_width - 4}" y="0" class="fg-secondary font-percent" '
            f'text-anchor="end">{percent:.2f}%</text>'
        )
        svg_parts.append("</g>")

    # --- Footer -------------------------------------------------------------
    footer_y = legend_start_y + (items_per_col * row_height) + 15
    svg_parts.append(
        f'<line x1="60" y1="{footer_y}" x2="{svg_width-60}" y2="{footer_y}" '
        f'stroke="{COLORS["border"]}" stroke-width="1"/>'
    )

    if USERNAME:
        svg_parts.append(
            f'<text x="{svg_width/2}" y="{footer_y + 18}" text-anchor="middle" '
            f'class="fg-secondary font-footer">'
            f'Based on repository analysis • github.com/{USERNAME}'
            f'</text>'
        )

    svg_parts.append(
        f'<text x="{svg_width/2}" y="{footer_y + 33}" text-anchor="middle" '
        f'class="fg-secondary font-footer" opacity="0.7">'
        f'Kanagawa Theme • Updated automatically'
        f'</text>'
    )

    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def main():
    """Main function to orchestrate the language statistics generation."""
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
            print(f"  {lang}: {size:,} bytes ({percent:.2f}%)")

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
