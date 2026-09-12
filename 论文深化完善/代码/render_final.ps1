param([string]$Root)
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open((Join-Path $Root '微网购电策略论文_深化检验版.docx'), $false, $false)
    $null = $document.Fields.Update()
    $document.Repaginate()
    $document.Save()
    $document.ExportAsFixedFormat((Join-Path $Root '排版检查.pdf'), 17)
} finally {
    if ($null -ne $document) { $document.Close($false) }
    if ($null -ne $word) { $word.Quit() }
}
