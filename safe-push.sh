#!/bin/bash
# Safe Git Push Script
# This script prepares and pushes the repository while excluding sensitive data

echo "🔐 Ensuring .env is not in git history..."
git rm --cached .env 2>/dev/null || true

echo "✅ Adding .gitignore updates..."
git add .gitignore

echo "📋 Staging all safe files..."
git add .

echo "🔍 Verifying no sensitive files are staged..."
if git diff --cached | grep -i "SUPABASE_\|AZURE_OPENAI_\|API_KEY\|api_key"; then
  echo "❌ ERROR: Sensitive data detected in staged files!"
  echo "Run: git reset <filename> to unstage"
  exit 1
fi

echo "✅ All checks passed!"
echo ""
echo "📤 Ready to commit and push!"
echo ""
echo "Next steps:"
echo "1. git commit -m 'Prepare for public release: update docs, algorithms, UI'"
echo "2. git push origin main"
echo ""
echo "OR run this one-liner:"
echo "git commit -m 'Prepare for public release' && git push origin main"
