# Windows: install (first time) and run backend + frontend in two windows.
Set-Location $PSScriptRoot
if (!(Test-Path backend\.venv)) { python -m venv backend\.venv; backend\.venv\Scripts\pip install -r backend\requirements.txt }
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
if (!(Test-Path frontend\node_modules)) { Push-Location frontend; npm install; Pop-Location }
if (Select-String -Path backend\.env -Pattern paste_your_finnhub_key_here -Quiet) { Write-Host "!! Put your Finnhub key in backend\.env first (https://finnhub.io/register)"; exit 1 }
Start-Process powershell -ArgumentList "-NoExit","-Command","cd backend; .venv\Scripts\uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd frontend; npm run dev"
