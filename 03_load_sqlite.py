"""
Step 3: Load cleaned CSVs into SQLite, run queries.sql, export results.

Needs: data/clean_jobs_final.csv, data/job_skills.csv, queries.sql (same folder)
Makes: data/jobs.db
       data/query_results/<query_name>.csv   (use these in Power BI / Tableau)
No extra installs: sqlite3 comes with Python.
"""
import os
import re
import sqlite3
import pandas as pd

os.makedirs("data/query_results", exist_ok=True)

jobs = pd.read_csv("data/clean_jobs_final.csv", dtype={"job_id": str})
skills = pd.read_csv("data/job_skills.csv", dtype={"job_id": str})

# Keep only skill rows whose job still exists after de-duplication
skills = skills[skills["job_id"].isin(jobs["job_id"])].drop_duplicates()

# Unbiased sample: exclude jobs found only through the "power bi developer" search
jobs["in_unbiased_sample"] = (jobs["search_query"] != "power bi developer").astype(int)

keep = ["job_id", "title", "company", "city", "level", "month",
        "salary_min", "salary_max", "salary_avg", "salary_outlier",
        "skill_count", "search_query", "in_unbiased_sample", "url"]
jobs = jobs[keep]

con = sqlite3.connect("data/jobs.db")
jobs.to_sql("jobs", con, if_exists="replace", index=False)
skills.to_sql("job_skills", con, if_exists="replace", index=False)
con.execute("CREATE INDEX IF NOT EXISTS idx_skills_job ON job_skills(job_id)")
con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city)")
con.commit()

print(f"Loaded {len(jobs)} jobs and {len(skills)} job-skill rows into data/jobs.db")
print(f"Unbiased sample size: {jobs['in_unbiased_sample'].sum()} jobs\n")

# Split queries.sql on the "-- name: xxx" markers
sql_text = open("queries.sql", encoding="utf-8").read()
parts = re.split(r"^-- name:\s*(\w+)\s*$", sql_text, flags=re.MULTILINE)
queries = dict(zip(parts[1::2], parts[2::2]))

for name, sql in queries.items():
    result = pd.read_sql_query(sql, con)
    result.to_csv(f"data/query_results/{name}.csv", index=False)
    print(f"=== {name} ({len(result)} rows) ===")
    print(result.head(10).to_string(index=False))
    print()

con.close()
print("Done. Results saved in data/query_results/")
