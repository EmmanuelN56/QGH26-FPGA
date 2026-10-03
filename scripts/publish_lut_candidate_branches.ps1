# Run manually from the repository root. Publishes sibling candidate branches.
[CmdletBinding()]
param(
    [string]$ResumeWorktree
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$gitRoot = $repoRoot
Set-Location -LiteralPath $repoRoot
$gitExe = 'C:/Program Files/Git/cmd/git.exe'
if (-not (Test-Path -LiteralPath $gitExe)) { $gitExe = (Get-Command git -ErrorAction Stop).Source }
function Invoke-ProjectGit {
    & $gitExe -C $gitRoot -c core.autocrlf=false -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol -c "safe.directory=$($gitRoot.Replace('\','/'))" @args
    if ($LASTEXITCODE -ne 0) { throw "Git failed: $args" }
}
# Check new source/document files before staging; archived results keep tool formatting.
function Assert-PublicationWhitespace {
    Invoke-ProjectGit diff --check
    $newFiles = (Invoke-ProjectGit ls-files --others --exclude-standard -z -- . ':(exclude)results/**') -split [char]0
    foreach ($relative in $newFiles) {
        if (-not $relative) { continue }
        $issues = & $gitExe -C $gitRoot -c core.autocrlf=false -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol -c "safe.directory=$($gitRoot.Replace('\','/'))" diff --no-index --check -- /dev/null $relative
        $checkExit = $LASTEXITCODE
        # --no-index returns 1 for a new file even when its whitespace is valid.
        if ($checkExit -gt 1 -or $issues) { throw "Whitespace check failed for ${relative}: $issues" }
    }
}
$study = 'results/area_20261003T192105403559Z'
$candidates = @(
    @{ Branch='codex/lut-230'; Name='carry_direct_equality'; LUT=230; ALU=104; Logic=342; Hash='f33a5f114d87616951c13435718ed73c124a23b2a02452ec93f26593e1278bf8' },
    @{ Branch='codex/lut-234'; Name='carry_uart_pointer'; LUT=234; ALU=72; Logic=314; Hash='ea5279614794fc79c7f3632b429584b29a3cb7c0fdb80811f3e4b95ef2cb8d4a' }
)
$baseBranch = 'codex/lut-comparison-base'
$currentBranch = Invoke-ProjectGit branch --show-current
if ($currentBranch -ne 'main') { throw 'Start on the existing local main branch.' }
foreach ($branch in @($baseBranch) + @($candidates | ForEach-Object { $_.Branch })) {
    $existing = Invoke-ProjectGit branch --list $branch
    if ($existing -and -not ($ResumeWorktree -and $branch -eq $baseBranch)) {
        throw "Branch already exists: $branch. Inspect it before rerunning."
    }
}
# Verify saved identities before changing any branch or file.
foreach ($candidate in $candidates) {
    $folder = "$study/$($candidate.Name)"
    $metadata = Get-Content -LiteralPath "$folder/build_summary.json" -Raw | ConvertFrom-Json
    if ($metadata.synthesis.LUT -ne $candidate.LUT -or $metadata.bitstream_sha256 -ne $candidate.Hash) { throw 'Candidate metadata mismatch.' }
    $digest = (Get-FileHash -LiteralPath "$folder/candidate.fs" -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($digest -ne $candidate.Hash) { throw 'Candidate bitstream mismatch.' }
    foreach ($entry in $metadata.source_sha256.PSObject.Properties) {
        $digest = (Get-FileHash -LiteralPath "$folder/source/$($entry.Name)" -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($digest -ne $entry.Value) { throw "Candidate source mismatch: $($entry.Name)" }
    }
    if (-not (Test-Path -LiteralPath "$study/prototypes/$($candidate.Name)/testbench/trade_pair_tb.v")) { throw 'Paired-engine testbench missing.' }
}
Invoke-ProjectGit fetch origin
# Each candidate will inherit the fetched remote main, even when local main is behind.
$remoteBaseCommit = Invoke-ProjectGit rev-parse origin/main
$remoteBranches = Invoke-ProjectGit ls-remote --heads origin refs/heads/codex/lut-230 refs/heads/codex/lut-234
if ($remoteBranches) { throw 'A target candidate branch already exists on GitHub. Inspect it before rerunning.' }
$reviewPaths = @(
    '.gitignore', '.gitattributes', 'README.md', 'PROJECT_BRIEF.md',
    'docs/board_bringup.md', 'docs/latency_optimization.md',
    'docs/grading_report.md', 'docs/lut_optimization_study.md', 'docs/human_review.md', 'docs/repository_recovery.md',
    'gowin/README.md', 'gowin/build_uart.tcl', 'gowin/uart.sdc',
    'constraints/19_tang_nano_20k.cst',
    'src/top.v', 'src/uart_rx.v', 'src/uart_tx.v', 'src/packet_controller.v', 'src/trade_engine.v',
    'scripts/reference_model.py', 'scripts/generate_vectors.py', 'scripts/run_regression.py',
    'scripts/capture_board_tests.py', 'scripts/capture_vector_stress.py',
    'scripts/prepare_latency_sweep.py', 'scripts/publish_lut_candidate_branches.ps1', 'scripts/verify_recovered_candidates.py',
    'testbench/top_tb.v', 'testbench/top_sessions_tb.v', 'testbench/trade_engine_tb.v',
    'testbench/uart_rx_tb.v', 'testbench/uart_tx_tb.v',
    'testbench/vectors', 'bitstream/trade_core.fs', 'bitstream/build_summary.json', 'results'
)
# Copy reviewed files into a separate native checkout. Preserve other remote files.
foreach ($relative in $reviewPaths) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $relative))) { throw "Missing publication input: $relative" }
}
if ($ResumeWorktree) {
    $publicationRoot = (Resolve-Path -LiteralPath $ResumeWorktree).ProviderPath
    $originalCommonDirectory = Invoke-ProjectGit rev-parse --path-format=absolute --git-common-dir
    $gitRoot = $publicationRoot
    $publicationTop = Invoke-ProjectGit rev-parse --show-toplevel
    if ([IO.Path]::GetFullPath($publicationTop).TrimEnd([char[]]'\/') -ne $publicationRoot.TrimEnd([char[]]'\/')) {
        throw 'ResumeWorktree must identify the root of the prepared checkout.'
    }
    $publicationCommonDirectory = Invoke-ProjectGit rev-parse --path-format=absolute --git-common-dir
    if ($publicationCommonDirectory -ne $originalCommonDirectory) { throw 'Resume checkout belongs to another repository.' }
    if ((Invoke-ProjectGit branch --show-current) -ne $baseBranch) { throw 'Resume requires the uncommitted comparison-base checkout.' }
    if ((Invoke-ProjectGit rev-parse HEAD) -ne $remoteBaseCommit) { throw 'Resume stopped: the base was committed or origin/main changed. Inspect before continuing.' }
    if (Invoke-ProjectGit diff --cached --name-only) { throw 'Resume stopped: the checkout already has staged changes. Inspect before continuing.' }
} else {
    $publicationRoot = Join-Path $env:LOCALAPPDATA ('GatorFPGA/candidate_publication_' + [guid]::NewGuid().ToString('N'))
    if (Test-Path -LiteralPath $publicationRoot) { throw 'Publication directory already exists.' }
    [IO.Directory]::CreateDirectory((Split-Path -Parent $publicationRoot)) | Out-Null
    Invoke-ProjectGit worktree add -b $baseBranch $publicationRoot $remoteBaseCommit
    $gitRoot = $publicationRoot
}
Set-Location -LiteralPath $publicationRoot
Write-Host "Preparing isolated publication checkout: $publicationRoot"
foreach ($relative in $reviewPaths) {
    $sourcePath = Join-Path $repoRoot $relative
    if (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
        $files = @(Get-Item -LiteralPath $sourcePath)
    } else {
        $files = @(Get-ChildItem -LiteralPath $sourcePath -File -Recurse -Force)
    }
    foreach ($file in $files) {
        $fileRelative = $file.FullName.Substring($repoRoot.Length).TrimStart([char[]]'\/')
        $destination = Join-Path $publicationRoot $fileRelative
        [IO.Directory]::CreateDirectory((Split-Path -Parent $destination)) | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    }
}
Invoke-ProjectGit status --short
Assert-PublicationWhitespace
Invoke-ProjectGit diff --stat
Write-Host "Review the full diff with: git -C `"$publicationRoot`" diff"
$review = Read-Host 'Type publish to commit the prepared snapshot and publish both candidate branches'
if ($review -cne 'publish') { throw "Stopped before any commit or push. Prepared checkout: $publicationRoot" }
Invoke-ProjectGit add -- @reviewPaths
Invoke-ProjectGit diff --cached --check
Invoke-ProjectGit commit -m 'Preserve validated trading core and LUT comparison evidence'
$baseCommit = Invoke-ProjectGit rev-parse HEAD
foreach ($candidate in $candidates) {
    # Both start from the same base commit, not from one another.
    Invoke-ProjectGit switch -c $candidate.Branch $baseCommit
    $folder = "$study/$($candidate.Name)"
    $metadata = Get-Content -LiteralPath "$folder/build_summary.json" -Raw | ConvertFrom-Json
    foreach ($entry in $metadata.source_sha256.PSObject.Properties) {
        Copy-Item -LiteralPath "$folder/source/$($entry.Name)" -Destination $entry.Name -Force
    }
    Copy-Item -LiteralPath "$folder/candidate.fs" -Destination 'bitstream/trade_core.fs' -Force
    Copy-Item -LiteralPath "$folder/build_summary.json" -Destination 'bitstream/build_summary.json' -Force
    Copy-Item -LiteralPath "$study/prototypes/$($candidate.Name)/testbench/trade_pair_tb.v" -Destination 'testbench/trade_pair_tb.v' -Force
    foreach ($entry in $metadata.source_sha256.PSObject.Properties) {
        $digest = (Get-FileHash -LiteralPath $entry.Name -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($digest -ne $entry.Value) { throw "Active source mismatch: $($entry.Name)" }
    }
    $digest = (Get-FileHash -LiteralPath 'bitstream/trade_core.fs' -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($digest -ne $candidate.Hash) { throw 'Active bitstream mismatch.' }
    $notice = "Experimental branch $($candidate.Branch): active src/ and bitstream/trade_core.fs are the $($candidate.LUT)-LUT candidate. Physical validation is pending. CANDIDATE.md identifies the build; historical release measurements below describe the archived 365-LUT baseline."
    foreach ($document in @('README.md', 'PROJECT_BRIEF.md')) {
        $path = Join-Path $publicationRoot $document
        $oldText = [IO.File]::ReadAllText($path)
        [IO.File]::WriteAllText($path, "$notice`n`n$oldText", [Text.UTF8Encoding]::new($false))
    }
    $handoff = @"
# $($candidate.LUT)-LUT physical-test candidate

Branch: $($candidate.Branch)
Source: src/ (matches the archived candidate source exactly)
Bitstream: bitstream/trade_core.fs
Build identity: bitstream/build_summary.json
SHA-256: $($candidate.Hash)
Resources: $($candidate.LUT) LUTs, 222 registers, $($candidate.ALU) ALUs, $($candidate.Logic) reported logic units, 0 B-SRAM, 8 SSRAM.
Evidence: $folder/
Fresh expanded simulation evidence: $folder/recovery_simulation/validation.json
Combined comparison evidence: results/recovery_candidate_validation.json

The exact source and bitstream were recovered from native Windows build copies.
Fresh recovery simulations are in the candidate recovery_simulation/ directory.
Synthesis/routing passed. Physical validation is pending.
The paired engine is tested by testbench/trade_pair_tb.v. The legacy standalone
engine remains in the source for compatibility; testing that legacy module alone
does not validate the shared candidate datapath. Include full-system tests.

Add the expanded physical suite to this branch, program the identified bitstream
in volatile SRAM mode, and save logs/CSVs with the branch commit and this SHA-256.
Use identical board/host settings when comparing the two branches. After testing,
merge only the selected candidate into main. Historical release documents describe
the archived baseline and must be updated when a new physical release is selected.
"@
    [IO.File]::WriteAllText((Join-Path $publicationRoot 'CANDIDATE.md'), "$handoff`n", [Text.UTF8Encoding]::new($false))
    Assert-PublicationWhitespace
    Invoke-ProjectGit diff --stat
    Invoke-ProjectGit add -- src/top.v src/uart_rx.v src/uart_tx.v src/packet_controller.v src/trade_engine.v constraints/19_tang_nano_20k.cst gowin/build_uart.tcl gowin/uart.sdc testbench/trade_pair_tb.v bitstream/trade_core.fs bitstream/build_summary.json README.md PROJECT_BRIEF.md CANDIDATE.md
    Invoke-ProjectGit diff --cached --check
    Invoke-ProjectGit commit -m "Prepare $($candidate.LUT)-LUT candidate for physical comparison"
    Invoke-ProjectGit push -u origin $candidate.Branch
}
Invoke-ProjectGit switch $baseBranch
Write-Host 'Published codex/lut-230 and codex/lut-234. Local main and origin/main were not changed.'
Write-Host "Publication checkout: $publicationRoot"
Write-Host "Original checkout, branch, index and working files were preserved: $repoRoot"
