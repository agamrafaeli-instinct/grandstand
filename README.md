# HN explorer board

A phone-first, read-only view of the project board for the Hacker News explorer: what needs a decision, what is being built, every epic with its progress, and the pipeline.

- Source of truth: the GitHub project https://github.com/users/agamrafaeli-instinct/projects/1
- `scripts/fetch_board.py` reads the project with the GitHub API and writes `data/board.json`. Finished (Done) items are counted, not listed.
- A GitHub Action refreshes the data and redeploys Pages about every 30 minutes, and on every push. Nothing here edits the board.
- If the repo sees no activity for 60 days GitHub pauses scheduled runs; push any commit to resume.
