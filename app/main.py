"""Recruiter Bypass — FastAPI application."""
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from app.database import init_db, get_db, SessionLocal
from app.models import Job, Employer, AgentRun, ConnectionLog, age_days
from app.scraper import scrape_seek, scrape_indeed, scrape_jora
from app.agents.base import BaseAgent, AgentOrchestrator
from app.agents import JDFingerprintAgent
from app.agents.phrase_search import PhraseSearchAgent
from app.logging_mw import log_request
import threading

# Agent config — set your DeepSeek API key
AGENT_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MAX_RECENT = 10
agent_running = False
agent_lock = threading.Lock()


def get_recent_searches(request: Request) -> list[str]:
    """Get recent search terms from cookie."""
    raw = request.cookies.get("recent_searches", "")
    return [s for s in raw.split("|") if s][:MAX_RECENT]


def get_last_search(request: Request) -> tuple[str, str]:
    """Get last-used keywords and location from cookies."""
    kw = request.cookies.get("last_keywords", "software engineer")
    loc = request.cookies.get("last_location", "Sunshine Coast QLD")
    return kw, loc


def update_recent_searches(keywords: str, recent: list[str]) -> str:
    """Add a search term to the front of the recent list, deduplicate, return cookie value."""
    terms = [keywords] + [s for s in recent if s != keywords]
    return "|".join(terms[:MAX_RECENT])

app = FastAPI(title="Recruiter Bypass")

# Templates
templates = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=select_autoescape(["html"]),
)
templates.filters["age_days"] = age_days


@app.on_event("startup")
def startup():
    init_db()


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    # Don't log static/asset requests
    if not request.url.path.startswith(("/static", "/favicon")):
        log_request(request)
    response = await call_next(request)
    return response


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    job_count = db.query(Job).count()
    employer_count = db.query(Employer).count()
    matched = db.query(Job).filter(Job.found_employer.isnot(None)).count()
    hidden = db.query(Job).filter(Job.found_employer.is_(None), Job.is_direct.is_(False)).count()
    recent_jobs = db.query(Job).order_by(Job.scraped_at.desc()).limit(10).all()
    employers = db.query(Employer).order_by(Employer.name).all()
    employer_urls = {e.name: (e.careers_url or f"https://{e.domain}") for e in employers if e.domain or e.careers_url}
    last_kw, last_loc = get_last_search(request)

    return templates.get_template("dashboard.html").render(
        request=request,
        job_count=job_count,
        employer_count=employer_count,
        matched_count=matched,
        recent_jobs=recent_jobs,
        employers=employers,
        recent_searches=get_recent_searches(request),
        hidden_count=hidden,
        last_keywords=last_kw,
        last_location=last_loc,
        employer_urls=employer_urls,
    )


