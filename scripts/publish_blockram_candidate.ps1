# Run manually. Prepares one exact candidate and publishes its separate branch.
[CmdletBinding()]
param(
    [switch]$PrepareOnly,
    [string]$ResumeWorktree
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$gitRoot = $repoRoot
$branch = 'codex/logic-312-blockram'
$study = 'results/area_20261003T192105403559Z'
$candidateRelative = "$study/context_ram"
$candidateRoot = Join-Path $repoRoot $candidateRelative
$expectedHash = '825bf4d70b30f3ed7f01a09e725d65304f37f7b26c551289ea06fd13b947ef8d'
$gitExe = 'C:/Program Files/Git/cmd/git.exe'
if (-not (Test-Path -LiteralPath $gitExe)) { $gitExe = (Get-Command git -ErrorAction Stop).Source }
function Invoke-ProjectGit {
    & $gitExe -C $gitRoot -c core.autocrlf=false -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol -c "safe.directory=$($gitRoot.Replace('\','/'))" @args
    if ($LASTEXITCODE -ne 0) { throw "Git failed: $args" }
}
function Copy-ReviewedPath($relative, $destinationRoot) {
    $source = Join-Path $repoRoot $relative
    if (Test-Path -LiteralPath $source -PathType Leaf) { $files = @(Get-Item -LiteralPath $source) }
    else { $files = @(Get-ChildItem -LiteralPath $source -Recurse -File -Force | Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' }) }
    foreach ($file in $files) {
        $suffix = $file.FullName.Substring($repoRoot.Length).TrimStart([char[]]'\/')
        $target = Join-Path $destinationRoot $suffix
        [IO.Directory]::CreateDirectory((Split-Path -Parent $target)) | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target -Force
    }
}
function Assert-BuildIdentity($root) {
    foreach ($entry in $metadata.source_sha256.PSObject.Properties) {
        $actual = (Get-FileHash -LiteralPath (Join-Path $root $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $entry.Value) { throw "Build input mismatch: $($entry.Name)" }
    }
    $actual = (Get-FileHash -LiteralPath (Join-Path $root 'bitstream/trade_core.fs') -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expectedHash) { throw 'Active bitstream hash mismatch.' }
}
function Assert-PublicationWhitespace {
    Invoke-ProjectGit diff --check
    $newFiles = (Invoke-ProjectGit ls-files --others --exclude-standard -z -- . ':(exclude)results/**') -split [char]0
    foreach ($relative in $newFiles) {
        if (-not $relative) { continue }
        $issues = & $gitExe -C $gitRoot -c core.autocrlf=false -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --no-index --check -- /dev/null $relative
        $checkExit = $LASTEXITCODE
        if ($checkExit -gt 1 -or $issues) { throw "Whitespace check failed for ${relative}: $issues" }
    }
}
$metadata = Get-Content -LiteralPath (Join-Path $candidateRoot 'build_summary.json') -Raw | ConvertFrom-Json
$validation = Get-Content -LiteralPath (Join-Path $repoRoot 'results/fullrange_20261003_ranking/context_ram/validation.json') -Raw | ConvertFrom-Json
if ($metadata.bitstream_sha256 -ne $expectedHash -or $validation.bitstream_sha256 -ne $expectedHash -or -not $validation.all_passed) { throw 'Candidate identity or simulation evidence mismatch.' }
$buildPaths = @('src/top.v','src/uart_rx.v','src/uart_tx.v','src/packet_controller.v','src/trade_engine.v','constraints/19_tang_nano_20k.cst','gowin/build_uart.tcl','gowin/uart.sdc')
if (@($metadata.source_sha256.PSObject.Properties).Count -ne $buildPaths.Count) { throw 'Unexpected build input list.' }
foreach ($relative in $buildPaths) {
    $expected = $metadata.source_sha256.$relative
    $actual = (Get-FileHash -LiteralPath (Join-Path $candidateRoot "source/$relative") -Algorithm SHA256).Hash.ToLowerInvariant()
    if (-not $expected -or $actual -ne $expected) { throw "Archived build input mismatch: $relative" }
}
if ((Get-FileHash -LiteralPath (Join-Path $candidateRoot 'candidate.fs') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) { throw 'Archived bitstream mismatch.' }
$resourceReport = [IO.File]::ReadAllText((Join-Path $candidateRoot 'reports/gwsynthesis/trade_core_syn.rpt.html'))
$resourceText = [regex]::Replace([regex]::Replace($resourceReport,'<[^>]+>',' '),'\s+',' ')
if ($resourceText -notmatch 'Logic 312\(272 LUT, 40 ALU\)' -or $resourceText -notmatch 'Register 179 /') { throw 'Unexpected synthesis resource summary.' }
$copyPaths = @(
    '.gitignore','.gitattributes','README.md','PROJECT_BRIEF.md',
    'docs/grading_report.md','docs/lut_optimization_study.md','docs/human_review.md','docs/repository_recovery.md',
    'docs/blockram_candidate.md','docs/logic_optimization.md','docs/official/SCORING_AND_RANKING_CLARIFICATION.md',
    'scripts/21_quick_uart_test.py','scripts/22_robust_uart_test.py','scripts/22_robust_uart_test_fullrange.py',
    'scripts/reference_model.py','scripts/generate_vectors.py','scripts/run_regression.py',
    'scripts/capture_board_tests.py','scripts/capture_vector_stress.py','scripts/prepare_latency_sweep.py',
    'scripts/verify_fullrange_candidates.py','scripts/publish_blockram_candidate.ps1',
    'testbench/uart_rx_tb.v','testbench/uart_tx_tb.v','testbench/top_tb.v','testbench/trade_engine_tb.v','testbench/vectors',
    'results/fullrange_20261003_ranking',
    "$study/context_ram","$study/carry_uart_pointer","$study/carry_direct_equality"
)
$reviewPaths = @($copyPaths) + @($buildPaths) + @('testbench/top_sessions_tb.v','testbench/trade_pair_tb.v','bitstream/trade_core.fs','bitstream/build_summary.json','CANDIDATE.md')
foreach ($relative in $copyPaths) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $relative))) { throw "Missing publication input: $relative" }
}
# PrepareOnly creates an ordinary file snapshot; no Git command is run in that mode.
if ($PrepareOnly) {
    if ($ResumeWorktree) { throw 'PrepareOnly cannot resume a Git worktree.' }
    $publicationRoot = Join-Path $repoRoot ('.build/blockram_ready_' + [guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($publicationRoot) | Out-Null
} else {
    if ((Invoke-ProjectGit ls-remote --heads origin "refs/heads/$branch")) { throw "Branch already exists on origin: $branch. Inspect before updating." }
    if ((Invoke-ProjectGit branch --list $branch) -and -not $ResumeWorktree) { throw "Local branch already exists: $branch. Use ResumeWorktree only for a stopped, uncommitted preparation." }
    Invoke-ProjectGit fetch origin
    $remoteBaseCommit = Invoke-ProjectGit rev-parse origin/main
    if ($ResumeWorktree) {
        $publicationRoot = (Resolve-Path -LiteralPath $ResumeWorktree).ProviderPath
        $commonDirectory = Invoke-ProjectGit rev-parse --path-format=absolute --git-common-dir
        $gitRoot = $publicationRoot
        $top = Invoke-ProjectGit rev-parse --show-toplevel
        if ([IO.Path]::GetFullPath($top).TrimEnd([char[]]'\/') -ne $publicationRoot.TrimEnd([char[]]'\/')) { throw 'ResumeWorktree must be the checkout root.' }
        if ((Invoke-ProjectGit rev-parse --path-format=absolute --git-common-dir) -ne $commonDirectory) { throw 'Resume checkout belongs to another repository.' }
        if ((Invoke-ProjectGit branch --show-current) -ne $branch) { throw 'Resume checkout is on another branch.' }
        if ((Invoke-ProjectGit rev-parse HEAD) -ne $remoteBaseCommit) { throw 'Resume stopped: origin/main changed or a commit was already made.' }
        if ((Invoke-ProjectGit diff --cached --name-only)) { throw 'Resume checkout already has staged changes. Inspect first.' }
    } else {
        $publicationRoot = Join-Path $env:LOCALAPPDATA ('GatorFPGA/blockram_publication_' + [guid]::NewGuid().ToString('N'))
        [IO.Directory]::CreateDirectory((Split-Path -Parent $publicationRoot)) | Out-Null
        Invoke-ProjectGit worktree add -b $branch $publicationRoot $remoteBaseCommit
        $gitRoot = $publicationRoot
    }
}
foreach ($relative in $copyPaths) { Copy-ReviewedPath $relative $publicationRoot }
foreach ($relative in $buildPaths) {
    $target = Join-Path $publicationRoot $relative
    [IO.Directory]::CreateDirectory((Split-Path -Parent $target)) | Out-Null
    Copy-Item -LiteralPath (Join-Path $candidateRoot "source/$relative") -Destination $target -Force
}
foreach ($bench in @('top_sessions_tb.v','trade_pair_tb.v')) {
    Copy-Item -LiteralPath (Join-Path $candidateRoot "verification_source/testbench/$bench") -Destination (Join-Path $publicationRoot "testbench/$bench") -Force
}
[IO.Directory]::CreateDirectory((Join-Path $publicationRoot 'bitstream')) | Out-Null
Copy-Item -LiteralPath (Join-Path $candidateRoot 'candidate.fs') -Destination (Join-Path $publicationRoot 'bitstream/trade_core.fs') -Force
$metadata.status = 'fullrange_simulations_passed_awaiting_physical_validation'
$metadata.simulation = $validation.checks
$metadata | Add-Member -NotePropertyName fullrange_validation -NotePropertyValue 'results/fullrange_20261003_ranking/context_ram/validation.json' -Force
$metadata | Add-Member -NotePropertyName resource_summary -NotePropertyValue $validation.resources -Force
[IO.File]::WriteAllText((Join-Path $publicationRoot 'bitstream/build_summary.json'), (($metadata | ConvertTo-Json -Depth 30) + "`n"), [Text.UTF8Encoding]::new($false))
Copy-Item -LiteralPath (Join-Path $repoRoot 'docs/blockram_candidate.md') -Destination (Join-Path $publicationRoot 'CANDIDATE.md') -Force
$notice = "Experimental branch ${branch}: active source and bitstream are the block-RAM candidate, 312 synthesis Logic / 179 registers / one B-SRAM. Physical validation is pending. CANDIDATE.md identifies this build. Historical release measurements below describe the archived 365-LUT baseline."
foreach ($document in @('README.md','PROJECT_BRIEF.md')) {
    $path = Join-Path $publicationRoot $document
    $text = [IO.File]::ReadAllText($path)
    [IO.File]::WriteAllText($path, "$notice`n`n$text", [Text.UTF8Encoding]::new($false))
}
Assert-BuildIdentity $publicationRoot
if ($PrepareOnly) {
    Write-Output "Prepared exact block-RAM candidate: $publicationRoot"
    return
}
Invoke-ProjectGit status --short
Assert-PublicationWhitespace
Invoke-ProjectGit diff --stat
Write-Host "Review: git -C `"$publicationRoot`" diff"
Write-Host "Resume a precommit stop: powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$repoRoot/scripts/publish_blockram_candidate.ps1`" -ResumeWorktree `"$publicationRoot`""
$review = Read-Host 'Type publish to commit and push codex/logic-312-blockram'
if ($review -cne 'publish') { throw "Stopped before commit/push. Prepared checkout: $publicationRoot" }
Invoke-ProjectGit add -- @reviewPaths
Invoke-ProjectGit diff --cached --check
Invoke-ProjectGit commit -m 'Prepare block-RAM candidate for total-logic qualification testing'
Invoke-ProjectGit push -u origin $branch
Write-Host "Published $branch. Publication checkout: $publicationRoot"
