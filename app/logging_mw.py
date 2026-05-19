"""Connection logging middleware with IP geolocation."""
import datetime
import httpx
from fastapi import Request
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import ConnectionLog


GEO_CACHE = {}  # Simple in-memory cache for IP lookups


def lookup_ip(ip: str) -> dict:
    """Look up IP geolocation. Returns dict with city, region, country, isp."""
    if ip in GEO_CACHE:
        return GEO_CACHE[ip]

    # Skip private/local IPs
    if ip.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.",
                      "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
                      "172.24.", "172.25.", "172.26.", "172.27.", "172.28.",
                      "172.29.", "172.30.", "172.31.", "100.", "0.")):
        return {"city": "Local", "region": "", "country": "", "isp": ""}

    try:
        r = httpx.get(f"http://ip-api.com/json/{ip}?fields=city,regionName,country,isp",
                      timeout=5)
        if r.status_code == 200:
            data = r.json()
            result = {
                "city": data.get("city", ""),
                "region": data.get("regionName", ""),
                "country": data.get("country", ""),
                "isp": data.get("isp", ""),
            }
            GEO_CACHE[ip] = result
            return result
    except Exception:
        pass

    return {"city": "", "region": "", "country": "", "isp": ""}


def log_request(request: Request):
    """Log an HTTP request to the database. Deduplicates same IP within 1 hour."""
    try:
        db = SessionLocal()
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        ua = request.headers.get("user-agent", "")[:300]

        # Skip if this IP was already logged in the last hour
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        recent = db.query(ConnectionLog).filter(
            ConnectionLog.ip == ip,
            ConnectionLog.timestamp >= cutoff,
        ).first()
        if recent:
            db.close()
            return

        # Look up IP if it's new
        existing = db.query(ConnectionLog).filter(ConnectionLog.ip == ip).first()
        if existing and existing.city:
            city, region, country, isp = existing.city, existing.region, existing.country, existing.isp
        else:
            geo = lookup_ip(ip)
            city, region, country, isp = geo["city"], geo["region"], geo["country"], geo["isp"]

        log = ConnectionLog(
            ip=ip, path=path, user_agent=ua,
            city=city, region=region, country=country, isp=isp,
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(log)
        db.commit()
        db.close()
    except Exception:
        pass
