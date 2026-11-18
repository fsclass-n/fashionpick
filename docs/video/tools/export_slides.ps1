# PowerPoint 에서 발표 자료를 1920x1080 PNG 로 내보낸다 (읽기 전용으로 열기)
# 실행: powershell -ExecutionPolicy Bypass -File docs/video/tools/export_slides.ps1
$root = Resolve-Path "$PSScriptRoot\..\..\.."
$src = Join-Path $root "docs\fashionpick_발표자료.pptx"
$out = Join-Path $root "docs\video\build\slides"
New-Item -ItemType Directory -Force $out | Out-Null
$ppt = New-Object -ComObject PowerPoint.Application
$pres = $ppt.Presentations.Open($src, $true, $false, $false)
foreach ($i in 1..$pres.Slides.Count) { $pres.Slides($i).Export((Join-Path $out ("slide{0:D2}.png" -f $i)), "PNG", 1920, 1080) }
$pres.Close(); $ppt.Quit()
Write-Output "exported $($pres.Slides.Count) slides -> $out"