@app.get("/jobs", response_class=HTMLResponse)
def jobs_list(request: Request, db: Session = Depends(get_db), page: int = 1, filter: str = "all",
              sort: str = "scraped_at", order: str = "desc"):
    per_page = 25
    query = db.query(Job)

    if filter == "hidden":
        query = query.filter(Job.found_employer.is_(None), Job.is_direct.is_(False))
    elif filter == "revealed":
        query = query.filter(Job.found_employer.isnot(None))
    elif filter == "direct":
        query = query.filter(Job.is_direct.is_(True))

    # Sort
    sort_col = getattr(Job, sort, Job.scraped_at)
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    total = query.count()
    jobs = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page
    last_kw, last_loc = get_last_search(request)
    employers = db.query(Employer).all()
    employer_urls = {e.name: (e.careers_url or f"https://{e.domain}") for e in employers if e.domain or e.careers_url}

    return templates.get_template("jobs.html").render(
        request=request, jobs=jobs, page=page, pages=pages, total=total,
        recent_searches=get_recent_searches(request), filter=filter,
        last_keywords=last_kw, last_location=last_loc, employer_urls=employer_urls,
        sort=sort, order=order,
    )


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(job_id: int, request: Request, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return HTMLResponse("<h2>Job not found</h2>", status_code=404)
    return templates.get_template("job_detail.html").render(request=request, job=job)


@app.get("/employers", response_class=HTMLResponse)
def employers_list(request: Request, db: Session = Depends(get_db),
                   sort: str = "name", order: str = "asc"):
    sort_col = getattr(Employer, sort, Employer.name)
    if order == "asc":
        employers = db.query(Employer).order_by(sort_col.asc()).all()
    else:
        employers = db.query(Employer).order_by(sort_col.desc()).all()
    return templates.get_template("employers.html").render(
        request=request, employers=employers, sort=sort, order=order)


@app.post("/scrape")
def trigger_scrape(keywords: str = Form(default="software engineer"), location: str = Form(default="Sunshine Coast QLD"), db: Session = Depends(get_db), request: Request = None):
    jobs_data = scrape_seek(keywords=keywords, location=location, pages=1)
    jobs_data += scrape_indeed(keywords=keywords, location=location, pages=1)
    jobs_data += scrape_jora(keywords=keywords, location=location, pages=1)
    new_count = 0
    for jd in jobs_data:
        existing = db.query(Job).filter(Job.source_id == jd["source_id"]).first()
        if not existing:
            try:
                db.add(Job(**jd))
                new_count += 1
            except Exception:
                db.rollback()
    db.commit()
    response = RedirectResponse(f"/jobs?scraped={new_count}", status_code=303)
    cookie_val = update_recent_searches(keywords, get_recent_searches(request))
    response.set_cookie(key="recent_searches", value=cookie_val, max_age=365*24*3600)
    response.set_cookie(key="last_keywords", value=keywords, max_age=365*24*3600)
    response.set_cookie(key="last_location", value=location, max_age=365*24*3600)
    return response


@app.get("/agents", response_class=HTMLResponse)
def agents_view(request: Request, db: Session = Depends(get_db)):
    runs = db.query(AgentRun).order_by(AgentRun.started_at.desc()).limit(20).all()
    return templates.get_template("agents.html").render(
        request=request, runs=runs, agent_running=agent_running)


@app.get("/logs", response_class=HTMLResponse)
def logs_view(request: Request, db: Session = Depends(get_db),
              sort: str = "timestamp", order: str = "desc"):
    sort_col = getattr(ConnectionLog, sort, ConnectionLog.timestamp)
    if order == "asc":
        logs = db.query(ConnectionLog).order_by(sort_col.asc()).limit(100).all()
    else:
        logs = db.query(ConnectionLog).order_by(sort_col.desc()).limit(100).all()
    unique_ips = db.query(ConnectionLog.ip).distinct().count()
    return templates.get_template("logs.html").render(
        request=request, logs=logs, unique_ips=unique_ips, sort=sort, order=order)


@app.post("/agents/run")
def trigger_agents(db: Session = Depends(get_db)):
    """Run agents in a background thread. Returns immediately."""
    global agent_running

    with agent_lock:
        if agent_running:
            return RedirectResponse("/agents?msg=already_running", status_code=303)
        agent_running = True

    unmatched = (
        db.query(Job)
        .filter(Job.found_employer.is_(None), Job.is_direct.is_(False))
        .all()
    )
    if not unmatched:
        with agent_lock:
            agent_running = False
        return RedirectResponse("/agents?msg=no_unmatched", status_code=303)

    job_ids = [j.id for j in unmatched]

    def _run_agents():
        global agent_running
        bg_db = SessionLocal()
        try:
            # Phrase search agent
            run1 = AgentRun(agent_name="phrase_search", status="running")
            bg_db.add(run1)
            bg_db.commit()
            psa = PhraseSearchAgent()
            orch = AgentOrchestrator(bg_db)
            orch.run_agent(psa, job_ids, agent_run_id=run1.id)

            # JD fingerprint agent
            if AGENT_API_KEY:
                run2 = AgentRun(agent_name="jd_fingerprint", status="running")
                bg_db.add(run2)
                bg_db.commit()
                jdf = JDFingerprintAgent(api_key=AGENT_API_KEY)
                orch.run_agent(jdf, job_ids, agent_run_id=run2.id)
        finally:
            bg_db.close()
            with agent_lock:
                agent_running = False

    threading.Thread(target=_run_agents, daemon=True).start()
    return RedirectResponse("/agents?msg=started", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
