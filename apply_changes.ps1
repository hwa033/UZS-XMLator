<#
Apply changes stored in `changes.patch` by writing file blocks into the workspace.

This helper is an alternative to a unified git diff. It parses `changes.patch` created
by the assistant and writes each `=== FILE: path ===` block to disk, creating directories
as needed. Run this from the repository root using PowerShell.

Usage:
  & .\apply_changes.ps1

It will prompt before overwriting existing files.
#>

$patch = Get-Content -Raw -Path .\changes.patch
$blocks = $patch -split "^=== FILE: " -ne ""

foreach ($b in $blocks) {
    if (-not $b.Trim()) { continue }
    $lines = $b -split "`n"
    $first = $lines[0].Trim()
    if ($first -notlike "*=== FILE: *") { $path = $first } else { $path = $first }
    # path may include trailing text, take until end of line
    $path = $first -replace " ===.*$", ''
    $bodyStart = [Array]::IndexOf($lines, '','')
    # Find the first line that looks like code block start (``` or content)
    $contentLines = @()
    $found = $false
    for ($i = 1; $i -lt $lines.Length; $i++) {
        $ln = $lines[$i]
        if ($ln -like '```*') { $found = -not $found; continue }
        if ($found) { $contentLines += $ln }
        elseif ($ln -ne '') { $contentLines += $ln }
    }

    $outPath = Join-Path -Path (Get-Location) -ChildPath $path
    $dir = Split-Path $outPath -Parent
    if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

    if (Test-Path $outPath) {
        Write-Host "Overwrite $path? (Y/N)" -NoNewline
        $k = Read-Host
        if ($k -ne 'Y' -and $k -ne 'y') { Write-Host "Skipping $path"; continue }
    }

    $contentLines | Set-Content -Path $outPath -Encoding utf8
    Write-Host "Wrote: $path"
}

Write-Host 'Done applying changes.'
