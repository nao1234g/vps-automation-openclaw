# /commit skill

Stage all modified tracked files, write a concise commit message, and commit.

## Steps

1. Run `git status` and `git diff --stat` to see what changed
2. Run `git log --oneline -5` to match existing commit style
3. Stage relevant files (prefer specific paths over `git add -A` to avoid .env leaks)
4. Write a commit message: `type: one-line summary in English or Japanese`
   - Prefix: `feat` / `fix` / `docs` / `refactor` / `chore`
   - Under 72 characters
   - Add `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` trailer
5. Commit using HEREDOC format
6. Show `git log --oneline -3` to confirm

## Rules
- NEVER push without explicit user request
- NEVER use `--no-verify`
- NEVER amend previous commits unless explicitly asked
- If nothing to commit, say so and stop
