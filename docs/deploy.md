# Deploying Scam Shield UAE

One service runs both the website and the API, so there is a single thing to deploy.

## Render (free tier)

1. Push the repo to GitHub.
2. In Render, choose **New > Blueprint** and select the repo. Render reads `render.yaml`.
3. Click **Apply**. The first build takes a few minutes.
4. Open the `onrender.com` address Render gives you. Check `/health` returns `{"status":"ok"}`.
5. Add the address to the top of `README.md` as the live demo link.

The free tier sleeps after about 15 minutes without traffic, so the first visit can take around 30 seconds. Say so in the README, or open the site just before you share it.

## Run locally

```bash
pip install -e ".[dev]"
uvicorn scamshield.api:app --reload
# open http://127.0.0.1:8000
```

## Notes

- The rate limiter keys on the client IP. `render.yaml` starts uvicorn with `--proxy-headers`, so the IP comes from the proxy header instead of the proxy's own address.
- The limiter is in memory and per process. It is fine for a demo, and it resets when the service restarts.
- The site sends a strict Content-Security-Policy (scripts and styles from the same origin only). Do not add inline scripts, inline styles or third-party scripts without changing it on purpose.
