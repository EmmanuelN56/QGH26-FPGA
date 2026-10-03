# Instructions for Coding Agents

Before changing this repository, read [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) completely. It is the implementation contract for the Gator Quant Hacks FPGA trading core.

Key rules:

- Never run `git add`, `git commit`, `git push`, `git tag`, `git merge`, `git rebase`, or create a pull request. The human team owns all Git history and remote actions.
- Read-only Git commands such as `git status`, `git diff`, `git log`, and `git show` are allowed when needed.
- After making changes, report the changed files and provide copy-paste commands the human can use to review, stage, commit, and push them.
- Never add AI attribution, generated-by notices, bot signatures, `Co-authored-by` trailers, or references to an agent in source files, documentation, commit-message suggestions, or release metadata unless a human explicitly requests that disclosure.
- Suggested commit messages must be ordinary, factual descriptions of the project change. The human must execute the commit.
- Organizer artifacts and tests override repository prose if they conflict.
- Do not invent missing protocol, pin, build, or programming details. Mark them as TODO and report the missing source.
- Keep UART transport, packet control, and strategy logic separately testable.
- Preserve exact byte order, per-item state, index-zero reset order, floor-average behavior, and held-action semantics.
- Do not optimize until the reference model and regression tests pass.
- For every optimization, record correctness, LUTs, registers, B-SRAM, timing, and physical-board latency before and after.
- Never put dashboards, databases, AI APIs, or voice services in the official decision path.
- Do not claim physical-board validation unless a connected board was programmed and the resulting logs/CSVs were saved.

Current source-of-truth and status fields are in `PROJECT_BRIEF.md`. Research references are in `outputs/`.

## Human-owned Git workflow

Agents stop after editing, testing, and showing the diff. When a change is ready, provide commands in this form for a human to inspect and run:

```powershell
git status --short
git diff --check
git diff
git add <explicit paths>
git commit -m "Describe the project change"
git push
```

Always list explicit paths in the suggested `git add` command. Do not suggest `git add .` when unrelated files may exist.
