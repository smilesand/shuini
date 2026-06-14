$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$PythonExe = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $PythonExe)) { $PythonExe = 'python' }
& $PythonExe .\scripts\package.py --variant desktop --platform windows