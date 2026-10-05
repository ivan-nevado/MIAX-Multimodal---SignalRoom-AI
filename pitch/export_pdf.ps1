# Exporta pitch/SignalRoom_PitchDeck.pptx a PDF con PowerPoint (fuentes incrustadas).
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pptx = Join-Path $here "SignalRoom_PitchDeck.pptx"
$pdf = Join-Path $here "SignalRoom_PitchDeck.pdf"
$app = New-Object -ComObject PowerPoint.Application
try {
    $pres = $app.Presentations.Open($pptx, $true, $false, $false)
    $pres.SaveAs($pdf, 32)  # ppSaveAsPDF
    $pres.Close()
    Write-Output "OK -> $pdf"
} finally {
    $app.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
