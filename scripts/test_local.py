#!/usr/bin/env python3

import os
import sys
from pathlib import Path


def setup_test_environment():

    username = input("Enter your GitHub username: ").strip()
    if not username:
        print("Username is required")
        sys.exit(1)

    print("\nGitHub Personal Access Token:")
    print("   - For public repos only: press Enter to skip")
    print("   - For complete data: create token at https://github.com/settings/tokens")
    print(
        "   - Token needs 'repo' scope for private repos, or no scopes for public only"
    )

    token = input("Enter your GitHub token (or press Enter to skip): ").strip()

    print("\nExcluded languages (optional):")
    print("   - Enter comma-separated languages to exclude (e.g., HTML,CSS,Dockerfile)")
    print("   - Or press Enter to include all languages")

    excluded = input("Excluded languages: ").strip()

    print("\nTop languages to show (optional):")
    print("   - Enter a positive integer (e.g., 6, 8, 10)")
    print("   - Press Enter to use the default (6)")

    top_langs_input = input("Top languages (default 6): ").strip()

    os.environ["GITHUB_USERNAME"] = username
    os.environ["USERNAME"] = username

    if token:
        os.environ["GH_TOKEN"] = token
        print("Token provided - will include private repos")
    else:
        print(
            "No token provided - only public repos will be analyzed (rate limits will be lower)"
        )

    if excluded:
        os.environ["EXCLUDED_LANGS"] = excluded
        print(f"Will exclude: {excluded}")

    if top_langs_input:
        try:
            n = int(top_langs_input)
            if n > 0:
                os.environ["TOP_LANGS"] = top_langs_input
                print(f"Will show top {n} languages")
            else:
                print("Top languages must be positive - using default (6)")
        except ValueError:
            print("Invalid number for top languages - using default (6)")

    return username, token


def display_language_stats(langs_data, excluded_data, total_lines, excluded_total):
    if not langs_data and not excluded_data:
        print("No language data to display")
        return

    print(f"\nLanguage Statistics")
    print("=" * 50)

    unique_repos = {
        repo_name for repo_data in langs_data.values() for repo_name in repo_data
    }
    print(f"Total repositories analyzed: {len(unique_repos)}")
    print(f"Total code size (bytes): {total_lines:,}")
    print(f"Languages found: {len(langs_data)}")

    sorted_langs = sorted(
        langs_data.items(), key=lambda x: sum(x[1].values()), reverse=True
    )

    print(f"\nAll Languages:")
    print("-" * 50)

    for lang, repo_data in sorted_langs:
        lang_total = sum(repo_data.values())
        percentage = (lang_total / total_lines) * 100 if total_lines else 0
        print(f"{lang}: {lang_total:,} bytes ({percentage:.2f}%)")

    if excluded_data:
        print(f"\nExcluded Languages:")
        print("-" * 50)

        sorted_excluded = sorted(
            excluded_data.items(), key=lambda x: sum(x[1].values()), reverse=True
        )

        for lang, repo_data in sorted_excluded:
            lang_total = sum(repo_data.values())
            total_with_excluded = total_lines + excluded_total
            percentage = (
                (lang_total / total_with_excluded) * 100 if total_with_excluded else 0
            )
            print(f"{lang}: {lang_total:,} bytes ({percentage:.2f}%)")

        print(f"\nTotal excluded bytes: {excluded_total:,}")
        print(
            f"Total code size including excluded (bytes): "
            f"{total_lines + excluded_total:,}"
        )


def run_test_with_stats():
    print("\n" + "=" * 50)
    print("Running language stats generation...")
    print("=" * 50)

    try:
        sys.path.insert(0, "scripts")

        from fetch_languages import EXCLUDED_LANGS, TOP_N, get_language_data, get_repos

        repos = get_repos()

        langs_detailed = {}
        excluded_detailed = {}
        total_lines = 0
        excluded_total = 0

        print(f"Processing {len(repos)} repositories...")

        for repo in repos:
            try:
                langs = get_language_data(repo)
                repo_name = repo["name"]

                for lang, lines in langs.items():
                    if lang.lower() in EXCLUDED_LANGS:
                        if lang not in excluded_detailed:
                            excluded_detailed[lang] = {}
                        excluded_detailed[lang][repo_name] = lines
                        excluded_total += lines
                    else:
                        if lang not in langs_detailed:
                            langs_detailed[lang] = {}
                        langs_detailed[lang][repo_name] = lines
                        total_lines += lines

            except Exception as e:
                print(f"Error processing {repo['name']}: {e}")
                continue

        if total_lines == 0 and excluded_total == 0:
            print("No language data found!")
            return False

        display_language_stats(
            langs_detailed, excluded_detailed, total_lines, excluded_total
        )

        print(f"\nGenerating SVG...")

        import fetch_languages

        langs_simple = {}
        for lang, repo_data in langs_detailed.items():
            langs_simple[lang] = sum(repo_data.values())

        top_langs = sorted(langs_simple.items(), key=lambda x: x[1], reverse=True)[
            :TOP_N
        ]

        svg_content = fetch_languages.generate_svg(top_langs, total_lines)

        svg_path = Path("assets/languages.svg")
        os.makedirs(svg_path.parent, exist_ok=True)

        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        print("Script completed successfully!")

        if svg_path.exists():
            size = svg_path.stat().st_size
            print(f"SVG created: {svg_path} ({size:,} bytes)")

            import webbrowser

            choice = input("\nopen in browser? (y/n): ").lower()
            if choice == "y":
                webbrowser.open(f"file://{svg_path.absolute()}")
        else:
            print("SVG file was not created")

    except ImportError as e:
        print(f"Could not import required modules: {e}")
        print(
            "Make sure fetch_languages.py and colors.py are in the scripts/ directory"
        )
    except Exception as e:
        print(f"Error running script: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def main():
    print("Local Language Stats Tester")
    print("=" * 30)

    if not Path("scripts/fetch_languages.py").exists():
        print("Could not find scripts/fetch_languages.py")
        print("Make sure you're running this from the repository root")
        sys.exit(1)

    if not Path("scripts/colors.py").exists():
        print("Could not find scripts/colors.py")
        print("Make sure colors.py is in the scripts/ directory")
        sys.exit(1)

    username, token = setup_test_environment()

    success = run_test_with_stats()

    if success:
        print(f"\nTest completed! Check assets/languages.svg")
        print(f"Your GitHub: https://github.com/{username}")
    else:
        print("\nTest failed - check error messages above")


if __name__ == "__main__":
    main()
