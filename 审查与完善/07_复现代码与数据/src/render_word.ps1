param(
  [string]$Docx = 'C:\Users\30511\AppData\Local\Temp\microgrid-paper.docx',
  [string]$Pdf = 'C:\Users\30511\AppData\Local\Temp\microgrid-paper.pdf'
)
$word = $null
$document = $null
try {
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0
  $document = $word.Documents.Open($Docx, $false, $true)
  $document.ExportAsFixedFormat($Pdf, 17)
} finally {
  if ($null -ne $document) { $document.Close($false) }
  if ($null -ne $word) { $word.Quit() }
}
