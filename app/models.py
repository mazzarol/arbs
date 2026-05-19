import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from app.database import Base


def age_days(dt: datetime.datetime) -> int:
    """Days since a datetime. Returns 0 if less than 1 day."""
    delta = datetime.datetime.utcnow() - dt
    return max(0, delta.days)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), default="seek")       # seek, linkedin, indeed
    source_id = Column(String(100), unique=True)       # external ID
    title = Column(String(300))
    location = Column(String(200))
    snippet = Column(Text)
    description = Column(Text)
    url = Column(String(500))
    listed_company = Column(String(300))               # what the ad says
    found_employer = Column(String(300), nullable=True) # what our AI found
    match_confidence = Column(Float, nullable=True)
    match_method = Column(String(100), nullable=True)   # "jd_fingerprint", "manual", etc.
    is_direct = Column(Boolean, default=False)          # known direct employer
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)
    first_seen = Column(DateTime, default=datetime.datetime.utcnow)


class Employer(Base):
    __tablename__ = "employers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), unique=True)
    domain = Column(String(300), nullable=True)
    careers_url = Column(String(500), nullable=True)
    is_direct_hire = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.datetime.utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100))
    status = Column(String(50))       # running, completed, failed
    jobs_processed = Column(Integer, default=0)
    employers_found = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    log = Column(Text, nullable=True)


class ConnectionLog(Base):
    __tablename__ = "connection_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(45))
    path = Column(String(300))
    user_agent = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    isp = Column(String(200), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
