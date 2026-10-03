# Human review and Git commands



The trading core, minimum-gap source, matching tested bitstream and evidence

are uncommitted. Review the source/evidence before staging. No Git history or

remote action has been performed. Final release evidence is `results/release_zero_gap_20261003T180901633856Z/`.

The original baseline and failed experiments remain preserved for comparison.



Copy these PowerShell commands from the repository root. The per-command

`safe.directory` option trusts only this known UNC checkout for Windows Git;

it does not change global configuration. The explicit path list includes the

initial trading-core implementation and its new latency work. `results` is the

project evidence directory; inspect the status before staging it.



```powershell

git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA status --short

git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA diff --check

git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA diff

$reviewPaths = @(

    '.gitignore',

    'README.md',

    'PROJECT_BRIEF.md',

    'docs/board_bringup.md',

    'docs/latency_optimization.md',

    'docs/grading_report.md',

    'docs/lut_optimization_study.md',

    'docs/human_review.md',

    'gowin/README.md',

    'gowin/build_uart.tcl',

    'src/top.v',

    'src/packet_controller.v',

    'src/trade_engine.v',

    'scripts/reference_model.py',

    'scripts/generate_vectors.py',

    'scripts/run_regression.py',

    'scripts/capture_board_tests.py',

    'scripts/capture_vector_stress.py',

    'scripts/prepare_latency_sweep.py',

    'testbench/top_tb.v',

    'testbench/top_sessions_tb.v',

    'testbench/trade_engine_tb.v',

    'testbench/vectors',

    'bitstream/trade_core.fs',

    'results'

)

git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA add -- $reviewPaths

git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA commit -m "Implement and validate minimum-gap FPGA trading core"

git -c safe.directory=//wsl.localhost/Ubuntu-26.04/home/hao/QuizletFPGA push

```



Fill the remaining human metadata and verify repository/public submission

access before freezing the full final Git SHA for Devpost. Commit-message

suggestion describes the complete currently uncommitted implementation.



Latest organizer-rubric revalidation and comparison: `docs/grading_report.md`; fresh saved evidence: `results/regrade_20261003T183908493740Z/`, `results/board_20261003T185249884957Z/`, and `results/stress_20261003T185302954524Z/`. The review path list includes the report, configurable simulation timeout and saved results.



Area-study review: `docs/lut_optimization_study.md` and `results/area_20261003T192105403559Z/`. Candidate files are experimental; `bitstream/trade_core.fs` and live `src/` were preserved. The path list above includes the study and saved evidence.




## Native recovery and candidate publication

Use `C:/Users/Lenovo/Downloads/QuizletFPGA`. Earlier commands above refer to the
previous working tree and its historical release. Review the recovered source,
`docs/repository_recovery.md`, and the candidate publication script first.

```powershell
Set-Location 'C:\Users\Lenovo\Downloads\QuizletFPGA'
git status --short
git diff --check
git diff
Get-Content .\scripts\publish_lut_candidate_branches.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_lut_candidate_branches.ps1
```

The script contains explicit staging paths and the factual commit messages,
then pushes each candidate branch. It must be run by a human; no publication
commands were executed during recovery. The isolated publication checkout is
based on fetched origin/main, so the older local main does not need a pull or
stash before running it.

If a run stops before the shared snapshot commit, resume its prepared checkout:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_lut_candidate_branches.ps1 -ResumeWorktree 'C:\Users\Lenovo\AppData\Local\GatorFPGA\candidate_publication_bdf19fc2c1854f059c99be1b22d21220'
```

Resume requires the same repository, the comparison-base branch, an empty
index, and a HEAD equal to the freshly fetched origin/main. It recopies the
reviewed publication inputs before showing the diff and asking for `publish`.
Windows CRLF line endings are accepted; actual trailing spaces/tabs remain
errors in active source and documents. Archived results retain vendor formatting
and are excluded from whitespace lint so their recorded bytes remain intact.

## Full-range organizer clarification review

The 230/234 comparison branches already exist locally and on origin. Do not
rerun their publisher to apply this update: its existing-branch guard is
intentional. Prepare a new native review checkout from the shared comparison
snapshot, then copy only this update from the Downloads repository:

```powershell
Set-Location 'C:\Users\Lenovo\Downloads\QuizletFPGA'
$updateSource = (Get-Location).Path
$updateReview = 'C:\Users\Lenovo\Downloads\QuizletFPGA-fullrange-review'
if (Test-Path -LiteralPath $updateReview) { throw 'Review directory already exists; inspect before continuing.' }
git worktree add -b codex/fullrange-ranking-review $updateReview codex/lut-comparison-base
if ($LASTEXITCODE -ne 0) { throw 'Git could not create the review checkout; no files were copied.' }
$updatePaths = @(
    'PROJECT_BRIEF.md',
    'docs/grading_report.md',
    'docs/lut_optimization_study.md',
    'docs/human_review.md',
    'docs/official/SCORING_AND_RANKING_CLARIFICATION.md',
    'scripts/22_robust_uart_test_fullrange.py',
    'scripts/verify_fullrange_candidates.py',
    'scripts/publish_lut_candidate_branches.ps1',
    'results/fullrange_20261003_ranking'
)
foreach ($relative in $updatePaths) {
    $from = Join-Path $updateSource $relative
    $to = Join-Path $updateReview $relative
    [IO.Directory]::CreateDirectory((Split-Path -Parent $to)) | Out-Null
    Copy-Item -LiteralPath $from -Destination $to -Recurse -Force
}
Set-Location -LiteralPath $updateReview
git status --short
git diff --check
git diff
git add -- $updatePaths
git diff --cached --check
git commit -m "Add organizer full-range validation and ranking requirements"
git push -u origin codex/fullrange-ranking-review
```

The review branch keeps the shared baseline source active and the exact
experimental sources/bitstreams archived. The human team can incorporate this
common validation update into its candidate branches after reviewing it.
No physical qualification or final candidate selection is claimed.

## Separate block-RAM test branch

Run this manually from the original native Downloads repository:

```powershell
Set-Location 'C:\Users\Lenovo\Downloads\QuizletFPGA'
Get-Content .\scripts\publish_blockram_candidate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_blockram_candidate.ps1
```

The script verifies the eight exact context_ram build inputs, matching bitstream,
312-Logic/179-register synthesis summary and fresh simulation evidence. It fetches
origin/main and prepares a separate native worktree for codex/logic-312-blockram.
The new branch has the block-RAM source active, its matching .fs and build identity,
paired-engine bench, unchanged organizer test copies, clarification and fresh
full-range evidence. It preserves other files from the fetched main.

Review the displayed status/diff, then type `publish` to execute the explicit
staging paths, commit and push defined in the script. Its Git commands include:

```powershell
git status --short
git diff --check
git diff
git add -- $reviewPaths
git diff --cached --check
git commit -m "Prepare block-RAM candidate for total-logic qualification testing"
git push -u origin codex/logic-312-blockram
```

`$reviewPaths` is the explicit path array in the script; run the script, not this
internal excerpt in an unrelated shell. Existing target branches are rejected.
If preparation stops before a commit, use the printed `-ResumeWorktree` command
only after reviewing that checkout. Resume verifies repository, branch, base HEAD
and empty staging index. A `-PrepareOnly` invocation produces a file snapshot
without running any Git commands. No board programming occurs in either mode.

Optimization now starts from the archived 312-Logic block-RAM candidate and
minimizes the complete Logic row. Keep this identified candidate as the test
baseline while future experiments remain separate. Physical testing with the
new organizer suite remains pending; see docs/logic_optimization.md.
