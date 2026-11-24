import pandas as pd

df = pd.read_csv("data/clean_jobs_final.csv")
c = (df[df["city"] != "Unspecified"]
     .groupby("city").size()
     .reset_index(name="postings")
     .sort_values("postings", ascending=False)
     .head(10))
c.to_csv("data/query_results/city_postings.csv", index=False)
print(c)
