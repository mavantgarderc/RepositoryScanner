# RepositoryScanner

Account analyzer based on GitHub's language statistics (byte-based code size from public & private repos) using the GitHub API, exporting a beautiful SVG card of your top languages.

The card:

- Shows your **top 6 languages** by total code size
- Uses a **Kanagawa paper‑ink**–inspired theme
- Updates automatically every 24 hours via **GitHub Actions**

> **How languages are measured**  
> GitHub’s language API returns the number of **bytes** of code per language.  
> The percentages in this card are based on those byte-based sizes (not raw line counts), which matches how GitHub itself computes language stats.

---

## Demo

Once set up, your card will live at:

```md
https://raw.githubusercontent.com/<username>/RepositoryScanner/main/assets/languages.svg
```

Example usage in a profile README:

```md
## My Coding Languages

![Languages](https://raw.githubusercontent.com/<username>/RepositoryScanner/main/assets/languages.svg)
```

Replace `<username>` with your GitHub username.

> If the card doesn’t seem to update right away, append a dummy query parameter
> like `?v=1` to bypass browser caching:
>
> ```md
> ![Languages](https://raw.githubusercontent.com/<username>/RepositoryScanner/main/assets/languages.svg?v=1)
> ```

---

## Features

- **Comprehensive analysis**: scans both public and private repositories
- **Top 6 languages** by total code size
- **Kanagawa theme** for a clean, paper‑ink look
- **Auto‑updates daily** via GitHub Actions
- **SVG output** that looks sharp anywhere (profile, docs, dashboards)
- **Configurable** excluded languages and colors

---

## Quick Start (Recommended: GitHub Actions)

### 1. Fork this repository

1. Click **Fork** at the top‑right of this page.
2. Work from your forked copy (`<username>/RepositoryScanner`).

### 2. Create a GitHub Personal Access Token

1. Go to  
   https://github.com/settings/tokens
2. Click **“Generate new token (classic)”** or create a fine-grained token.
3. Give it a name (e.g. `RepositoryScanner Token`).
4. Enable scopes:
   - `repo` (for private repositories) or `public_repo` if you only care about public
   - `read:user`
5. Generate and **copy** the token (you won’t see it again).

### 3. Add repository secrets

In your **forked** repository:

1. Go to **Settings → Secrets and variables → Actions**.
2. Click **“New repository secret”** and add:

| Secret name       | Required | Example value          | Notes                                     |
| ----------------- | -------- | ---------------------- | ----------------------------------------- |
| `GH_TOKEN`        | ✅       | `ghp_xxxxxxxxxxxx`     | Your personal access token                |
| `GITHUB_USERNAME` | ✅       | `your_github_username` | The account to analyze                    |
| `EXCLUDED_LANGS`  | ❌       | `HTML,CSS,Dockerfile`  | Comma‑separated list of languages to skip |

> `GITHUB_USERNAME` is used by the script and in the workflow.  
> For backwards compatibility, `USERNAME` is also supported and will be used if `GITHUB_USERNAME` is not set.  
> `EXCLUDED_LANGS` is optional; use it to ignore markup / infra languages.

### 4. Run the workflow once

1. Go to the **Actions** tab in your forked repo.
2. Click **“Update Language Stats”**.
3. Click **“Run workflow”** (select `main`).
4. Wait for it to finish (usually 30–60 seconds).

When it succeeds, you should see a new/updated file:

```text
assets/languages.svg
```

in your repository.

### 5. Add the card to your profile

In your `username/username` profile repo, add:

```md
## My Coding Languages

![Languages](https://raw.githubusercontent.com/<username>/RepositoryScanner/main/assets/languages.svg)
```

Replace `<username>` with your GitHub username.

---

## Local Development

You can run the generator locally for debugging or customization.

### 1. Clone your fork

```bash
git clone https://github.com/<username>/RepositoryScanner.git
cd RepositoryScanner
```

### 2. Set up Python & dependencies

Use Python 3.10+ (3.11 recommended).

```bash
# Optional but recommended:
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install required packages
pip install --upgrade pip
pip install requests python-dotenv
```

> The `requirements.txt` may be updated later; for now the core deps are `requests` and `python-dotenv`.

### 3. Configure environment variables

You can either:

**Option A – `.env` file**

1. Copy the example:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in:

   ```dotenv
   GH_TOKEN=ghp_xxxxxxxxxxxx
   GITHUB_USERNAME=your_github_username
   EXCLUDED_LANGS=HTML,CSS,Dockerfile
   ```

