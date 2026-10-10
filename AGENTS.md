# Grandstand: notes for coding agents

Goal: deploy Grandstand, a read-only progress board for the developer's GitHub Projects v2 board.

1. Create a repo from this template (public if the developer wants free Pages).
2. Write `board.config.json`. Find the project number and status names with `gh api graphql` (query `projectV2(number:N){field(name:"Status"){... on ProjectV2SingleSelectField{options{name}}}}`). Put the statuses that need the human in `needsMe` and the in-progress ones in `building`.
3. Ask the developer for a token that can read the project, and store it only as the Actions secret `BOARD_TOKEN`: `gh secret set BOARD_TOKEN -R <owner>/<repo>`. Never commit it, never print it.
4. Enable Pages: `gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow`.
5. `gh workflow run refresh.yml -R <owner>/<repo>`, wait for success, open the Pages URL at 390 px wide and check it.
6. Keep your board's Status field current. The page only shows what the board says.

Do not add write access. Do not copy issue bodies into the repo.
