#!/usr/bin/env python3
"""Seed Sunshine Coast employer database."""
import sys
sys.path.insert(0, "/home/peter/recruiter-bypass")

from app.database import init_db, SessionLocal
from app.models import Employer

init_db()
db = SessionLocal()

employers = [
    # --- Maroochydore CBD ---
    ("Youi Insurance", "youi.com.au", "https://youi.com.au/careers", True,
     "Sunshine Coast HQ, insurtech, .NET/Azure/React, 1000+ staff"),
    ("Auto & General", "autogeneral.com.au", "https://autogeneral.com.au/careers", True,
     "Insurance group, Python/React, microservices, major SC employer"),
    ("Sunshine Coast Council", "sunshinecoast.qld.gov.au", "https://sunshinecoast.qld.gov.au/council/employment", True,
     "Local government, IT/cloud/geospatial, 2000+ staff"),
    ("Huddle Insurance", "huddle.com.au", "https://huddle.com.au/careers", True,
     "Insurtech, digital-first, growing engineering team"),
    ("Mighty Kingdom", "mightykingdom.com", None, True,
     "Game development studio, Unity/Unreal, creative tech"),
    # --- Kawana / Birtinya ---
    ("Sunshine Coast University Hospital", "health.qld.gov.au/sunshinecoast", "https://smartjobs.qld.gov.au", True,
     "Major public hospital, health IT/clinical systems, 5000+ staff"),
    ("USC Thompson Institute", "usc.edu.au", None, True,
     "University mental health research, data science"),
    # --- Noosa / Noosaville ---
    ("Noosa Council", "noosa.qld.gov.au", "https://noosa.qld.gov.au/council/employment", True,
     "Local government, IT/digital services"),
    ("Neto", "netohq.com", None, True,
     "Noosa e-commerce SaaS platform, acquired by Maropost"),
    # --- Caloundra ---
    ("Caloundra RSL", "caloundrarsl.com.au", None, True,
     "Major club/entertainment venue, IT systems"),
    # --- Nambour ---
    ("Queensland Health (Nambour Hospital)", "health.qld.gov.au", None, True,
     "Regional hospital, health IT, clinical systems"),
    # --- Coolum ---
    ("Coolum Beach Resort", "coolumresort.com.au", None, True,
     "Major resort, IT systems, digital booking"),
    # --- Sippy Downs / University ---
    ("University of the Sunshine Coast", "usc.edu.au", "https://usc.edu.au/about/careers", True,
     "University, IT/enterprise systems/cybersecurity, 2000+ staff"),
    ("Shine Lawyers", "shine.com.au", "https://shine.com.au/careers", True,
     "National law firm, IT/digital/cybersecurity, SC office"),
    # --- Warana / Bokarina ---
    ("Peregian Digital Hub", "peregianhub.com.au", None, True,
     "Tech coworking space, multiple startups"),
    # --- SC Airport ---
    ("Sunshine Coast Airport", "sunshinecoastairport.com.au", None, True,
     "Airport operator, IT/systems"),
    # --- Major Nationals with SC presence ---
    ("Suncorp (SC office)", "suncorp.com.au", "https://suncorp.com.au/careers", True,
     "Major insurer, SC tech hub, cloud/agile"),
    ("CommBank (SC office)", "commbank.com.au", "https://commbank.com.au/careers", True,
     "Major bank, technology hub"),
    ("Coles Group (SC)", "colesgroup.com.au", "https://colesgroup.com.au/careers", True,
     "Retail/tech, SC distribution centre"),
    ("Woolworths Group (SC)", "woolworthsgroup.com.au", "https://woolworthsgroup.com.au/careers", True,
     "Retail/tech, SC operations"),
    # --- Hospitality / Tourism Tech ---
    ("Mantra Group (Accor)", "all.accor.com", "https://careers.accor.com", True,
     "Major hotel chain, SC properties, IT/digital"),
    ("Australia Zoo", "australiazoo.com.au", "https://australiazoo.com.au/about-us/careers", True,
     "Major tourist attraction, IT/digital/marketing"),
    ("Sea Life Sunshine Coast", "visitsealife.com", None, True,
     "Aquarium/attraction, IT/systems"),
    # --- Healthcare ---
    ("UnitingCare (SC)", "unitingcareqld.com.au", "https://unitingcareqld.com.au/careers", True,
     "Major healthcare provider, health IT, clinical systems"),
    ("Blue Care", "bluecare.org.au", None, True,
     "Aged care/health, IT systems, SC offices"),
    # --- Tech / Digital ---
    ("Atmail", "atmail.com", None, True,
     "Email SaaS platform, SC-based tech company"),
    ("HeliMods", "helimods.com", None, True,
     "Aerospace simulation tech, SC-based, software engineering"),
    ("EPEC Group", "epecgroup.com", None, True,
     "Engineering/electrical, SC-based, IT/Automation"),
    # --- Construction / Infrastructure ---
    ("Fulton Hogan (SC)", "fultonhogan.com", "https://fultonhogan.com/careers", True,
     "Infrastructure/construction, IT systems, SC operations"),
    # --- Education ---
    ("TAFE Queensland (SC)", "tafeqld.edu.au", "https://tafeqld.edu.au/about/careers", True,
     "Vocational education, IT/digital, multiple SC campuses"),
    ("Matthew Flinders Anglican College", "mfac.edu.au", None, True,
     "Private school, IT/EdTech, SC"),
    ("Sunshine Coast Grammar School", "scgs.qld.edu.au", None, True,
     "Private school, IT/EdTech, SC"),
]

added = 0
for name, domain, careers_url, direct, notes in employers:
    existing = db.query(Employer).filter(Employer.name == name).first()
    if not existing:
        db.add(Employer(name=name, domain=domain, careers_url=careers_url,
                       is_direct_hire=direct, notes=notes))
        added += 1

db.commit()
total = db.query(Employer).count()
print(f"Added {added} new, total {total} employers")
db.close()
