-- Job market analysis queries (SQLite)
-- Skill-demand queries use the unbiased sample (in_unbiased_sample = 1),
-- i.e. excluding postings found only via the "power bi developer" search.
-- Salary queries exclude Entry level (too few rows to analyze).

-- name: q1_top_skills
SELECT
    js.skill,
    COUNT(*) AS jobs,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM jobs WHERE in_unbiased_sample = 1), 1) AS pct_of_jobs
FROM job_skills js
JOIN jobs j ON j.job_id = js.job_id
WHERE j.in_unbiased_sample = 1
GROUP BY js.skill
ORDER BY jobs DESC;

-- name: q2_top_skills_per_city
-- Window function: rank skills inside each city (cities with 30+ jobs only)
WITH city_skill AS (
    SELECT j.city, js.skill, COUNT(*) AS jobs
    FROM job_skills js
    JOIN jobs j ON j.job_id = js.job_id
    WHERE j.in_unbiased_sample = 1
      AND j.city <> 'Unspecified'
      AND j.city IN (
          SELECT city FROM jobs
          WHERE in_unbiased_sample = 1 AND city <> 'Unspecified'
          GROUP BY city HAVING COUNT(*) >= 30)
    GROUP BY j.city, js.skill
),
ranked AS (
    SELECT *, RANK() OVER (PARTITION BY city ORDER BY jobs DESC) AS rnk
    FROM city_skill
)
SELECT city, rnk, skill, jobs
FROM ranked
WHERE rnk <= 5
ORDER BY city, rnk;

-- name: q3_median_salary_by_skill
-- SQLite has no MEDIAN(), so it is built with ROW_NUMBER + COUNT windows
WITH s AS (
    SELECT js.skill, j.salary_avg,
           ROW_NUMBER() OVER (PARTITION BY js.skill ORDER BY j.salary_avg) AS rn,
           COUNT(*)     OVER (PARTITION BY js.skill) AS cnt
    FROM job_skills js
    JOIN jobs j ON j.job_id = js.job_id
    WHERE j.salary_avg IS NOT NULL
      AND j.in_unbiased_sample = 1
      AND j.level <> 'Entry'
)
SELECT skill,
       MAX(cnt) AS jobs_with_salary,
       ROUND(AVG(salary_avg)) AS median_salary
FROM s
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY skill
HAVING MAX(cnt) >= 15
ORDER BY median_salary DESC;

-- name: q4_median_salary_by_city
WITH s AS (
    SELECT city, salary_avg,
           ROW_NUMBER() OVER (PARTITION BY city ORDER BY salary_avg) AS rn,
           COUNT(*)     OVER (PARTITION BY city) AS cnt
    FROM jobs
    WHERE salary_avg IS NOT NULL
      AND city <> 'Unspecified'
      AND level <> 'Entry'
)
SELECT city,
       MAX(cnt) AS jobs_with_salary,
       ROUND(AVG(salary_avg)) AS median_salary
FROM s
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY city
HAVING MAX(cnt) >= 15
ORDER BY median_salary DESC;

-- name: q5_skill_pairs
-- Self-join: which skills appear together in the same posting
SELECT a.skill AS skill_1,
       b.skill AS skill_2,
       COUNT(*) AS jobs_together
FROM job_skills a
JOIN job_skills b ON a.job_id = b.job_id AND a.skill < b.skill
JOIN jobs j ON j.job_id = a.job_id
WHERE j.in_unbiased_sample = 1
GROUP BY a.skill, b.skill
ORDER BY jobs_together DESC
LIMIT 15;

-- name: q6_sql_salary_premium
-- Do postings mentioning SQL pay more? (median, mid and senior only)
WITH tagged AS (
    SELECT j.salary_avg,
           CASE WHEN EXISTS (SELECT 1 FROM job_skills js
                             WHERE js.job_id = j.job_id AND js.skill = 'SQL')
                THEN 'Mentions SQL' ELSE 'No SQL' END AS grp
    FROM jobs j
    WHERE j.salary_avg IS NOT NULL
      AND j.in_unbiased_sample = 1
      AND j.level <> 'Entry'
),
s AS (
    SELECT grp, salary_avg,
           ROW_NUMBER() OVER (PARTITION BY grp ORDER BY salary_avg) AS rn,
           COUNT(*)     OVER (PARTITION BY grp) AS cnt
    FROM tagged
)
SELECT grp,
       MAX(cnt) AS jobs_with_salary,
       ROUND(AVG(salary_avg)) AS median_salary
FROM s
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY grp;

-- name: q7_monthly_trend
-- CTE + LAG for month-over-month change (first/last months may be partial)
WITH monthly AS (
    SELECT month, COUNT(*) AS postings
    FROM jobs
    WHERE month IS NOT NULL AND month <> 'NaT'
    GROUP BY month
    HAVING COUNT(*) >= 30   -- ignore sparse old months (mostly noise)
)
SELECT month,
       postings,
       postings - LAG(postings) OVER (ORDER BY month) AS change_vs_prev_month
FROM monthly
ORDER BY month;
