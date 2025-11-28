<#
Script to download Inter font files into `web/static/fonts/`.
Run this from the repo root in PowerShell. This uses curl (available in modern Windows).
It fetches WOFF2/WOFF variants for local bundling.

Note: If you prefer other weights or formats, adjust URLs accordingly.
#>

$out = "web/static/fonts"
If (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

$files = @(
    @{ url = 'https://github.com/rsms/inter/releases/download/v3.19/Inter-3.19.zip'; name = 'Inter.zip' }
)

Write-Host "This script will download Inter font archive to $out."
Write-Host "Please extract desired .woff/.woff2 files into $out and then reload the app."

foreach ($f in $files) {
    $dest = Join-Path $out $f.name
    Write-Host "Downloading $($f.url) -> $dest"
    try {
        curl $f.url -o $dest
        Write-Host "Downloaded $dest"
    } catch {
        Write-Host "Failed to download $($f.url): $_"
    }
}

Write-Host "Done. Extract the archive and place Inter-Regular.woff2 and Inter-Bold.woff2 into $out."
