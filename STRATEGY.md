# Employer Identification — Strategy & Progress Tracking

## Identification Methods (Ordered by Reliability)

### 1. Direct Cross-Reference (Highest Confidence)
The employer posts the SAME role on their own careers page AND via a recruiter.
- Scrape employer careers pages we know about
- Fuzzy-match JD title + location + tech stack
- If match found → 95%+ confidence
- **Progress signal:** "Cross-reference match found → [Employer Name]"

### 2. JD Fingerprint Matching
Every company writes job ads differently. Extract a "fingerprint" of unique phrases
and match against a database of known employer descriptions.
- "Award-winning SaaS platform serving 10,000+ businesses"
- "We're a team of 50 engineers building the future of logistics"
- "Free lunch, Friday drinks, ESOP, dog-friendly office"
- **Progress signal:** "3 fingerprints match [Employer A], 2 match [Employer B]"

### 3. Location + Industry + Headcount Triangulation
"Fintech startup in Maroochydore with 30-50 engineers" — that's maybe 3 companies.
- Query LinkedIn/Google Maps for companies matching the profile
- Narrow by tech stack mentioned in JD
- **Progress signal:** "Narrowed to 4 possible employers in Maroochydore"

### 4. Salary & Benefits Fingerprint
Specific combinations are unique: "$130K + ESOP + 6 weeks leave + conference budget"
- Match against known salary data (Glassdoor, Levels.fyi, Seek salary insights)
- **Progress signal:** "Benefits package matches 2 known employers"

### 5. Logo / Brand Detection
Some recruiter ads embed the employer's branding:
- Watermark or header image in the ad
- Color scheme matches a known brand
- OCR on images for company names
- **Progress signal:** "Logo detected — reverse image search pending"

### 6. Recruiter Specialization
Some recruiters specialize in specific companies or industries:
- "This recruiter has placed 12 roles at Company X in the past 6 months"
- Track which recruiters post for which employers over time
- **Progress signal:** "Recruiter history: 80% of their roles are for fintech clients"

---

## Progress Feedback — What the Dashboard Shows

### Per Job
```
┌─────────────────────────────────────────────────┐
│ Senior Python Developer — Maroochydore          │
│ Posted by: Absolute IT (Recruiter)               │
│                                                  │
│ 🔍 Analysis Progress    ████████░░ 80%          │
│                                                  │
│ ✅ Cross-reference: No direct match found        │
│ ✅ JD Fingerprint:   3 phrases match Weeha       │
│ ✅ Location+Industry: 4 possible employers       │
│ ⏳ Benefits Match:    Pending                    │
│ ⬜ Logo Detection:    Not attempted              │
│                                                  │
│ Top Match: Weeha (67% confidence)                │
│ Evidence: "React Native + AI-Assisted",          │
│           "fast-growing Australian startup",     │
│           Maroochydore fintech                   │
└─────────────────────────────────────────────────┘
```

### Per Agent Run
| Agent | Jobs Processed | Employers Found | Avg Confidence | Time |
|---|---|---|---|---|
| JD Fingerprinter | 23 | 8 | 72% | 2:14 |
| Location Triangulator | 23 | 5 | 45% | 1:08 |
| Logo Detector | 23 | 1 | 90% | 0:32 |

### Overall Stats
- 50 jobs scraped
- 32 recruiter-hidden (64%)
- 18 employers identified (56% of hidden)
- 12 confirmed (candidate reported match)
- Avg time to identify: 3.2 minutes per job

---

## Confidence Tiers

| Tier | Range | Criteria |
|---|---|---|
| **Confirmed** | 95%+ | Cross-reference match with employer careers page |
| **High** | 70-94% | Multiple fingerprints + location + industry align |
| **Medium** | 40-69% | Some fingerprints or location match, but ambiguous |
| **Low** | 10-39% | Weak signals, needs more data |
| **Unknown** | 0% | No analysis run yet |

---

## Agent Architecture

```
Job Scraped → Queue → [Agent Swarm]
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                     ▼
JD Fingerprinter   Location Triangulator   Logo Detector
    │                    │                     │
    └────────────────────┼────────────────────┘
                         ▼
                   Confidence Aggregator
                         │
                         ▼
                Employer Match → Dashboard
```

Agents run in parallel. The aggregator weights each method by historical accuracy
and combines confidence scores.
