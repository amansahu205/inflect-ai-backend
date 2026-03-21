import finnhub
import json
import os
import time
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
# Go up 3 levels: download → scripts → backend → inflect (root)
ROOT_DIR = BASE_DIR.parents[2]
DATA_DIR = ROOT_DIR / "data"

# Create folders
os.makedirs(DATA_DIR / "news", exist_ok=True)
os.makedirs(DATA_DIR / "metrics", exist_ok=True)
os.makedirs(DATA_DIR / "prices", exist_ok=True)
os.makedirs(DATA_DIR / "fundamentals", exist_ok=True)
os.makedirs(DATA_DIR / "recommendations", exist_ok=True)

# Load .env from root
load_dotenv(ROOT_DIR / ".env")


# Load from project root regardless of 
# where script is run from
env_path = Path(__file__).resolve(
).parents[3] / '.env'
load_dotenv(env_path)

FINNHUB_KEY = os.getenv("FINNHUB_KEY")

client = finnhub.Client(api_key=FINNHUB_KEY)

df = pd.read_csv("sp500_companies.csv")
TICKERS = df['ticker'].tolist()

os.makedirs("data/recommendations", exist_ok=True)

for ticker in tqdm(TICKERS):
    try:
        recs = client.recommendation_trends(ticker)
        if recs:
            with open(
                f"data/recommendations/{ticker}.json",
                "w"
            ) as f:
                json.dump(recs[:12], f, indent=2)
        time.sleep(1.1)
    except Exception as e:
        tqdm.write(f"✗ {ticker}: {e}")

print("Done — recommendations downloaded")
