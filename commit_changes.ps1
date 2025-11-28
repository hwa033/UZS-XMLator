<#
Helper script to stage and commit the workspace changes locally.

Usage (PowerShell):
  # from repository root
  & .\commit_changes.ps1

This script will:
- show `git status` (porcelain)
- stage the set of likely-changed files
- create a commit with a descriptive message
#>

Write-Output "Running local commit helper..."

$files = @(
  'web/utils.py',
  'web/app.py',
  'tests/test_utils.py',
  'tests/test_tag_datasets.py',
  'tools/tag_datasets.py',
  '.github/workflows/ci.yml'
)

Write-Output "Repository status (porcelain):"
git status --porcelain

Write-Output "Staging listed files (if present)..."
foreach ($f in $files) {
  if (Test-Path $f) {
    git add $f
    Write-Output "Staged: $f"
  } else {
    Write-Output "(missing) $f"
  }
}

Write-Output "Also staging any remaining changes (optional)..."
git add -A

$msg = 'Prune archived originals; refactor helpers into web.utils; add tests and CI workflow'
try {
  git commit -m $msg
  Write-Output 'Commit created.'
} catch {
  Write-Output 'No commit was created (maybe no changes to commit).'
}

Write-Output 'You can push with: git push origin HEAD'
