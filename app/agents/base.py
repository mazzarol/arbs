"""Base agent class and orchestrator."""
import httpx
import json
import time
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session


class BaseAgent:
    """Base class for employer-identification agents."""

    name: str = "base"

    def __init__(self, api_key: str = None, api_url: str = None, model: str = None):
        self.api_key = api_key
        self.api_url = api_url or "https://api.deepseek.com/v1/chat/completions"
        self.model = model or "deepseek-chat"

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> Optional[str]:
        """Call the LLM API and return the response text."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        try:
            r = httpx.post(self.api_url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"LLM error {r.status_code}: {r.text[:200]}")
                return None
        except Exception as e:
            print(f"LLM call failed: {e}")
            return None

    def run(self, db: Session, job_ids: list[int]) -> dict:
        """Run the agent on a batch of jobs. Returns stats dict."""
        raise NotImplementedError


class AgentOrchestrator:
    """Runs agents sequentially or in parallel, aggregates results."""

    def __init__(self, db: Session):
        self.db = db
        self.results = []

    def run_agent(self, agent: BaseAgent, job_ids: list[int], agent_run_id: int = None):
        """Run one agent and record the run."""
        from app.models import AgentRun

        started = datetime.utcnow()
        stats = agent.run(self.db, job_ids)
        finished = datetime.utcnow()

        if agent_run_id:
            run = self.db.query(AgentRun).filter(AgentRun.id == agent_run_id).first()
            if run:
                run.status = "completed" if stats.get("error") is None else "failed"
                run.jobs_processed = stats.get("processed", 0)
                run.employers_found = stats.get("found", 0)
                run.finished_at = finished
                run.log = json.dumps(stats)
                self.db.commit()

        self.results.append({"agent": agent.name, "stats": stats})
        return stats

    def run_all(self, agents: list[BaseAgent], job_ids: list[int]):
        """Run multiple agents sequentially on the same job batch."""
        all_stats = {}
        for agent in agents:
            stats = self.run_agent(agent, job_ids)
            all_stats[agent.name] = stats
        return all_stats
