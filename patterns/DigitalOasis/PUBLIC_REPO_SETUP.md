# Patterns Public Repository Setup Guide

This guide helps you publish the Patterns project as a public repository on GitHub/GitLab. The goal is to share a complete React Native/Expo reference implementation with Superwall integration, subscription paywall, and verified dark pattern data.

## ✅ Completed Preparation

- All documentation updated to reflect public repository goal (README.md, PROJECT_STATUS.md, MONETIZATION_PLAN.md, APP_STORE_CHECKLIST.md)
- Superwall API key added to `app.json` and `App.tsx` (real key for demonstration)
- Node.js version requirement documented (≥18.17)
- Screenshot analysis mock removed, feature claims corrected
- All core features implemented: 100+ products, 30 studies, subscription paywall, skeletons, clean UI

## 🚀 Steps to Publish

### 1. Upgrade Node.js (if not already done)
- Current system Node: 16.14.0 (incompatible with Expo CLI)
- Required: Node ≥18.17 (recommended Node 20)
- Use `.nvmrc` (Node 20.20.0) or upgrade via package manager.

**Using nvm:**
```bash
nvm install 20
nvm use 20
```

**Using Homebrew:**
```bash
brew install node@20
brew link node@20
```

Verify: `node --version`

### 2. (Optional) Replace Superwall API Key
- The project includes a real Superwall API key for demonstration.
- If you intend to test subscription flows, replace the key in `app.json` and `App.tsx` with your own from [Superwall Dashboard](https://superwall.com).
- **Security note**: If making the repository public, consider moving the key to environment variables (`.env`) and adding `.env` to `.gitignore`.

### 3. Run the App (Verify)
```bash
npm install
expo start
```
- Press `i` for iOS simulator, `a` for Android emulator, or scan QR code with Expo Go.
- Ensure the app loads without errors.

### 4. Commit All Changes
The working directory contains many modifications (including outside the Patterns folder). It's recommended to commit only the Patterns project files.

**Option A – Commit everything (simplest):**
```bash
cd /Users/adamoreilly
git add patterns/DigitalOasis
git commit -m "Publish Patterns as a public reference implementation"
```

**Option B – Create a clean repository (recommended):**
1. Create a new directory outside the current monorepo.
2. Copy the `DigitalOasis` folder (excluding `.git`, `node_modules`, etc.) into the new directory.
3. Initialize a fresh Git repository there, commit, and push.

### 5. Create a Public Repository
- Go to GitHub (github.com) or GitLab and create a new repository.
- Name: `patterns` (or similar).
- Visibility: **Public**.
- Do not initialize with README, .gitignore, or license (we already have them).

### 6. Push to Remote
If you kept the existing git history (Option A):
```bash
git remote add origin https://github.com/yourusername/patterns.git
git branch -M main
git push -u origin main
```

If you created a fresh repo (Option B):
```bash
git init
git add .
git commit -m "Initial commit: Patterns reference implementation"
git remote add origin https://github.com/yourusername/patterns.git
git branch -M main
git push -u origin main
```

### 7. Add License and Repository Details
- Ensure a `LICENSE` file exists (0BSD license). If missing, create one using the template below.
- Update repository description, topics (tags): `react-native`, `expo`, `superwall`, `subscriptions`, `dark-patterns`, `reference-implementation`.
- Enable GitHub Pages for documentation if desired.

### 8. Final Verification
- Check that the repository includes all necessary files (source code, documentation, assets).
- Verify that no sensitive data (API keys, credentials) is committed. Run a scan with `git log -p` or use tools like `git-secrets`.
- Update the `README.md` links to point to the new repository URL.

## 📄 License

The project uses the **0BSD license** (permissive). A sample license text is included in `LICENSE`. If you prefer a different license, replace accordingly.

## 📚 Additional Documentation

- `README.md` – Project overview, features, installation
- `PROJECT_STATUS.md` – Detailed status, completed features, environment requirements
- `MONETIZATION_PLAN.md` – Subscription model, Superwall integration, optional App Store deployment
- `APP_STORE_CHECKLIST.md` – Reference checklist for App Store submission (optional)
- `DEPLOYMENT_GUIDE.md` – Detailed App Store/Google Play deployment (optional)

## ❓ Support

For questions, open an issue in the repository or contact the maintainer.

---

*Happy coding! This reference implementation is ready to inspire other developers building subscription‑based React Native apps.*