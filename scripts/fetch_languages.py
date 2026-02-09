import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import requests
from colors import COLORS
from dotenv import load_dotenv

load_dotenv()

CACHE_FILE = Path(".contribution_cache.json")


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


def generate_svg(top_langs, total_size, contribution_data=None):
    svg_width = 600
    svg_height = 355 if contribution_data else 280

    bar_width = 480
    bar_height = 24
    bar_x = (svg_width - bar_width) // 2
    bar_y = 85

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
        ".stat-box { fill: #2a2a37; stroke: #3a3a47; stroke-width: 1; rx: 6; ry: 6; }",
        ".stat-value { font-family: 'Courier New', monospace; font-size: 16px; font-weight: bold; }",
        ".stat-label { font-family: 'Courier New', monospace; font-size: 10px; }",
    ]

    for lang, _ in top_langs:
        class_name = lang_to_class(lang)
        color = COLORS["languages"].get(
            lang, COLORS.get("accent", COLORS["fg_primary"])
        )
        style_lines.append(f".{class_name} {{ fill: {color}; }}")

    svg_parts = [
        f'<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" '
        f'xmlns="http://www.w3.org/2000/svg">',
        "<defs>",
        "<style>",
        *style_lines,
        "</style>",
        f'<clipPath id="barClip">'
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="4" ry="4"/>'
        f"</clipPath>",
        "</defs>",
    ]

    svg_parts.append(
        f'<rect width="{svg_width}" height="{svg_height}" '
        f'fill="{COLORS["bg_primary"]}" rx="12"/>'
    )
    svg_parts.append(
        f'<rect x="8" y="8" width="{svg_width-16}" height="{svg_height-16}" '
        f'fill="none" stroke="{COLORS["border"]}" stroke-width="2" rx="8"/>'
    )

    svg_parts.append(
        f"""
        <text x="{svg_width/2}" y="35" text-anchor="middle"
              fill="{COLORS['fg_primary']}" class="font-title">
            <tspan x="{svg_width/2}" dy="0">Most Used Languages</tspan>
            <tspan x="{svg_width/2}" dy="1.2em">(Public and Private Repositories)</tspan>
        </text>
        """
    )

    if total_size <= 0:
        int_widths = [0] * len(top_langs)
    else:
        raw_widths = []
        for _, size in top_langs:
            proportion = size / total_size
            raw = proportion * bar_width
            raw_widths.append(raw)

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

        if diff != 0 and len(int_widths) > 0:
            fracs = [rw - iw for rw, iw in zip(raw_widths, int_widths)]
            if diff > 0:
                order = sorted(
                    range(len(int_widths)), key=lambda i: fracs[i], reverse=True
                )
                for idx in order:
                    if diff <= 0:
                        break
                    if int_widths[idx] > 0:
                        int_widths[idx] += 1
                        diff -= 1
            else:
                order = sorted(range(len(int_widths)), key=lambda i: fracs[i])
                for idx in order:
                    if diff >= 0:
                        break
                    if int_widths[idx] > 1:
                        int_widths[idx] -= 1
                        diff += 1

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

    svg_parts.append(
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" '
        f'fill="{COLORS["bg_primary"]}" rx="4">'
    )
    svg_parts.append(
        f'  <animate attributeName="width" from="{bar_width}" to="0" '
        f'dur="1.2s" fill="freeze"/>'
    )
    svg_parts.append("</rect>")

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
        svg_parts.append(f'<circle cx="8" cy="-3" r="5" class="{class_name}"/>')
        svg_parts.append(
            f'<text x="24" y="0" class="fg-primary font-lang">{lang}</text>'
        )
        svg_parts.append(
            f'<text x="{col_width - 4}" y="0" class="fg-secondary font-percent" '
            f'text-anchor="end">{percent:.2f}%</text>'
        )
        svg_parts.append("</g>")

    if contribution_data:

        stats_start_y = legend_start_y + (items_per_col * row_height) + 20
        box_width = 150
        box_height = 65
        spacing = (svg_width - 3 * box_width) // 4

        x_pos = spacing
        y_pos = stats_start_y

        svg_parts.append(
            f'<rect x="{x_pos}" y="{y_pos}" width="{box_width}" height="{box_height}" class="stat-box"/>'
        )
        svg_parts.append(
            f'<text x="{x_pos + box_width/2}" y="{y_pos + 25}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="{COLORS["fg_primary"]}" class="stat-value">{contribution_data["total_contributions"]:,}</text>'
        )
        svg_parts.append(
            f'<text x="{x_pos + box_width/2}" y="{y_pos + 45}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="{COLORS["fg_secondary"]}" class="stat-label">TOTAL CONTRIBUTIONS</text>'
        )

        x_pos += box_width + spacing

        svg_parts.append(
            f'<rect x="{x_pos}" y="{y_pos}" width="{box_width}" height="{box_height}" class="stat-box"/>'
        )
        svg_parts.append(
            f'<text x="{x_pos + box_width/2}" y="{y_pos + 25}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="{COLORS["accent"]}" class="stat-value">{contribution_data["current_streak"]} DAYS</text>'
        )
        svg_parts.append(
            f'<text x="{x_pos + box_width/2}" y="{y_pos + 45}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="{COLORS["fg_secondary"]}" class="stat-label">CURRENT STREAK</text>'
        )

        x_pos += box_width + spacing

        svg_parts.append(
            f'<rect x="{x_pos}" y="{y_pos}" width="{box_width}" height="{box_height}" class="stat-box"/>'
        )
        svg_parts.append(
            f'<text x="{x_pos + box_width/2}" y="{y_pos + 25}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="{COLORS["fg_primary"]}" class="stat-value">{contribution_data["longest_streak"]} DAYS</text>'
        )
        svg_parts.append(
            f'<text x="{x_pos + box_width/2}" y="{y_pos + 45}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="{COLORS["fg_secondary"]}" class="stat-label">LONGEST STREAK</text>'
        )

        footer_y = y_pos + box_height + 15
    else:
        footer_y = legend_start_y + (items_per_col * row_height) + 15

    svg_parts.append(
        f'<line x1="60" y1="{footer_y}" x2="{svg_width-60}" y2="{footer_y}" '
        f'stroke="{COLORS["border"]}" stroke-width="1"/>'
    )

    if USERNAME:
        svg_parts.append(
            f'<text x="{svg_width/2}" y="{footer_y + 18}" text-anchor="middle" '
            f'class="fg-secondary font-footer">'
            f"Based on repository analysis • github.com/{USERNAME}"
            f"</text>"
        )

    svg_parts.append(
        f'<text x="{svg_width/2}" y="{footer_y + 33}" text-anchor="middle" '
        f'class="fg-secondary font-footer" opacity="0.7">'
        f"Kanagawa Theme • Updated automatically"
        f"</text>"
    )

    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def load_contribution_cache():
    """Load cached contribution data from file."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load cache: {e}")
    return {}


def save_contribution_cache(cache_data):
    """Save contribution data to cache file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save cache: {e}")


