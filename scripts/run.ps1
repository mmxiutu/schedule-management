Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .\.venv)) {
    python -m venv .venv
    .\.venv\Scripts\pip install -e .
}
& .\.venv\Scripts\schedule-assistant.exe
