# GitHub and Vercel deployment

## GitHub

```bash
gh repo create pramaan-ai-sih26261 --public --source=. --remote=origin
git add .
git commit -m "feat: add PRAMAAN-AI validation platform"
git push -u origin main
```

## Vercel

The repository includes `api/index.py`, `vercel.json`, and a root
`requirements.txt` so Vercel can expose the FastAPI app as a Python function.

```bash
npm install --global vercel
vercel login
vercel --prod
```

The hosted MVP uses ephemeral `/tmp` SQLite and upload storage. It is suitable
for a demo deployment; production persistence should use PostgreSQL and object
storage. The seeded demo accounts are synthetic and should be replaced before
any real deployment.
