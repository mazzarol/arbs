"""Phrase Search Agent — finds hidden employers by searching unique JD phrases on multiple search engines."""

import re
import urllib.parse
from curl_cffi import requests
from bs4 import BeautifulSoup
from collections import Counter
from app.agents.base import BaseAgent
from app.models import Job, Employer
from sqlalchemy.orm import Session

JOB_BOARD_DOMAINS = [
    "seek.com.au", "seek.com", "indeed.com", "linkedin.com/jobs",
    "glassdoor.com", "jora.com", "careerone.com.au", "adzuna.com.au",
    "simplyhired.com", "ziprecruiter.com", "monster.com",
    "roberthalf.com", "hays.com", "randstad.com", "michaelpage.com",
    "adecco.com", "chandlermacleod.com", "hudson.com",
]

EXCLUDE_PHRASES = [
    "we are seeking", "we are looking", "the successful candidate",
    "please apply", "click apply", "apply now", "send your resume",
    "for more information", "we encourage", "we welcome",
    "we offer", "we provide", "competitive salary",
    "equal opportunity", "diversity", "inclusion",
]

# Company-specific clue words — sentences containing these are good search candidates
CLUE_WORDS = [
    "aws", "ec2", "ecs", "lambda", "route53", "docker", "kubernetes",
    "terraform", "react", "node", "typescript", "golang", "python",
    "microservice", "serverless", "fintech", "healthtech", "edtech",
    "saas", "platform", "product", "pipeline", "cicd",
    "engineering team", "software development",
    "agile", "scrum", "azure", "gcp", "api",
    "backed by", "funded", "series a", "series b", "startup",
    "we build", "we develop", "our platform", "our product",
    "our engineering", "our technology", "our tech",
    "award-winning", "industry-leading", "market-leading",
    "fastest-growing", "vc-backed", "bootstrapped",
    "brisbane-based", "sunshine coast", "gold coast",
]


class PhraseSearchAgent(BaseAgent):
    """Identifies employers by searching unique JD phrases on search engines."""

    name = "phrase_search"

    def _extract_search_phrases(self, text: str, max_phrases: int = 8) -> list[str]:
        """Extract unique, searchable phrases from a job description."""
        candidates = []
        sentences = re.split(r'[.\n•·-]+', text)
        for s in sentences:
            s = s.strip()
            if len(s) < 80 or len(s) > 350:
                continue
            if any(excl in s.lower() for excl in EXCLUDE_PHRASES):
                continue
            # Score by number of clue words
            score = sum(1 for cw in CLUE_WORDS if cw in s.lower())
            if score > 0:
                candidates.append((score, s))

        candidates.sort(key=lambda x: x[0], reverse=True)

        seen = set()
        unique = []
        for _, phrase in candidates:
            key = phrase[:100].lower()
            if key not in seen:
                seen.add(key)
                unique.append(phrase)
        return unique[:max_phrases]

    def _search_engines(self, phrase: str) -> list[dict]:
        """Search a phrase on multiple engines. Returns list of {title, url, snippet}."""
        results = []
        query = f'"{phrase[:200]}"'

        # DuckDuckGo
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            r = requests.get(url, impersonate="safari17_0", timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", class_="result__a"):
                href = a.get("href", "")
                if "uddg=" in href:
                    href = urllib.parse.parse_qs(href.split("uddg=")[1].split("&")[0]).get("uddg", [href])[0]
                if not href.startswith("http"):
                    continue
                if any(bd in href.lower() for bd in JOB_BOARD_DOMAINS):
                    continue
                snippet_el = a.find_next("a", class_="result__snippet")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                results.append({
                    "title": a.get_text(strip=True),
                    "url": href,
                    "snippet": snippet,
                    "source": "ddg",
                })
        except Exception:
            pass

        # Google
        try:
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            r = requests.get(url, impersonate="chrome124", timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            for g in soup.find_all("div", class_="g"):
                a = g.find("a", href=True)
                if a:
                    href = a.get("href", "")
                    if not href.startswith("http"):
                        continue
                    if any(bd in href.lower() for bd in JOB_BOARD_DOMAINS):
                        continue
                    title_el = g.find("h3")
                    title = title_el.get_text(strip=True) if title_el else ""
                    snippet_el = g.find("span", class_=lambda c: c and "aCOpRe" in str(c) if c else False)
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    results.append({
                        "title": title,
                        "url": href,
                        "snippet": snippet,
                        "source": "google",
                    })
        except Exception:
            pass

        return results

    def _extract_company_names(self, url: str, title: str) -> list[str]:
        """Extract possible company names from URL and page title."""
        names = []

        # From title: "Senior Developer at Acme Corp — Careers"
        title_match = re.search(r'(?:at|with|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s+[–—-]|\s*$|\s*\|)', title)
        if title_match:
            names.append(title_match.group(1).strip())

        # From domain
        domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
        parts = domain.split('.')
        if len(parts) >= 2:
            name = parts[-2] if parts[-1] in ('au', 'nz', 'uk', 'com', 'org', 'net', 'io', 'co') else parts[-1]
            name = name.replace('-', ' ').title()
            if name.lower() not in ('www', 'careers', 'jobs', 'apply', 'home'):
                names.append(name)

        # From URL path: /careers/acme-corp/ or /company/acme-corp
        path_match = re.search(r'/(?:company|careers|about)/([a-z0-9-]+)', url.lower())
        if path_match:
            names.append(path_match.group(1).replace('-', ' ').title())

        return list(set(names))

    def run(self, db: Session, job_ids: list[int]) -> dict:
        """Process jobs and attempt to identify employers via phrase search."""
        jobs = db.query(Job).filter(Job.id.in_(job_ids)).all()
        if not jobs:
            return {"processed": 0, "found": 0, "error": "No jobs found"}

        employers = db.query(Employer).all()
        employer_names = {e.name.lower(): e.name for e in employers}
        employer_domains = {}
        for e in employers:
            if e.domain:
                employer_domains[e.domain.lower()] = e.name

        processed = 0
        found = 0
        errors = 0

        for job in jobs:
            if job.found_employer:
                continue

            text = job.description or job.snippet or ""
            if len(text) < 100:
                continue

            phrases = self._extract_search_phrases(text)
            if not phrases:
                continue

            processed += 1
            company_votes = Counter()

            for phrase in phrases[:4]:  # Search up to 4 phrases
                results = self._search_engines(phrase)
                for r in results:
                    candidates = self._extract_company_names(r["url"], r["title"])
                    for c in candidates:
                        company_votes[c] += 1

            if not company_votes:
                continue

            best_match = None
            best_confidence = 0.0

            for company_name, votes in company_votes.most_common(5):
                company_lower = company_name.lower()

                # Check exact employer DB match
                if company_lower in employer_names:
                    confidence = min(0.95, 0.5 + votes * 0.12)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = employer_names[company_lower]
                    continue

                # Check domain match
                for domain, ename in employer_domains.items():
                    if domain in company_lower or company_lower in domain:
                        confidence = 0.85
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = ename
                        break

                # Partial name match (fuzzy)
                for ename_lower, ename in employer_names.items():
                    if company_lower in ename_lower or ename_lower in company_lower:
                        confidence = min(0.80, 0.4 + votes * 0.10)
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = ename
                        break

            if best_match and best_confidence > 0.4:
                job.found_employer = best_match
                job.match_confidence = best_confidence
                job.match_method = "phrase_search"
                found += 1

        db.commit()
        return {
            "processed": processed,
            "found": found,
            "errors": errors,
            "employers_available": len(employers),
        }