**Option B – Shell exports**

```bash
export GH_TOKEN="ghp_xxxxxxxxxxxx"
export GITHUB_USERNAME="your_github_username"
export EXCLUDED_LANGS="HTML,CSS,Dockerfile"
```

> Note: On some systems, `USERNAME` is already set by the OS (e.g. your local login name).  
> Prefer `GITHUB_USERNAME` to avoid confusion. For backwards compatibility, `USERNAME` is still supported.

### 4. Run the generator

From the **repository root**:

```bash
python scripts/fetch_languages.py
```

If everything is configured correctly, you’ll get:

```text
assets/languages.svg
```

Open it in a browser or image viewer to preview.

---

## GitHub Actions Automation

The workflow file is:

```text
.github/workflows/update-chart.yaml
```

It is configured to:

- Run **daily at 00:00 UTC**:
  ```yaml
  schedule:
    - cron: "0 0 * * *"
  ```
- Run on demand via **“Run workflow”**
- Commit updated `assets/languages.svg` back to `main`

### Changing the schedule

Edit `.github/workflows/update-chart.yaml` and adjust the `cron` line. Examples:

- Every 12 hours:
  ```yaml
  - cron: "0 */12 * * *"
  ```
- Every Monday at midnight:
  ```yaml
  - cron: "0 0 * * 1"
  ```
- First day of every month:
  ```yaml
  - cron: "0 0 1 * *"
  ```

---

## Configuration

### Environment variables

| Variable          | Required | Description                         | Example               |
| ----------------- | -------- | ----------------------------------- | --------------------- |
| `GH_TOKEN`        | ✅       | GitHub personal access token        | `ghp_xxxxxxxxxxxx`    |
| `GITHUB_USERNAME` | ✅       | GitHub username to analyze          | `mavantgarderc`       |
| `EXCLUDED_LANGS`  | ❌       | Comma‑separated languages to ignore | `HTML,CSS,Dockerfile` |

> For backwards compatibility, `USERNAME` is also supported and will be used if `GITHUB_USERNAME` is not set.  
> If `GH_TOKEN` is not set, only **public** repositories will be analyzed and GitHub’s unauthenticated rate limits will apply. Using a token is strongly recommended.

### Colors

The Kanagawa color palette and per‑language colors are defined in:

```text
scripts/colors.py
```

Adjust them there to change the chart’s look.

### Layout

The SVG layout (sizes, spacing, font sizes, bar widths, etc.) is defined in the SVG generation logic inside:

```text
scripts/fetch_languages.py
```

Modify that function if you want a different layout.

---

## Security & Privacy

- Uses **GitHub’s API** to read:
  - Your list of repositories
  - Language statistics per repository
- Does **not** read your actual code content.
- Tokens are read from:
  - Local `.env` / environment (for local development)
  - **GitHub Secrets** (for Actions), never committed to the repo.

**Best practices:**

- Keep your `GH_TOKEN` private and never commit it.
- Use GitHub Actions **secrets** for tokens.
- If you only care about **public** repos, you can use a token with just `public_repo` instead of full `repo`.

---

## Troubleshooting

### “401 Unauthorized” or API errors

- Ensure `GH_TOKEN` is set and valid.
- Confirm it has `repo` + `read:user` scopes (or `public_repo` if you only use public repos).
- Without a token, you may hit GitHub’s unauthenticated rate limits quickly.

### “No language data found”

Possible causes:

- All repos are forks (these are filtered out).
- All languages are in `EXCLUDED_LANGS`.
- Token doesn’t have access to private repos you expect to see.
- You’re running without `GH_TOKEN` and GitHub has rate-limited unauthenticated requests.

### Workflow not running

- Check that **GitHub Actions** are enabled for your repo.
- Ensure the workflow file is named and located exactly as:

  ```text
  .github/workflows/update-chart.yaml
  ```

- Verify YAML syntax (you can use the Actions editor’s validator).
- Confirm you pushed changes to the `main` branch (or adjust the workflow branches).

---

## Contributing

Contributions are welcome!

- Report bugs / issues
- Suggest new features
- Improve design and theming
- Enhance documentation
- Add more configuration options

Open a PR or issue on GitHub.

---

## License

This project is distributed under the [MIT License](LICENSE).

Inspired by:

- https://github.com/anuraghazra/github-readme-stats

Kanagawa color theme influenced by:

- https://github.com/rebelot/kanagawa-paper.nvim
