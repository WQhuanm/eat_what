$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$supported = @('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')

$files = Get-ChildItem -LiteralPath $scriptDir -File |
  Where-Object { $supported -contains $_.Extension.ToLower() } |
  Sort-Object CreationTimeUtc, Name

if (-not $files -or $files.Count -eq 0) {
  "No image files found in $scriptDir"
  exit 0
}

# Phase 1: rename all files to temporary names to avoid collisions
$tempPairs = @()
for ($i = 0; $i -lt $files.Count; $i++) {
  $file = $files[$i]
  $tmpName = "__tmp_rename_{0}{1}" -f $i, $file.Extension.ToLower()
  $tmpPath = Join-Path $scriptDir $tmpName
  Rename-Item -LiteralPath $file.FullName -NewName $tmpName
  $tempPairs += [PSCustomObject]@{
    TmpPath = $tmpPath
    Ext = $file.Extension.ToLower()
  }
}

# Phase 2: rename temp files to image1, image2, ... by creation time order
for ($i = 0; $i -lt $tempPairs.Count; $i++) {
  $targetName = "image{0}{1}" -f ($i + 1), $tempPairs[$i].Ext
  Rename-Item -LiteralPath $tempPairs[$i].TmpPath -NewName $targetName
}

"Renamed $($tempPairs.Count) image file(s) in creation-time order."

# 项目根目录执行 powershell -ExecutionPolicy Bypass -File "paper\LaTex\test\test_images\rename_by_creation_time.ps1"
