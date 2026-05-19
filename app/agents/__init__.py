"""JD Fingerprint Agent — identifies hidden employers by matching job description
phrases against a database of known employers."""

from app.agents.base import BaseAgent
from app.models import Job, Employer
from sqlalchemy.orm import Session
import json

SYSTEM_PROMPT = """You are an expert at identifying hidden employers behind recruiter-posted job ads.
You analyze a job description and match it against a list of known companies.

For each job, return a JSON object with:
{
  "analysis": {
    "key_phrases": ["unique phrase 1", "unique phrase 2"],
    "industry": "guessed industry",
    "tech_stack": ["tech1", "tech2"],
    "company_size_hint": "startup/SME/enterprise based on clues"
  },
  "matches": [
    {
      "employer_name": "Company Name",
      "confidence": 0.85,
      "evidence": "This phrase matched their known profile: ..."
    }
  ]
}

Rules:
- Only match if you have real evidence. Confidence 0 if no match.
- Use the employer descriptions provided to find matches.
- A "leading provider of X in Australia" matched with a company description
  containing similar language is strong evidence.
- Location match alone is weak evidence.
- Tech stack match alone is medium evidence.
- Combined location + tech + industry is strong evidence.
- Return at most 3 matches, sorted by confidence."""


class JDFingerprintAgent(BaseAgent):
    """Matches recruiter JDs against known employer profiles."""

    name = "jd_fingerprint"

    def run(self, db: Session, job_ids: list[int]) -> dict:
        """
        Process unmatched jobs and attempt to identify the employer.
        Returns stats dict with processed, found, errors.
        """
        # Load jobs
        jobs = db.query(Job).filter(Job.id.in_(job_ids)).all()
        if not jobs:
            return {"processed": 0, "found": 0, "error": "No jobs found"}

        # Load employer profiles
        employers = db.query(Employer).all()
        employer_list = []
        for e in employers:
            employer_list.append({
                "name": e.name,
                "domain": e.domain or "",
                "notes": e.notes or "",
                "is_direct": e.is_direct_hire,
            })

        employer_text = json.dumps(employer_list, indent=2)

        processed = 0
        found = 0
        errors = 0

        for job in jobs:
            if job.found_employer:
                continue  # Already matched

            # Build the prompt
            user_prompt = f"""Job to analyze:

Title: {job.title}
Location: {job.location}
Listed by: {job.listed_company or 'Unknown (possibly direct)'}
Description: {job.description or job.snippet or 'No description available'}
URL: {job.url}

Known employers in database:
{employer_text}

Identify the most likely employer behind this job ad. If the job is already
posted by a direct employer (not a recruiter), say so. Return JSON only."""

            result = self._call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.2)
            processed += 1

            if not result:
                errors += 1
                continue

            # Parse the JSON response
            try:
                # Extract JSON from response (may have markdown wrapping)
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0]
                data = json.loads(result.strip())
            except json.JSONDecodeError:
                errors += 1
                continue

            # Apply best match
            matches = data.get("matches", [])
            if matches and matches[0].get("confidence", 0) > 0.3:
                best = matches[0]
                job.found_employer = best["employer_name"]
                job.match_confidence = best["confidence"]
                job.match_method = "jd_fingerprint"
                found += 1

        db.commit()
        return {
            "processed": processed,
            "found": found,
            "errors": errors,
            "employers_available": len(employer_list),
        }
