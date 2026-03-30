# GitHub Setup Guide

Step-by-step instructions to push this project to GitHub.

## Prerequisites

- Git installed (`git --version`)
- GitHub account
- Anthropic API key (get from https://console.anthropic.com/)

## Steps

### 1. Initialize Git Repository

```bash
cd /Users/nizamijussupov/Desktop/AI/Sandbox/ai-sandbox

# Initialize git (if not already done)
git init

# Add all files
git add .

# Check what will be committed (make sure .env is NOT included!)
git status

# Create initial commit
git commit -m "Initial commit: Production RAG system

- Phase 1: Document indexing with ChromaDB
- Phase 2: Stateless Q&A
- Phase 3: Conversational RAG with memory
- Phase 4: REST API with FastAPI
- Docker deployment ready
- Complete documentation"
```

### 2. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `fastapi-rag-system` (or your choice)
3. Description: `Production-ready RAG system for FastAPI documentation - Weekend project demonstrating AI systems engineering`
4. **Keep it Public** (for portfolio)
5. **Don't** initialize with README (we already have one)
6. Click "Create repository"

### 3. Push to GitHub

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/fastapi-rag-system.git

# Verify remote
git remote -v

# Push to GitHub
git push -u origin main

# If your default branch is 'master', use:
# git branch -M main
# git push -u origin main
```

### 4. Verify Upload

Check that these files are **NOT** in your GitHub repo (should be in .gitignore):
- ❌ `.env` (contains API key!)
- ❌ `data/fastapi_repo/` (large cloned repo)
- ❌ `data/chroma_db/` (vector DB - users will regenerate)

Check that these files **ARE** in your repo:
- ✅ `README.md`
- ✅ `.env.example`
- ✅ `src/` directory
- ✅ `Dockerfile`
- ✅ `docker-compose.yml`
- ✅ `requirements.txt`
- ✅ `LICENSE`

### 5. Add GitHub Topics (Optional but Recommended)

On your GitHub repo page, click "⚙️ Settings" → scroll to "Topics" and add:
- `rag`
- `retrieval-augmented-generation`
- `fastapi`
- `langchain`
- `chromadb`
- `anthropic`
- `claude`
- `ai-engineering`
- `machine-learning`
- `nlp`

### 6. Enable GitHub Actions

Your repo already has `.github/workflows/test.yml`. GitHub Actions will run automatically on push.

### 7. Update README with Your GitHub Username

Edit `README.md` and replace any placeholder links with your actual GitHub URL.

## Security Checklist

Before pushing, verify:

- [ ] `.env` file is in `.gitignore`
- [ ] No API keys in code
- [ ] `.env.example` has placeholder values only
- [ ] Large data files are excluded

## Post-Push: Update Your Profile

1. **Pin this repo** to your GitHub profile (shows in "Pinned repositories")
2. **Add to resume/LinkedIn**: "Built production RAG system with 10 req/sec throughput"
3. **Write a blog post** about your learning journey

## Troubleshooting

### Issue: ".env file was pushed"

```bash
# Remove from Git history (BEFORE others clone!)
git rm --cached .env
git commit -m "Remove .env from tracking"
git push --force

# Rotate your API key immediately!
# Go to https://console.anthropic.com/ and regenerate
```

### Issue: "Repository size too large"

```bash
# data/ folder should be in .gitignore
git rm -r --cached data/fastapi_repo
git rm -r --cached data/chroma_db
git commit -m "Remove large data files"
git push
```

### Issue: "Permission denied (publickey)"

```bash
# Use HTTPS instead of SSH
git remote set-url origin https://github.com/YOUR_USERNAME/fastapi-rag-system.git
```

## Next Steps

After pushing to GitHub:

1. **Add a demo video**: Record a quick demo and add to README
2. **Create issues**: Add "enhancement" issues for future features
3. **Set up GitHub Projects**: Track your roadmap
4. **Enable Discussions**: For community questions
5. **Add CI/CD badge**: Once Actions run, add badge to README

## Share Your Work

- Tweet with hashtags: `#RAG #AI #MachineLearning #FastAPI`
- Post on LinkedIn with project link
- Share in relevant communities (r/MachineLearning, AI Discord servers)
- Add to your portfolio website

---

**You're ready to push!** 🚀

Run the commands in Step 1 and 3, and you'll have your project live on GitHub.