def get_user_creation_date():
    """Fetch the user's account creation date."""
    query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
      }
    }
    """

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "RepositoryScanner/1.0 (+https://github.com/mavantgarderc/RepositoryScanner)",
    }

    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"login": USERNAME}},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}")
            return None

        user_data = data["data"]["user"]
        if not user_data:
            print(f"User '{USERNAME}' not found")
            return None

        created_at = datetime.fromisoformat(
            user_data["createdAt"].replace("Z", "+00:00")
        )
        return created_at

    except Exception as e:
        print(f"Error fetching user creation date: {e}")
        return None


def fetch_year_contributions(year):
    """Fetch contribution data for a specific year."""
    from_date = datetime(year, 1, 1, 0, 0, 0)
    to_date = datetime(year, 12, 31, 23, 59, 59)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
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
      }
    }
    """

    variables = {
        "login": USERNAME,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "RepositoryScanner/1.0 (+https://github.com/mavantgarderc/RepositoryScanner)",
    }

    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            print(f"GraphQL errors for {year}: {data['errors']}")
            return None

        user_data = data["data"]["user"]
        if not user_data:
            print(f"User '{USERNAME}' not found")
            return None

        return user_data["contributionsCollection"]

    except Exception as e:
        print(f"Error fetching contributions for {year}: {e}")
        return None


