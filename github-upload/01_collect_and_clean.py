"""
Step 1: Collect and clean data-analyst job postings for India (Adzuna API).

Setup:
  1. Register free at https://developer.adzuna.com/ -> get APP_ID and APP_KEY
  2. pip install requests pandas
  3. Set env vars:  ADZUNA_APP_ID, ADZUNA_APP_KEY
  4. python 01_collect_and_clean.py

Outputs:
  data/raw_jobs.csv       (untouched API data, keep for reproducibility)
  data/clean_jobs.csv     (one row per job)
  data/job_skills.csv     (one row per job-skill pair, ready for SQL)
"""
import os
import re
import time
import requests
import pandas as pd

APP_ID = os.environ["ADZUNA_APP_ID"]
APP_KEY = os.environ["ADZUNA_APP_KEY"]
QUERIES = ["data analyst", "business analyst", "bi analyst", "power bi developer"]
PAGES_PER_QUERY = 10          # 50 results per page
os.makedirs("data", exist_ok=True)

# ---------- 1. COLLECT ----------
def fetch(query, page):
    url = f"https://api.adzuna.com/v1/api/jobs/in/search/{page}"
    params = {"app_id": APP_ID, "app_key": APP_KEY,
              "results_per_page": 50, "what": query,
              "content-type": "application/json"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])

rows = []
for q in QUERIES:
    for p in range(1, PAGES_PER_QUERY + 1):
        try:
            results = fetch(q, p)
        except requests.RequestException as e:
            print(f"Skipping {q} page {p}: {e}")
            continue
        if not results:
            break
        for j in results:
            rows.append({
                "job_id": j.get("id"),
                "title": j.get("title"),
                "company": (j.get("company") or {}).get("display_name"),
                "location": (j.get("location") or {}).get("display_name"),
                "salary_min": j.get("salary_min"),
                "salary_max": j.get("salary_max"),
                "salary_is_predicted": j.get("salary_is_predicted"),
                "created": j.get("created"),
                "description": j.get("description"),
                "url": j.get("redirect_url"),
                "search_query": q,
            })
        time.sleep(1)  # be polite to the API

raw = pd.DataFrame(rows)
raw.to_csv("data/raw_jobs.csv", index=False)
print(f"Collected {len(raw)} raw rows")

# ---------- 2. CLEAN ----------
df = raw.copy()

# 2a. Remove duplicates (same posting returned by multiple queries)
df = df.drop_duplicates(subset="job_id")
df = df.drop_duplicates(subset=["title", "company", "location"])

# 2b. Standardize cities (first part of "Area, City, State")
CITY_MAP = {"bangalore": "Bengaluru", "bengaluru": "Bengaluru",
            "bombay": "Mumbai", "gurgaon": "Gurugram",
            "new delhi": "Delhi", "madras": "Chennai"}

def clean_city(loc):
    if not isinstance(loc, str):
        return None
    parts = [p.strip() for p in loc.split(",")]
    # Adzuna lists most specific first; pick the part that matches a known city
    for p in parts:
        key = p.lower()
        if key in CITY_MAP:
            return CITY_MAP[key]
    return parts[0].title()

df["city"] = df["location"].apply(clean_city)

# 2c. Salary: keep numeric, compute average, flag predicted values
df["salary_avg"] = df[["salary_min", "salary_max"]].mean(axis=1)
# Drop absurd values (adjust after looking at your own distribution)
df.loc[(df["salary_avg"] < 100_000) | (df["salary_avg"] > 10_000_000),
       ["salary_min", "salary_max", "salary_avg"]] = None

# 2d. Dates
df["created"] = pd.to_datetime(df["created"], errors="coerce")
df["month"] = df["created"].dt.to_period("M").astype(str)

# 2e. Experience level guessed from title (document this limitation!)
def level(title):
    t = str(title).lower()
    if re.search(r"\b(senior|sr|lead|principal|manager|head)\b", t):
        return "Senior"
    if re.search(r"\b(junior|jr|intern|trainee|fresher|entry)\b", t):
        return "Entry"
    return "Mid"

df["level"] = df["title"].apply(level)

# ---------- 3. EXTRACT SKILLS ----------
SKILLS = {
    "SQL": r"\bsql\b", "Python": r"\bpython\b", "Excel": r"\bexcel\b",
    "Power BI": r"power\s?bi", "Tableau": r"\btableau\b", "R": r"\br\b(?=[ ,/])",
    "Looker": r"\blooker\b", "Statistics": r"\bstatistic",
    "Machine Learning": r"machine learning", "AWS": r"\baws\b",
    "Azure": r"\bazure\b", "Snowflake": r"\bsnowflake\b",
    "Spark": r"\bspark\b", "ETL": r"\betl\b", "DAX": r"\bdax\b",
}
text = (df["title"].fillna("") + " " + df["description"].fillna("")).str.lower()

skill_rows = []
for skill, pattern in SKILLS.items():
    hit = text.str.contains(pattern, regex=True)
    for jid in df.loc[hit, "job_id"]:
        skill_rows.append({"job_id": jid, "skill": skill})

job_skills = pd.DataFrame(skill_rows)
df["skill_count"] = df["job_id"].map(job_skills.groupby("job_id").size()).fillna(0).astype(int)

# ---------- 4. SAVE ----------
df.drop(columns=["description"]).to_csv("data/clean_jobs.csv", index=False)
job_skills.to_csv("data/job_skills.csv", index=False)

print(f"Clean jobs: {len(df)}")
print(f"Jobs with salary: {df['salary_avg'].notna().sum()}")
print(f"Job-skill pairs: {len(job_skills)}")
print(job_skills["skill"].value_counts().head(10))
