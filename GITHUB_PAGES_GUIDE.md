# Deploy PharmAi Vision on GitHub Pages (free)
Designed & developed by NIKHIL CHARY SRIRAMOJU

1. Get a free Groq key: https://console.groq.com → API Keys → Create. (Never commit it.)
2. Create a repo: github.com/new → name `pharmai-vision` → Public → Create.
3. Upload: unzip this package, then in the repo click "Add file → Upload files", drag ALL contents (including the hidden `.github` folder), commit to `main`.
   Or via terminal:
   ```bash
   cd pharmai-vision
   git init && git add . && git commit -m "PharmAi Vision master release"
   git branch -M main
   git remote add origin https://github.com/Nikhil-creat/pharmai-vision.git
   git push -u origin main
   ```
4. Repo → Settings → Pages → Source: **GitHub Actions** (the included workflow publishes `/docs`).
   Alternative: Source "Deploy from a branch" → `main` → `/docs`.
5. Open Actions tab, wait for the green check. Site: https://nikhil-creat.github.io/pharmai-vision/
6. Open the site → ⚙ Settings → paste your Groq key → Save. Done.

Notes
- The key lives only in the visitor's browser (localStorage). Each visitor uses their own free key. Do NOT hard-code a key into `index.html` — it would be public and get abused/revoked.
- Want a shared key without exposing it? Put a tiny Cloudflare Worker in front of Groq that holds the key and rate-limits, then change `GROQ` in `docs/index.html` to the worker URL.
- Full stack (Docker): `cp .env.example .env`, set `GROQ_API_KEY`, `docker compose up --build`. Kubernetes: `infra/k8s/pharmai.yaml`.
- Custom domain: Settings → Pages → Custom domain.