def merge_years_data(years_data):
    """Merge contribution data from multiple years."""
    all_weeks = []
    total_calendar_contributions = 0
    total_commit = 0
    total_issue = 0
    total_pr = 0
    total_review = 0

    for year, data in sorted(years_data.items()):
        if not data:
            continue

        calendar = data["contributionCalendar"]
        all_weeks.extend(calendar["weeks"])
        total_calendar_contributions += calendar["totalContributions"]
        total_commit += data["totalCommitContributions"]
        total_issue += data["totalIssueContributions"]
        total_pr += data["totalPullRequestContributions"]
        total_review += data["totalPullRequestReviewContributions"]

    return {
        "weeks": all_weeks,
        "total_contributions": total_calendar_contributions,
        "totalCommitContributions": total_commit,
        "totalIssueContributions": total_issue,
        "totalPullRequestContributions": total_pr,
        "totalPullRequestReviewContributions": total_review,
    }


def get_contribution_data():
    """Fetch all-time contribution data using GitHub GraphQL API with caching."""
    print(f"Fetching contribution data for user: {USERNAME}")

    created_at = get_user_creation_date()
    if not created_at:
        print("Could not determine user creation date, falling back to last 365 days")
        return get_contribution_data_fallback()

    start_year = created_at.year
    current_year = datetime.now().year

    print(f"Account created: {created_at.strftime('%Y-%m-%d')}")
    print(f"Fetching contributions from {start_year} to {current_year}...")

    cache = load_contribution_cache()
    years_data = cache.get("years", {})
    all_types_data = cache.get("all_types", {})

    years_to_fetch = []
    for year in range(start_year, current_year + 1):
        year_str = str(year)
        if year_str not in years_data or year == current_year:
            years_to_fetch.append(year)

    print(f"Years to fetch: {years_to_fetch}")

    rate_limit_remaining = None
    for i, year in enumerate(years_to_fetch):
        year_str = str(year)
        print(f"Fetching {year}... ({i+1}/{len(years_to_fetch)})")

        data = fetch_year_contributions(year)
        if data:
            years_data[year_str] = {
                "weeks": data["contributionCalendar"]["weeks"],
                "totalContributions": data["contributionCalendar"][
                    "totalContributions"
                ],
            }
            all_types_data[year_str] = {
                "totalCommitContributions": data["totalCommitContributions"],
                "totalIssueContributions": data["totalIssueContributions"],
                "totalPullRequestContributions": data["totalPullRequestContributions"],
                "totalPullRequestReviewContributions": data[
                    "totalPullRequestReviewContributions"
                ],
            }

            save_contribution_cache(
                {
                    "years": years_data,
                    "all_types": all_types_data,
                    "last_updated": datetime.now().isoformat(),
                }
            )
        else:
            print(f"Warning: Failed to fetch data for {year}")

        if i < len(years_to_fetch) - 1:
            time.sleep(1)

    merged = merge_years_data(
        {
            year: {
                "contributionCalendar": {
                    "weeks": data["weeks"],
                    "totalContributions": data["totalContributions"],
                },
                "totalCommitContributions": all_types_data.get(year, {}).get(
                    "totalCommitContributions", 0
                ),
                "totalIssueContributions": all_types_data.get(year, {}).get(
                    "totalIssueContributions", 0
                ),
                "totalPullRequestContributions": all_types_data.get(year, {}).get(
                    "totalPullRequestContributions", 0
                ),
                "totalPullRequestReviewContributions": all_types_data.get(year, {}).get(
                    "totalPullRequestReviewContributions", 0
                ),
            }
            for year, data in years_data.items()
        }
    )

    current_streak, longest_streak = calculate_streaks_all_time(merged["weeks"])

    all_types_total = (
        merged["totalCommitContributions"]
        + merged["totalIssueContributions"]
        + merged["totalPullRequestContributions"]
        + merged["totalPullRequestReviewContributions"]
    )

    contribution_data = {
        "total_contributions": merged["total_contributions"],
        "all_types_total": all_types_total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "commit_contributions": merged["totalCommitContributions"],
        "issue_contributions": merged["totalIssueContributions"],
        "pr_contributions": merged["totalPullRequestContributions"],
        "review_contributions": merged["totalPullRequestReviewContributions"],
        "years_fetched": len(years_data),
    }

    print(f"\nSuccessfully fetched contribution data:")
    print(f"  Total contributions (all time): {merged['total_contributions']:,}")
    print(f"  Total contributions (all types): {all_types_total:,}")
    print(f"  Years analyzed: {len(years_data)}")
    print(f"  Current streak: {current_streak} days")
    print(f"  Longest streak: {longest_streak} days")

    return contribution_data


