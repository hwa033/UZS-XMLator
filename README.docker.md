# Docker quick start

Build the image and run the app locally:

```powershell
# from project root (Windows PowerShell)
docker compose build --pull
docker compose up -d

# Open http://localhost:8080
```

Notes:
- The container exposes port `8080` and serves the Flask app using `gunicorn`.
- Volumes mount `uzs_filedrop` and `web/static/downloads` so generated XML and ZIP archives are accessible locally.
