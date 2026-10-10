# Grandstand

### Watch your coding agent work.

Your agent is building. You are on your phone. **Grandstand** is the front-row seat: a clean, read-only page that shows what needs you, what is being built and how far each epic has come, straight from your GitHub project board. No login, no server, no new tool to learn.

**Live demo** (the board of a real project, refreshed every 30 minutes): https://agamrafaeli-instinct.github.io/grandstand/

- Free: runs on GitHub Actions and GitHub Pages.
- Read-only: it can look, it cannot touch your board.
- Phone first: one column, light and dark, no sideways scroll.
- Agent friendly: a coding agent can set it up in one pass from `AGENTS.md`.

**Grandstand is an eyes-only progress board for your GitHub project, built for your phone.** Point it at a GitHub Projects (v2) board and get a static page that shows what needs you, what is being built, every epic with its progress, and the whole pipeline. It reads. It never writes.

Made so a coding agent can show a developer how the work is going, without a login, a server or a database. The demo shows the board of the Hacker News explorer project.

## What you get

- **Needs me**: items in the statuses you name (for example "Needs decision", "QA").
- **Building**: items in progress or ready to build.
- **Epics**: issues with sub-issues or an `epic` label, grouped by a field such as Horizon, with a progress bar.
- **Pipeline**: all open work by status, in your board's column order.
- Finished work is hidden by default and counted in the footer.
- Light and dark, one column, no sideways scroll at 320 px.

## How it works

1. `scripts/fetch_board.py` reads your project through the GitHub GraphQL API and writes `data/board.json`.
2. A GitHub Action runs every 30 minutes, on every push and on demand. It bakes the JSON, stages `index.html` plus the data and deploys GitHub Pages.
3. The page is plain HTML and JavaScript. No tracking, no build step, no dependencies. Your token only exists in Actions secrets and is never written to the repo or the page.

## Set it up in about 5 minutes

1. Click **Use this template** (or fork). Keep the repo public if you want free Pages.
2. Edit `board.config.json` (see below): your GitHub login, owner type (`user` or `org`), project number (the number in `github.com/users/<you>/projects/<n>`) and the status names you use.
3. Create a token that can read the project: a classic personal access token with `read:project` and `repo` (or `public_repo` for public repos), or a fine-grained token with Projects read access plus Issues read. Save it as a repo secret named `BOARD_TOKEN` (Settings, Secrets and variables, Actions).
4. In Settings, Pages, set the source to **GitHub Actions**.
5. Run the **Refresh board and deploy Pages** workflow once. Your board is at `https://<you>.github.io/<repo>/`.

### For a coding agent

Everything needed is in this repo, no UI steps beyond the secret. With `gh` authenticated: create the repo from the template, write `board.config.json`, `gh secret set BOARD_TOKEN`, `gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow`, then `gh workflow run refresh.yml`. See `AGENTS.md`.

## Config (`board.config.json`)

| Key | Meaning |
|---|---|
| `title` | Page title. |
| `owner`, `ownerType` | GitHub login that owns the project, and `user` or `org`. |
| `project` | Project number. |
| `statusField` | The single-select field that holds the stage. Default `Status`. |
| `needsMe` | Status names that need a human. Shown in the first tab. |
| `building` | Status names that mean work in progress or ready. |
| `hideStatuses` | Status names hidden from every tab. Default `["Done"]`. Closed and merged items are always hidden. |
| `groupField`, `groupOrder` | Optional single-select field used to group epics (for example `Horizon`: Now, Next, Later). |
| `epicLabel` | Label that marks an epic. Issues with sub-issues, or titled `[Epic]`, also count. |

## Limits

- Read-only by design. Nothing here edits your board.
- GitHub pauses scheduled workflows after 60 days with no repo activity. Any push resumes them.
- Single-select fields only for status and grouping. Items from several repos work. Iteration and number fields are not shown.
- The page shows titles, status, group and progress. Nothing else from the issue is copied.

## Status

Early, built in public. Issues and pull requests are welcome. Licence: MIT.

## Set up a new board (worked example: agamrafaeli-instinct/grandstand-board)
1. Create a GitHub Project with a single-select Status field. The names are yours (the example uses Defined, Ready, Dev, Done).
2. Make a new repo for the instance. It holds only `board.config.json` and one workflow. No code is copied.
3. In `board.config.json` set `owner`, `ownerType`, `project` (the number), `statusField`, `hideStatuses`, `needsMe`, `building`, `tiles` (label and status per stat tile) and, for the pulse, `workRepo` plus `workRunName` (a substring of the workflow name to watch, or null to use the Dev ticket only).
4. Copy `.github/workflows/refresh.yml` from the example repo. It checks out this repo as `tool/`, runs `python3 tool/scripts/fetch_board.py`, then publishes `tool/index.html` with `data/board.json`.
5. Add a repo secret `BOARD_TOKEN`: a token that can read the project and the watched repo's Actions.
6. Turn on Pages with the "GitHub Actions" source, then run the workflow once.
