"""Seek.com.au job scraper using curl-cffi for browser impersonation."""
from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

BASE = "https://au.seek.com"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

RECRUITER_KEYWORDS = [
    # Major IT recruiters (Australia)
    "recruit", "talent", "hays", "randstad", "adecco", "manpower",
    "consulting", "people2people", "robert half", "michael page",
    "chandler macleod", "hudson", "programmed", "talent international",
    "absolute it", "paxus", "greythorn", "candle", "halcyon knights",
    "genesis it", "iterate", "just people", "modis", "remedy", "t+o",
    "profusion", "ambition", "mars", "gough", "six degrees", "davidson",
    # Additional IT recruiters
    "circuIT", "ethos", "finite", "horizon one", "motion", "ncs",
    "peoplebank", "progressive", "spark", "technology people",
    "titan", "verse", "west", "xpt", "zone it", "talent hub",
    "clearcompany", "cynosure", "dedicated it", "digital natives",
    "edison", "emerald", "exclaim", "finity", "fourquarters",
    "genesis", "halcyon", "harrison", "harvey nash", "haystack",
    "hcm", "hi-tech", "ikon", "infopeople", "ingenuity", "insight",
    "interpro", "kinetic", "lauren", "link", "logical", "m&t",
    "m4", "mane", "mansell", "march", "marvin", "maven", "mcr",
    "melbourne it", "metric", "morson", "niteo", "northbridge",
    "novon", "oaklands", "onq", "opus", "orr", "pacific",
    "parity", "path", "paxus", "people bank", "peoplebank",
    "perm", "philip", "pilot", "pinpoint", "pinnacle", "pioneer",
    "pivot", "place", "planit", "point", "precision", "prime",
    "pros", "qest", "ramsay", "real", "redefine", "remedy",
    "renaissance", "resource", "revolution", "rochelle", "s2m",
    "saber", "sahra", "salt", "satellite", "scala", "select",
    "shannon", "sharp", "silicon", "sirius", "sourced", "south",
    "sphere", "spinnaker", "spirit", "stars", "sustain", "sw",
    "swift", "synchronise", "talent x", "tardis", "teksystems",
    "tenth", "the drive", "the network", "tiger", "titan",
    "transformed", "tribe", "trident", "troocoo", "u&u",
    "unify", "upstream", "venture", "vivid", "wave", "whizdom",
    "winthrop", "wise", "wolfe", "worktrybe", "xl", "you",
    "zen", "zenergy", "zone",
]


def is_recruiter(company_name: str) -> bool:
    """Check if the listed company is a known recruitment agency. Uses whole-word matching."""
    if not company_name:
        return False
    company_lower = company_name.lower()
    # Split into words for whole-word matching
    company_words = set(company_lower.replace("&", " ").replace("-", " ").split())
    for kw in RECRUITER_KEYWORDS:
        kw_lower = kw.lower()
        # Multi-word keywords: check if they appear as a phrase
        if " " in kw_lower:
            if kw_lower in company_lower:
                return True
        # Single-word keywords: check whole-word match
        else:
            if kw_lower in company_words:
                return True
    return False


