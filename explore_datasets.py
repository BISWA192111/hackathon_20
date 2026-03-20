import pandas as pd
import os
from pathlib import Path

print("=" * 80)
print("EXPLORING DATASETS")
print("=" * 80)

# Read job descriptions
try:
    df_jobs = pd.read_csv('job_title_des.csv/job_title_des.csv')
    print("\n=== JOB DESCRIPTIONS DATASET ===")
    print(f"Shape: {df_jobs.shape}")
    print(f"Columns: {df_jobs.columns.tolist()}")
    print(f"\nFirst row sample:")
    print(df_jobs.iloc[0])
    print(f"\nSample job titles:")
    for title in df_jobs['Job_Title'].unique()[:10]:
        print(f"  - {title}")
except Exception as e:
    print(f"Error reading job descriptions: {e}")

# Check O*NET database
print("\n=== O*NET DATABASE ===")
onet_path = Path('db_30_1_excel/db_30_1_excel')
if onet_path.exists():
    files = list(onet_path.glob('*'))
    print(f"Files found: {len(files)}")
    for f in files[:20]:
        print(f"  - {f.name}")
else:
    print("O*NET folder not found")

# Check data folder
print("\n=== EXISTING DATA ===")
data_path = Path('data')
if data_path.exists():
    files = list(data_path.glob('*'))
    print(f"Files in data/: {len(files)}")
    for f in files:
        print(f"  - {f.name} ({f.stat().st_size} bytes)")
