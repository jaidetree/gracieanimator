# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## Project board

Issues are tracked on the **Gracie Animator Django Migration** GitHub Project (project #7, owner `jaidetree`). The board groups by a single-select **Status** field with these options:

`Backlog` → `Ready` → `In progress` → `In review` → `Done`

Identifiers (stable; only change if the board is rebuilt):

| Item | ID |
| --- | --- |
| Project ID | `PVT_kwHOAAkB2c4BbxyK` |
| Status field ID | `PVTSSF_lAHOAAkB2c4BbxyKzhWf1GQ` |
| `In progress` option | `47fc9ee4` |
| `In review` option | `df73e18b` |
| `Done` option | `98236657` |

### Move an issue to a status

- **Starting work**: move the issue to `In progress` (option `47fc9ee4`).
- **Finishing work**: move it to `In review` (option `df73e18b`) — this signals the change awaits manual testing by a human. Only a human moves an issue to `Done`.

`gh project item-edit` needs the *project item ID*, not the issue number. Look it up, then edit:

```bash
PROJECT_ID="PVT_kwHOAAkB2c4BbxyK"
STATUS_FIELD="PVTSSF_lAHOAAkB2c4BbxyKzhWf1GQ"
IN_REVIEW="df73e18b"
N=<issue-number>

ITEM_ID=$(gh project item-list 7 --owner jaidetree --format json \
  | python3 -c "import json,sys; print(next(i['id'] for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==$N))")

gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" \
  --field-id "$STATUS_FIELD" --single-select-option-id "$IN_REVIEW"
```

Swap `--single-select-option-id` for another option ID from the table above to move to a different status.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` then keep only `authorAssociation` of `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or `NONE` (drop `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either — resolve with `gh pr view 42` and fall back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.
