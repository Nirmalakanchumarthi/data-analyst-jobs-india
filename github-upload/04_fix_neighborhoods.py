"""
Step 4: Roll neighborhood names up to their parent city.

Reads : data/clean_jobs_final.csv
Writes: data/clean_jobs_final.csv   (updated)
        data/clean_jobs_final_backup.csv (copy of the file before this step)
Only changes places I'm confident about. Check the leftover list at the end.
"""
import shutil
import pandas as pd

shutil.copy("data/clean_jobs_final.csv", "data/clean_jobs_final_backup.csv")
df = pd.read_csv("data/clean_jobs_final.csv")

NEIGHBORHOOD_TO_CITY = {
    # Mumbai
    "Chembur": "Mumbai", "Goregaon East": "Mumbai",
    "Mulund West": "Mumbai", "Prabhadevi": "Mumbai",
    # Pune
    "Hadapsar": "Pune", "Vadgaon Sheri": "Pune",
    "Yerwada": "Pune", "Range Hills": "Pune",
    # Chennai
    "Nungambakkam": "Chennai", "Egmore Nungambakkam": "Chennai",
    "Royapettah": "Chennai", "Jafferkhanpet": "Chennai",
    "Injambakkam": "Chennai",
    # Ahmedabad
    "Ambawadi Vistar": "Ahmedabad", "Bodakdev": "Ahmedabad",
    # Delhi
    "Saket": "Delhi", "Nauroji Nagar": "Delhi",
    # Hyderabad
    "Secunderabad": "Hyderabad", "Hussainialam": "Hyderabad",
}

changed = df["city"].isin(NEIGHBORHOOD_TO_CITY).sum()
df["city"] = df["city"].replace(NEIGHBORHOOD_TO_CITY)
print(f"Rolled up {changed} rows into their parent city\n")

print("Top 15 cities now:")
print(df["city"].value_counts().head(15).to_string())

# Anything with fewer than 3 jobs is probably a small town or a neighborhood
# I wasn't sure about. Review this list and add any you recognize above.
counts = df["city"].value_counts()
leftover = counts[(counts < 3) & (counts.index != "Unspecified")]
print(f"\nSmall places left ({len(leftover)}), check if any belong to a big city:")
print(", ".join(leftover.index))

df.to_csv("data/clean_jobs_final.csv", index=False)
print("\nSaved data/clean_jobs_final.csv")
