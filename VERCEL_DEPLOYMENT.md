# Vercel Deployment Guide

## Prerequisites
- GitHub account with repo access to `https://github.com/BISWA192111/hackathon_20`
- Vercel account (free tier works fine)

## Step 1: Create/Access Vercel Account
1. Go to https://vercel.com
2. Click **Sign Up** (or login if you already have an account)
3. Choose **GitHub** as sign-up method (easier to connect repos)
4. Authorize Vercel to access your GitHub account

## Step 2: Import Your GitHub Repository
1. Once logged in, click **Add New** → **Project**
2. Select **Import Git Repository**
3. Paste this URL: `https://github.com/BISWA192111/hackathon_20`
4. Click **Continue**
5. Vercel will detect your repository

## Step 3: Configure the Project
1. **Project Name**: Give it a name (e.g., `hackathon-staging`)
2. **Framework**: Select **Docker** (Vercel detected your Dockerfile)
3. **Environment Variables**: Add any required variables
   - `SUPABASE_RUNS_TABLE` = `onboarding_runs` (already in vercel.json)
   - Add any other environment secrets from your `.env` file

## Step 4: Set the Deployment Branch
1. In the Vercel project settings, ensure:
   - **Git Branch to Deploy**: Set to `Testing/Staging` (the branch you want)
   - You can set this under **Settings** → **Git** after project creation

## Step 5: Deploy
1. Click **Deploy**
2. Vercel will:
   - Clone your repo from the Testing/Staging branch
   - Build your Docker image
   - Deploy to their servers
   - Provide you with a live URL

## Step 6: Monitor Deployment
- View deployment logs in the Vercel dashboard
- Check health endpoint: `https://your-vercel-url/api/v1/health`
- View logs: **Settings** → **Logs**

## Automatic Deployments
Once set up, every push to `Testing/Staging` branch will automatically redeploy!

## Troubleshooting

### Port Issues
- Vercel automatically exposes port 8000 (your FastAPI default)
- Your Dockerfile already handles this correctly

### Environment Variables
- Add secrets in Vercel dashboard: **Settings** → **Environment Variables**
- Include database credentials, API keys, etc.

### Docker Build Fails
- Check that all files in `.dockerignore` are correctly excluded
- Ensure Python version compatibility (3.11 is ideal)

## Rollback
If needed, you can redeploy a previous version from the Vercel dashboard.
