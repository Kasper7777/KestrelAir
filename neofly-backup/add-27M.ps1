# Adds $27,000,000 to the NeoFly pilot "Kazber" (players.id = 2).
# Run only after NeoFly has fully exited (including the tray icon).
# Usage:  powershell -ExecutionPolicy Bypass -File .\add-27M.ps1
$ErrorActionPreference = 'Stop'
$amount = 27000000
$playerId = 2
$neo = "$env:LOCALAPPDATA\Programs\Neofly"
$db  = "$neo\std.bin"
$bk  = $PSScriptRoot

if (Get-Process Neofly -ErrorAction SilentlyContinue) {
    Write-Host "NeoFly is still running. Exit it from the tray icon first, then rerun." -ForegroundColor Red
    exit 1
}

# Back up the save right before editing
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item $db "$bk\std-$ts-pre-edit.bin"
Write-Host "Backup: $bk\std-$ts-pre-edit.bin"

[void][Reflection.Assembly]::LoadFrom("$neo\System.Data.SQLite.dll")
$c = New-Object System.Data.SQLite.SQLiteConnection("Data Source=$db")
$c.Open()
$tx = $c.BeginTransaction()
$cmd = $c.CreateCommand(); $cmd.Transaction = $tx

$cmd.CommandText = "select cash from players where id=$playerId"
$before = [int64]$cmd.ExecuteScalar()
$after  = $before + $amount

$cmd.CommandText = "update players set cash=$after where id=$playerId"
[void]$cmd.ExecuteNonQuery()

# Add a ledger line so the Finances tab balance matches
$date = [int64](Get-Date -Format 'yyyyMMddHHmmss')
$cmd.CommandText = "insert into finances(date,description,incomes,expenses,type,source,balance,ownerId) values($date,'Capital injection',$amount,0,1,0,$after,$playerId)"
[void]$cmd.ExecuteNonQuery()

$tx.Commit()
$cmd = $c.CreateCommand(); $cmd.CommandText = "select cash from players where id=$playerId"
$check = $cmd.ExecuteScalar()
$c.Close()

Write-Host ("Cash: {0:N0} -> {1:N0}" -f $before, $check) -ForegroundColor Green
