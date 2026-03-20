@echo off
REM Safe Git Push Script for Windows
REM This script prepares and pushes the repository while excluding sensitive data

echo.
echo 🔐 Ensuring .env is not in git history...
git rm --cached .env 2>nul
echo.

echo ✅ Adding .gitignore updates...
git add .gitignore
echo.

echo 📋 Staging all safe files...
git add .
echo.

echo 🔍 Verifying no sensitive files are staged...
git diff --cached > temp_diff.txt
findstr /M "SUPABASE_ AZURE_OPENAI_ API_KEY api_key" temp_diff.txt >nul 2>&1
if not errorlevel 1 (
  echo.
  echo ❌ ERROR: Sensitive data detected in staged files!
  echo Run: git reset [filename] to unstage
  del temp_diff.txt
  exit /b 1
)
del temp_diff.txt

echo.
echo ✅ All checks passed!
echo.
echo 📤 Ready to commit and push!
echo.
echo Next steps:
echo 1. git commit -m "Prepare for public release: update docs, algorithms, UI"
echo 2. git push origin main
echo.
echo OR run this one-liner:
echo git commit -m "Prepare for public release" && git push origin main
echo.
pause
