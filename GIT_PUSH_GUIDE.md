# 📤 Git Push Guide - Safe Repository Publishing

This guide ensures sensitive data (API keys, .env files) are NOT pushed to your remote repository.

## ✅ Pre-Push Checklist

### 1. Verify .env File is NOT Committed

```bash
# Check if .env is in git (shows all committed files)
git ls-files | grep "\.env"
```

**If .env appears in the output**, you need to remove it from git history:

```bash
# Remove from git (but keep in your local machine)
git rm --cached .env

# Add to gitignore if not already there
echo ".env" >> .gitignore
git add .gitignore

# Commit the change
git commit -m "Remove .env from version control"

# OPTIONAL: Remove from entire git history (only if .env was committed with secrets)
# WARNING: This rewrites history - only do this before pushing!
git filter-branch --tree-filter 'rm -f .env' -- --all
```

### 2. Verify All Sensitive Files are Ignored

```bash
# Check what would be committed
git status

# Dry-run to see what will be committed
git diff --cached --name-only

# Verify no .env files appear
git check-ignore .env
git check-ignore .env.example  # Should NOT be ignored (it has placeholders)
```

**Expected output**:
```
.env       # Should print this (file is ignored)
(no output for .env.example)  # Should NOT be ignored
```

### 3. Clean Up Uncommitted Sensitive Files

```bash
# Don't commit:
.env                    # Never commit
*.log                   # Log files
db_30_1_excel/         # Large training data
__pycache__/           # Python cache

# DO commit:
.env.example           # Template for setup
requirements.txt       # Dependencies
README.md              # Documentation
ALGORITHMS_AND_TRAINING.md  # Technical docs
```

## 🔧 Setup Steps

### Step 1: Initialize/Update Remote (if not done)

```bash
# Add remote (replace with your GitHub/GitLab URL)
git remote add origin https://github.com/YOUR_USERNAME/hackathon-onboarding.git

# Or if remote exists, verify it
git remote -v
```

### Step 2: Commit Your Changes

```bash
# Check status
git status

# Add files (will respect .gitignore)
git add .

# Verify nothing sensitive is staged
git diff --cached | grep -i "api\|key\|secret\|token"
# Should return NOTHING

# Commit
git commit -m "Update README, algorithms docs, and UI improvements"
```

### Step 3: Push to Remote

```bash
# Push to main branch
git push origin main

# Or if your default branch is 'master'
git push origin master
```

### Step 4: Verify on Remote

1. Go to your GitHub/GitLab repository
2. Verify `.env` file is NOT present
3. Verify `.env.example` IS present
4. Check that sensitive files are not included:
   - No `db_30_1_excel/` folder
   - No `*.log` files
   - No `__pycache__/` directories

## ⚠️ If Secrets Were Already Pushed

**Immediately rotate your keys**:

1. **Supabase**: https://supabase.com/ → Project Settings → Regenerate Keys
2. **Azure OpenAI**: Azure Portal → Regenerate Access Keys
3. **Update .env.example** with new template (without actual values)

Then use `git filter-branch` to remove from history (see Step 1 above).

## 📋 Files That WILL Be Pushed

✅ **Core Application**:
- `app.py`
- `requirements.txt`
- `Dockerfile`
- `README.md`
- `ALGORITHMS_AND_TRAINING.md`
- `presentation_outline.md`

✅ **Source Code**:
- `backend/` (FastAPI code)
- `frontend/` (HTML/CSS/JS)
- `onboarding_engine/` (Algorithm implementation)
- `supabase/schema.sql` (Database schema template)

✅ **Configuration Templates**:
- `.env.example` (Setup guide, no actual keys)
- `.gitignore` (Ignore patterns)

## 📋 Files That WON'T Be Pushed

❌ **Sensitive**:
- `.env` (actual API keys and credentials)
- `.env.local` (local overrides)

❌ **Large Data**:
- `db_30_1_excel/` (training data, 100+ MB)
- `data/*.pkl` (serialized models)
- `*.xlsx` (Excel files)

❌ **Auto-Generated**:
- `__pycache__/`
- `.pytest_cache/`
- `*.pyc`
- `dist/` `build/`

❌ **Logs & Temp**:
- `*.log`
- `tmp/` `temp/`

❌ **IDE Files**:
- `.vscode/settings.json`
- `.idea/`
- `*.swp`

## 🔐 Post-Push Verification

```bash
# Verify repository integrity
git log --oneline -5  # Last 5 commits

# Check that no sensitive files exist
git ls-files | grep -E "\.env|\.log|__pycache__|\.pkl"
# Should return NOTHING
```

## 🚀 Quick Reference

```bash
# One-command push (after initial setup)
git add . && \
git commit -m "Your commit message" && \
git push origin main
```

## 💡 Tips for Future Development

1. **Create a `.env` locally** from `.env.example`:
   ```bash
   cp .env.example .env
   # Edit .env with your actual keys
   ```

2. **Never commit .env** - let `.gitignore` handle it

3. **Share .env with team safely**:
   - Use password manager (LastPass, 1Password)
   - Or encrypted file in separate private channel
   - NOT via git or email

4. **Rotate keys periodically**:
   - Every 90 days minimum
   - Immediately if accidentally exposed
   - Update `.env.example` template as needed

## 📞 Need Help?

```bash
# See what would be committed
git status

# See actual file content differences
git diff --cached

# Undo last commit (if made a mistake)
git reset --soft HEAD~1

# Remove accidentally staged file
git reset HEAD sensitive-file.txt
```

---

**Remember**: 
- ✅ `.env.example` should be committed (templates with placeholders)
- ❌ `.env` should NEVER be committed (contains real secrets)
- ✅ All source code should be committed
- ❌ Large data files should NOT be committed (add to .gitignore)