def get_contribution_data_fallback():
    """Fallback to last 365 days if multi-year fetch fails."""
    print("Falling back to last 365 days...")

    to_date = datetime.now()
    from_date = to_date - timedelta(days=365)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
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
      }
    }
    """

    variables = {
        "login": USERNAME,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "RepositoryScanner/1.0 (+https://github.com/mavantgarderc/RepositoryScanner)",
    }

    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}")
            return None

        user_data = data["data"]["user"]
        if not user_data:
            print(f"User '{USERNAME}' not found")
            return None

        contrib_collection = user_data["contributionsCollection"]
        calendar = contrib_collection["contributionCalendar"]

        current_streak, longest_streak = calculate_streaks_all_time(calendar["weeks"])

        all_types_total = (
            contrib_collection["totalCommitContributions"]
            + contrib_collection["totalIssueContributions"]
            + contrib_collection["totalPullRequestContributions"]
            + contrib_collection["totalPullRequestReviewContributions"]
        )

        return {
            "total_contributions": calendar["totalContributions"],
            "all_types_total": all_types_total,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "commit_contributions": contrib_collection["totalCommitContributions"],
            "issue_contributions": contrib_collection["totalIssueContributions"],
            "pr_contributions": contrib_collection["totalPullRequestContributions"],
            "review_contributions": contrib_collection[
                "totalPullRequestReviewContributions"
            ],
            "years_fetched": 1,
        }

    except Exception as e:
        print(f"Error in fallback: {e}")
        return None


def calculate_streaks_all_time(weeks):
    """Calculate current and longest streaks from all-time contribution data."""

    all_days = []
    for week in weeks:
        for day in week["contributionDays"]:
            all_days.append(
                {
                    "date": datetime.strptime(day["date"], "%Y-%m-%d"),
                    "count": day["contributionCount"],
                }
            )

    all_days.sort(key=lambda x: x["date"])

    if not all_days:
        return 0, 0

    date_map = {day["date"].date(): day["count"] for day in all_days}

    start_date = min(date_map.keys())
    end_date = max(date_map.keys())

    longest_streak = 0
    temp_streak = 0
    current_date = start_date

    while current_date <= end_date:
        has_contributions = date_map.get(current_date, 0) > 0

        if has_contributions:
            temp_streak += 1
        else:
            if temp_streak > 0:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 0

        current_date += timedelta(days=1)

    if temp_streak > 0:
        longest_streak = max(longest_streak, temp_streak)

    today = datetime.now().date()
    one_year_ago = today - timedelta(days=365)

    current_streak = 0
    check_date = today

    while check_date >= one_year_ago and check_date >= start_date:
        if date_map.get(check_date, 0) > 0:
            current_streak += 1
        else:
            break
        check_date -= timedelta(days=1)

    return current_streak, longest_streak


def calculate_streaks(weeks):
    """Legacy function - kept for backwards compatibility."""
    return calculate_streaks_all_time(weeks)


def main():
    """Main function to orchestrate the language statistics and contribution data generation."""
    print("Starting language statistics and contribution data generation...")

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

        contribution_data = get_contribution_data()

        svg_content = generate_svg(top_langs, total_size, contribution_data)

        os.makedirs(os.path.dirname(SVG_PATH), exist_ok=True)

        with open(SVG_PATH, "w", encoding="utf-8") as f:
            f.write(svg_content)

        print(f"\nSVG successfully written to {SVG_PATH}")
        print(f"Total code size analyzed (bytes): {total_size:,}")
        if contribution_data:
            print(f"Total contributions: {contribution_data['total_contributions']:,}")
            print(f"Years analyzed: {contribution_data.get('years_fetched', 1)}")
            print(f"Current streak: {contribution_data['current_streak']} days")
            print(f"Longest streak: {contribution_data['longest_streak']} days")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
