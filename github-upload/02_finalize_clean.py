"""
Step 2: Finalize the cleaned data (run once, after 01_collect_and_clean.py).

Reads : data/clean_jobs.csv, data/job_skills.csv
Writes: data/clean_jobs_final.csv   (the file to use from now on)
        data/report.txt             (numbers to quote in your README)
Nothing is deleted: problems are flagged in new columns.
"""
import pandas as pd

df = pd.read_csv("data/clean_jobs.csv")
skills = pd.read_csv("data/job_skills.csv")
report = []

def log(text=""):
    print(text)
    report.append(str(text))

log(f"Jobs loaded: {len(df)}")

# ---------- 1. CITY FIX ----------
NOT_CITIES = {
    "India", "Maharashtra", "Karnataka", "Telangana", "Tamil Nadu",
    "Gujarat", "Rajasthan", "Uttar Pradesh", "West Bengal", "Kerala",
    "Haryana", "Punjab", "Andhra Pradesh", "Madhya Pradesh", "Odisha",
    "Bihar", "Jharkhand", "Assam", "Chhattisgarh", "Uttarakhand",
}
mask = df["city"].isin(NOT_CITIES) | df["city"].isna()
df.loc[mask, "city"] = "Unspecified"
log(f"\n[City] Relabelled {mask.sum()} rows as 'Unspecified' "
    f"({mask.mean():.0%} of jobs)")
log("Top cities:")
log(df["city"].value_counts().head(12).to_string())

# ---------- 2. SALARY CHECKS ----------
s = df[df["salary_avg"].notna()]
log(f"\n[Salary] Jobs with salary: {len(s)} of {len(df)} ({len(s)/len(df):.0%})")
log("Note: salary_is_predicted is 0 everywhere, including rows with no "
    "salary, so it can't be trusted as proof the salaries are real.")
log(f"Share where salary_min == salary_max: "
    f"{(s['salary_min'] == s['salary_max']).mean():.0%}")
log("Most repeated salary values (many repeats may hint at estimates):")
log(s["salary_avg"].value_counts().head(5).to_string())

# ---------- 3. OUTLIER FLAGS (flag, don't delete) ----------
q1, q3 = s["salary_avg"].quantile([0.25, 0.75])
upper = q3 + 1.5 * (q3 - q1)
df["salary_outlier"] = False
df.loc[df["salary_avg"] > upper, "salary_outlier"] = True
# Entry-level title with a very high salary is more suspicious
df["salary_suspicious"] = (df["level"] == "Entry") & (df["salary_avg"] > upper)

log(f"\n[Outliers] Median salary: {s['salary_avg'].median():,.0f}")
log(f"IQR upper threshold: {upper:,.0f}")
log(f"Flagged as outlier: {df['salary_outlier'].sum()}")
log(f"Flagged as suspicious (entry-level + very high): "
    f"{df['salary_suspicious'].sum()}")
log("Highest salaries (check these by eye):")
log(df.sort_values("salary_avg", ascending=False)
      [["title", "company", "city", "level", "salary_avg"]]
      .head(10).to_string(index=False))

log("\nSalary coverage by level (aim for 30+ per level):")
log(df.groupby("level")["salary_avg"].agg(["count", "median"]).round(0).to_string())

# ---------- 4. SKILL BIAS CHECK ----------
# One of our searches was "power bi developer", which can inflate Power BI.
others = df.loc[df["search_query"] != "power bi developer", "job_id"]
all_counts = skills["skill"].value_counts()
other_counts = skills[skills["job_id"].isin(others)]["skill"].value_counts()
compare = pd.DataFrame({"all_jobs": all_counts,
                        "without_powerbi_query": other_counts}).fillna(0).astype(int)
log(f"\n[Bias check] Jobs excluding 'power bi developer' search: {len(others)}")
log(compare.head(10).to_string())

# ---------- 5. SAVE ----------
df.to_csv("data/clean_jobs_final.csv", index=False)
with open("data/report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report))
log("\nSaved: data/clean_jobs_final.csv and data/report.txt")
