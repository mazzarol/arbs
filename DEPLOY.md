# Deploy ARBS at arbs.inchargesolutions.au

## 1. DNS — add this record wherever inchargesolutions.au DNS is managed

```
Type:  A
Name:  arbs
Value: <your Lightsail public IP>
TTL:   300
```

## 2. Caddy — add this block to /etc/caddy/Caddyfile on Lightsail

```caddy
arbs.inchargesolutions.au {
        tls peter.mazzarol@gmail.com
        encode zstd gzip

        @http protocol http
        redir @http https://{host}{uri} 308

        header {
                Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
                X-Content-Type-Options "nosniff"
                X-Frame-Options "SAMEORIGIN"
                Referrer-Policy "strict-origin-when-cross-origin"
        }

        # Proxy to your desktop via Tailscale
        handle {
                reverse_proxy 100.66.58.2:8000 {
                        transport http {
                                dial_timeout 10s
                                response_header_timeout 120s
                        }
                }
        }
}
```

## 3. Reload Caddy on Lightsail

```bash
sudo systemctl reload caddy
```

## 4. Start the app on your desktop

```bash
cd ~/recruiter-bypass && .venv/bin/python -m app.main
```

The app already binds to 0.0.0.0:8000 so Tailscale can reach it.
No firewall changes needed — Tailscale is point-to-point.

## 5. Verify

```bash
curl -I https://arbs.inchargesolutions.au
```

Should return 200. Site will be live at https://arbs.inchargesolutions.au
