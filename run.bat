@echo off
setlocal
set PYTHONPATH=src
if "%1"=="test" (
    python -m unittest discover -s tests -v
) else (
    python -m depgraph %*
)
