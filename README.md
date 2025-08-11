# RepositoryScanner
Account analyzer based on logical lines of code (public &amp; private repo), exports svg card

A GitHub profile card showing the top programming languages you use, styled with the **Kanagawa-paper-ink** theme.  
The data comes from the GitHub API and updates automatically every 24 hours via GitHub Actions.

![Most Used Languages](assets/languages.svg)

---

## Features
- **Live data** from your public and private repositories.
- **Top 6 languages** by total lines of code.
- **Kanagawa-paper-ink** color palette.
- **Bar chart layout** with optional animation.
- Auto-updates every 24h UTC.

---

## Local Usage

### 1. Clone the repo
```bash
git clone https://github.com/mavantgarderc/RepositoryScanner.git
cd RepositoryScanner
````

### 2. Create a GitHub Personal Access Token

* Go to **Settings → Developer settings → Personal access tokens (classic)**.
* Click **Generate new token (classic)**.
* Check:

  * `repo` (for private repos)
  * `read:user`
* Copy the token.

### 3. Set the token in your shell

```bash
export GH_TOKEN='your_token_here'
```

### 4. Install dependencies

```bash
pip install requests
```

### 5. Run the generator

```bash
python3 scripts/fetch_languages.py
```

* The script will create/update:

```
assets/languages.svg
```

### 6. Preview

Open `assets/languages.svg` in your browser.

---

## GitHub Actions Auto-Update

### 1. Add your token to repo secrets

* Go to **Repo → Settings → Secrets → Actions**.
* Add:

  * Name: `GH_TOKEN`
  * Value: your token

### 2. Workflow file

The `.github/workflows/update-languages.yml` is already set up to:

* Run every 24h UTC (`cron: "0 0 * * *"`).
* Commit the updated `assets/languages.svg`.

### 3. First run

* Push the repo to GitHub.
* In the **Actions** tab, run the workflow manually once to generate the first card.

---

## Add to Your Profile README

In your GitHub profile repo (`<username>/<username>`):

```markdown
![Most Used Languages](https://raw.githubusercontent.com/mavantgarderc/KanagawaLanguagesUsed/main/assets/languages.svg)
```

---

## Notes

* The script uses `/user/repos` endpoint for private+public repo access.
* If you change your GitHub username, update `USERNAME` in `scripts/fetch_languages.py`.
* Forked repos are ignored by default; you can modify the filter in `get_repos()`.

---
