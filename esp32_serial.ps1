param(
  [Parameter(Mandatory=$true)][string]$Port,
  [Parameter(Mandatory=$true)][string]$Command,
  [int]$Seconds = 25,
  [Parameter(Mandatory=$true)][string]$OutFile,
  [string]$Arg = ""
)

$baud = 115200

$sp = New-Object System.IO.Ports.SerialPort $Port, $baud, "None", 8, "One"
$sp.ReadTimeout = 500
$sp.WriteTimeout = 500

try {
  $sp.Open()
  Start-Sleep -Milliseconds 800

  # 1) Menü-Befehl senden (z.B. 5)
  $sp.WriteLine($Command)

  # 2) Optional zweite Zeile senden (z.B. IP)
  if ($Arg -and $Arg.Trim().Length -gt 0) {
    Start-Sleep -Milliseconds 350
    $sp.WriteLine($Arg)
  }

  $end = (Get-Date).AddSeconds($Seconds)
  $lines = New-Object System.Collections.Generic.List[string]

  while((Get-Date) -lt $end) {
    try {
      $line = $sp.ReadLine()
      if ($line) { $lines.Add($line) }
    } catch {
      # Timeout -> weiter
    }
  }

  $lines | Out-File -FilePath $OutFile -Encoding UTF8
}
finally {
  if ($sp.IsOpen) { $sp.Close() }
}
