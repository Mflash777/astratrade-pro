# Create the GitHub repo and host the frontend on GitHub Pages

## 1. Initialize the repository locally

```bash
cd astratrade-pro
git init -b main
git add .
git commit -m "AstraTrade Pro: initial import"
```

## 2. Create the GitHub repository and push

**With the GitHub CLI:**

```bash
gh auth login
gh repo create astratrade-pro --public --source=. --remote=origin --push
```

**Without the CLI:** create an empty repo at <https://github.com/new> (no README), then:

```bash
git remote add origin https://github.com/<your-username>/astratrade-pro.git
git push -u origin main
```

## 3. Generate the lockfile (once)

The CI workflow uses `npm ci`, which requires `frontend/package-lock.json`:

```bash
cd frontend && npm install && cd ..
git add frontend/package-lock.json && git commit -m "Add lockfile" && git push
```

## 4. Enable GitHub Pages

1. Repo → **Settings** → **Pages**.
2. Under **Build and deployment → Source** choose **GitHub Actions**.
3. (Optional) **Settings → Secrets and variables → Actions → Variables** → add `NEXT_PUBLIC_API_URL` = your deployed backend URL (e.g. `https://api.yourdomain.com`). Leave it unset to publish the terminal in demo mode.

## 5. Deploy

The workflow `.github/workflows/deploy-frontend.yml` runs on every push to `main` that touches `frontend/` (or manually via **Actions → Deploy frontend to GitHub Pages → Run workflow**). It:

1. installs dependencies,
2. builds the static export with `NEXT_PUBLIC_BASE_PATH=/<repo-name>` so asset links resolve under `https://<user>.github.io/<repo-name>/`,
3. uploads `frontend/out` and deploys it with `actions/deploy-pages`.

Your terminal is live at **`https://<your-username>.github.io/astratrade-pro/`** within a minute or two.

### User/organization site instead of a project site

If the repo is named `<your-username>.github.io`, set `NEXT_PUBLIC_BASE_PATH: ""` in the workflow so the app is served from the domain root.

### Custom domain

Add a `CNAME` file containing your domain to `frontend/public/` and configure DNS as GitHub documents; with a custom domain also set `NEXT_PUBLIC_BASE_PATH: ""`.

## 6. Alternative: deploy from your machine with gh-pages

```bash
cd frontend
NEXT_PUBLIC_BASE_PATH=/astratrade-pro npm run deploy:gh-pages
```

This builds and pushes `out/` to a `gh-pages` branch; then set Pages → Source to **Deploy from a branch → gh-pages / (root)**.

## 7. Backend CI

`.github/workflows/backend-ci.yml` runs ruff, mypy, pytest (Python 3.11 & 3.12) and the frontend lint/typecheck/build on every push and pull request. Add branch protection on `main` requiring the "Backend CI" checks to pass.

## 8. Connect the Pages frontend to a backend

GitHub Pages is static, so the API must run elsewhere (see `docs/DEPLOYMENT.md`). Set `CORS_ORIGINS` on the backend to include `https://<your-username>.github.io`, and set the `NEXT_PUBLIC_API_URL` variable in step 4. Until then the published site runs in demo mode with mock data.