def parse_relative_date(text: str) -> datetime | None:
    """Parse relative date strings like '3d ago', '5h ago', 'Posted 2 days ago'."""
    if not text:
        return None
    # Remove "Posted" prefix, Featured/Expiring noise
    text = re.sub(r'(?i)posted\s*|featured|expiring|\•', '', text).strip()
    match = re.match(r'(\d+)\+?\s*(d|day|h|hour|w|week|m|minute)', text, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        unit = match.group(2)[0].lower()
        if unit == 'h':
            return datetime.utcnow() - timedelta(hours=num)
        elif unit == 'd':
            return datetime.utcnow() - timedelta(days=num)
        elif unit == 'w':
            return datetime.utcnow() - timedelta(weeks=num)
    return None


def scrape_seek(keywords="software engineer", location="Sunshine Coast QLD", pages=1):
    """
    Scrape Seek using curl-cffi to bypass anti-bot protection.
    Returns list of job dicts.
    """
    jobs = []

    for page in range(1, pages + 1):
        # Build URL based on location
        loc_slug = location.replace(' ', '-').replace(',', '')
        if location == "All Australia":
            url = f"{BASE}/{keywords.replace(' ', '-')}-jobs"
        elif location == "Remote":
            url = f"{BASE}/{keywords.replace(' ', '-')}-jobs/in-{loc_slug}"
        else:
            url = f"{BASE}/{keywords.replace(' ', '-')}-jobs/in-{loc_slug}"
        params = {"page": page}

        try:
            r = requests.get(url, params=params, headers=HEADERS,
                           impersonate="chrome124", timeout=20)
            if r.status_code != 200:
                print(f"Seek returned {r.status_code} for page {page}")
                continue
        except Exception as e:
            print(f"Seek request error (page {page}): {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all("article", attrs={"data-card-type": "JobCard"})

        if not cards:
            print(f"No job cards found on page {page} (Seek layout may have changed)")
            continue

        for card in cards:
            try:
                title_el = card.find("a", attrs={"data-automation": "jobTitle"})
                company_el = card.find("a", attrs={"data-automation": "jobCompany"})
                loc_el = card.find("a", attrs={"data-automation": "jobLocation"})
                snippet_el = card.find("span", attrs={"data-automation": "jobShortDescription"})

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if href and not href.startswith("http"):
                    href = BASE + href

                source_id = None
                match = re.search(r"/job/(\d+)", href)
                if match:
                    source_id = f"seek-{match.group(1)}"
                else:
                    # Use hash of title+company as fallback unique ID
                    source_id = f"seek-{hash(title + (company or ''))}"

                company = company_el.get_text(strip=True) if company_el else None
                loc = loc_el.get_text(strip=True) if loc_el else location
                snippet = snippet_el.get_text(strip=True) if snippet_el else None

                # Extract posting date
                date_el = card.find(attrs={"data-automation": "jobListingDate"})
                date_text = date_el.get_text(strip=True) if date_el else None
                posted_at = parse_relative_date(date_text) if date_text else datetime.utcnow()
                first_seen = posted_at or datetime.utcnow()

                direct = company is not None and not is_recruiter(company)

                jobs.append({
                    "source": "seek",
                    "source_id": source_id or f"seek-{hash(title + (company or ''))}",
                    "title": title,
                    "location": loc,
                    "snippet": snippet,
                    "url": href,
                    "listed_company": company,
                    "is_direct": direct,
                    "scraped_at": datetime.utcnow(),
                    "first_seen": first_seen,
                })
            except Exception as e:
                print(f"Card parse error: {e}")
                continue

    # Deduplicate by source_id (promoted + standard listings share IDs)
    seen = set()
    unique = []
    for j in jobs:
        if j["source_id"] not in seen:
            seen.add(j["source_id"])
            unique.append(j)

    # Fetch full descriptions for recruiter-hidden jobs
    for j in unique:
        if not j["is_direct"]:
            j["description"] = fetch_job_description(j["url"])

    return unique


def fetch_job_description(job_url: str) -> str | None:
    """Fetch the full job description from a Seek job detail page."""
    try:
        r = requests.get(job_url, headers=HEADERS, impersonate="chrome124", timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        desc = soup.find("div", attrs={"data-automation": "jobAdDetails"})
        if desc:
            return desc.get_text("\n", strip=True)
    except Exception as e:
        print(f"Description fetch error: {e}")
    return None


INDEED_BASE = "https://au.indeed.com"


def scrape_indeed(keywords="software engineer", location="Sunshine Coast QLD", pages=1):
    """Scrape Indeed Australia jobs. Uses Safari impersonation to bypass blocks."""
    jobs = []

    for page in range(pages):
        start = page * 10  # Indeed uses 0-based offset
        url = f"{INDEED_BASE}/jobs"
        params = {
            "q": keywords,
            "l": location,
            "start": start,
        }
        if location == "All Australia":
            params.pop("l", None)

        try:
            r = requests.get(url, params=params, impersonate="safari17_0", timeout=20)
            if r.status_code != 200:
                print(f"Indeed returned {r.status_code} for page {page}")
                continue
        except Exception as e:
            print(f"Indeed request error (page {page}): {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all("a", attrs={"data-jk": True})

        for card in cards:
            try:
                jk = card.get("data-jk", "")
                title = card.get_text(strip=True)
                href = f"{INDEED_BASE}/viewjob?jk={jk}"
                source_id = f"indeed-{jk}"

                parent = card.find_parent("li") or card.find_parent("div")
                company = None
                location_str = location
                snippet = None

                if parent:
                    co = parent.find("span", attrs={"data-testid": "company-name"})
                    if co:
                        company = co.get_text(strip=True)
                    loc = parent.find("div", attrs={"data-testid": "text-location"})
                    if loc:
                        location_str = loc.get_text(strip=True)
                    snip = parent.find("div", attrs={"data-testid": "jobsnippet_footer"})
                    if snip:
                        snippet = snip.get_text(strip=True)
                    # Also try getting snippet from the listing
                    if not snippet:
                        ul = parent.find("ul")
                        if ul:
                            snippet = ul.get_text(strip=True)

                direct = company is not None and not is_recruiter(company)

                jobs.append({
                    "source": "indeed",
                    "source_id": source_id,
                    "title": title,
                    "location": location_str,
                    "snippet": snippet,
                    "url": href,
                    "listed_company": company,
                    "is_direct": direct,
                    "scraped_at": datetime.utcnow(),
                    "first_seen": datetime.utcnow(),  # Indeed cards don't show date
                })
            except Exception as e:
                print(f"Indeed card parse error: {e}")
                continue

    return jobs


JORA_BASE = "https://au.jora.com"


def scrape_jora(keywords="software engineer", location="Sunshine Coast QLD", pages=1):
    """Scrape Jora Australia job aggregator."""
    jobs = []

    for page in range(pages):
        url = f"{JORA_BASE}/j"
        params = {"q": keywords, "l": location, "p": page + 1}

        try:
            r = requests.get(url, params=params, impersonate="chrome124", timeout=20)
            if r.status_code != 200:
                print(f"Jora returned {r.status_code} for page {page}")
                continue
        except Exception as e:
            print(f"Jora request error (page {page}): {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        # Jora has job cards with job-info and job-abstract divs
        info_divs = soup.find_all("div", class_="job-info")
        title_els = soup.find_all(class_="job-title")
        abstracts = soup.find_all("div", class_="job-abstract")

        # Match titles to info divs by finding the parent job card
        for title_el in title_els:
            try:
                card = title_el.find_parent("div", class_=lambda c: c and "job-card" in str(c).lower() if c else False)
                if not card:
                    continue

                title = title_el.get_text(strip=True)
                link_el = card.find("a", href=True)
                href = link_el.get("href", "") if link_el else ""
                if href and not href.startswith("http"):
                    href = JORA_BASE + href

                source_id = f"jora-{hash(href)}"

                # Get company and location from job-info
                info = card.find("div", class_="job-info")
                company = None
                location_str = location
                if info:
                    parts = [p.strip() for p in info.get_text("|").split("|")]
                    if len(parts) >= 1:
                        company = parts[0] if parts[0] and not parts[0].replace(".", "").isdigit() else None
                    if len(parts) >= 3:
                        location_str = parts[2] if parts[2] else location_str
                    elif len(parts) >= 2 and parts[1] and not parts[1].replace(".", "").isdigit():
                        location_str = parts[1]

                # Get snippet from job-abstract
                abstract = card.find("div", class_="job-abstract")
                snippet = abstract.get_text(strip=True) if abstract else None

                direct = company is not None and not is_recruiter(company)

                jobs.append({
                    "source": "jora",
                    "source_id": source_id,
                    "title": title,
                    "location": location_str,
                    "snippet": snippet,
                    "url": href,
                    "listed_company": company,
                    "is_direct": direct,
                    "scraped_at": datetime.utcnow(),
                    "first_seen": datetime.utcnow(),
                })
            except Exception as e:
                print(f"Jora card parse error: {e}")
                continue

    return jobs
