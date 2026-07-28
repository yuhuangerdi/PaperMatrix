# PaperMatrix agent workflow

- When a coherent, independently verifiable change is complete and its relevant checks pass, commit it and push the current branch unless the user explicitly asks not to.
- Do not let multiple unrelated completed changes accumulate in one uncommitted worktree.
- Before committing, review the worktree and exclude unrelated user changes. If ownership or scope is ambiguous, ask before staging.
- Report the commit and push result only after each command succeeds.
