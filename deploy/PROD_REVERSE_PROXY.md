# Production Setup (Reverse Proxy)

This project can run in production with:
- FastAPI (`uvicorn`) as internal app server
- `nginx` as reverse proxy and TLS terminator

## 1. Prerequisites

- Docker + Docker Compose plugin
- A domain name pointed to your server (for real TLS certificates)
- Prepared backend secrets in `backend/.env`

## 2. TLS certificates

Place certificates in `deploy/certs`:
- `deploy/certs/fullchain.pem`
- `deploy/certs/privkey.pem`

For initial testing, you can use self-signed certificates.
For production, use a trusted CA (for example Let's Encrypt).

## 3. Start production stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Services:
- `glukoze-api` (internal, `api:8000`)
- `glukoze-nginx` (public, `80/443`)

## 4. Routing model

- `https://<your-domain>/api/*` -> proxied to FastAPI
- `https://<your-domain>/healthz` -> backend health check
- HTTP (`:80`) -> redirected to HTTPS

## 5. Verify

```bash
curl -k https://<your-domain>/healthz
curl -k https://<your-domain>/api/auth/me
```

## 6. Electron client with external API

To run Electron against reverse proxy API instead of local backend, set:

```bash
API_BASE_URL=https://<your-domain> npm start
```

In this mode:
- local Python backend is not started by Electron main process
- frontend API calls use `API_BASE_URL`

## 7. Security checklist

- Use trusted TLS certificates (not self-signed) in production
- Limit exposed ports to `80/443`
- Keep `backend/.env` secrets strong and unique
- Restrict firewall access to database/storage paths
