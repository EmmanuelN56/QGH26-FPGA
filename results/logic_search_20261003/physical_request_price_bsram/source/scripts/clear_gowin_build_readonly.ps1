$ErrorActionPreference = 'Stop'
$optRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$optTarget = [System.IO.Path]::GetFullPath((Join-Path $optRoot '.build/gowin_trade'))
if (-not $optTarget.StartsWith($optRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    throw 'Build target escaped workspace'
}
if (-not (Test-Path -LiteralPath $optTarget)) { exit 0 }
$optEntries = @(Get-Item -LiteralPath $optTarget) + @(Get-ChildItem -LiteralPath $optTarget -Recurse -Force)
foreach ($optEntry in $optEntries) {
    if (-not ($optEntry.FullName -eq $optTarget -or $optEntry.FullName.StartsWith($optTarget + '\'))) {
        throw 'Entry escaped build directory'
    }
    if ($optEntry.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw 'Reparse point in build directory'
    }
}
foreach ($optEntry in $optEntries) {
    if (-not $optEntry.PSIsContainer) { $optEntry.IsReadOnly = $false }
}
