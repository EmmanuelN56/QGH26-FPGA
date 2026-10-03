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
