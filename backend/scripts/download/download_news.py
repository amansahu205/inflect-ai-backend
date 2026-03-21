import finnhub
import json
import os
import time
import pandas as pd
from tqdm import tqdm
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

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

os.makedirs("data/news", exist_ok=True)
os.makedirs("data/metrics", exist_ok=True)

today = datetime.now().strftime('%Y-%m-%d')
from_date = (
    datetime.now() - timedelta(days=90)
).strftime('%Y-%m-%d')

print(f"=== Downloading News + Metrics ===")
print(f"Tickers: {len(TICKERS)}")
print(f"Date range: {from_date} to {today}\n")

failed_news = []
failed_metrics = []

for ticker in tqdm(TICKERS):
    try:
        # NEWS — free, 1 year history
        news = client.company_news(
            ticker,
            _from=from_date,
            to=today
        )
        
        cleaned_news = []
        for article in news[:50]:
            cleaned_news.append({
                "ticker": ticker,
                "headline": article.get('headline'),
                "summary": article.get('summary'),
                "url": article.get('url'),
                "source": article.get('source'),
                "datetime": article.get('datetime'),
                "category": article.get('category'),
            })
        
        with open(
            f"data/news/{ticker}.json", "w"
        ) as f:
            json.dump(cleaned_news, f, indent=2)

    except Exception as e:
        failed_news.append(ticker)
        tqdm.write(f"✗ news {ticker}: {e}")

    try:
        # BASIC FINANCIALS — free
        metrics = client.company_basic_financials(
            ticker, 'all'
        )
        
        metric_data = metrics.get('metric', {})
        
        # Extract what we need
        extracted = {
            "ticker": ticker,
            "pe_ratio": metric_data.get(
                'peNormalizedAnnual'),
            "pe_ttm": metric_data.get('peTTM'),
            "rsi": metric_data.get('rsi14D') or 
                   metric_data.get('14DayRSI'),
            "52w_high": metric_data.get(
                '52WeekHigh'),
            "52w_low": metric_data.get(
                '52WeekLow'),
            "beta": metric_data.get('beta'),
            "dividend_yield": metric_data.get(
                'currentDividendYieldTTM'),
            "revenue_growth": metric_data.get(
                'revenueGrowthQuarterlyYoy'),
            "gross_margin": metric_data.get(
                'grossMarginTTM'),
            "operating_margin": metric_data.get(
                'operatingMarginTTM'),
            "net_margin": metric_data.get(
                'netProfitMarginTTM'),
            "roe": metric_data.get('roeTTM'),
            "roa": metric_data.get('roaTTM'),
            "debt_equity": metric_data.get(
                'totalDebt/totalEquityAnnual'),
            "current_ratio": metric_data.get(
                'currentRatioAnnual'),
            "eps_ttm": metric_data.get('epsTTM'),
            "price_to_book": metric_data.get(
                'pbAnnual'),
            "price_to_sales": metric_data.get(
                'psTTM'),
            "market_cap": metric_data.get(
                'marketCapitalization'),
        }
        
        with open(
            f"data/metrics/{ticker}.json", "w"
        ) as f:
            json.dump(extracted, f, indent=2)

    except Exception as e:
        failed_metrics.append(ticker)
        tqdm.write(f"✗ metrics {ticker}: {e}")

    # Free tier: 60 req/min = 1/sec
    # Each ticker = 2 calls
    # 503 × 2 = 1006 calls = ~17 minutes
    time.sleep(1.1)

print(f"\n=== Done ===")
print(f"News failed: {len(failed_news)}")
print(f"Metrics failed: {len(failed_metrics)}")

if failed_news:
    with open("failed_news.txt", "w") as f:
        f.write("\n".join(failed_news))

if failed_metrics:
    with open("failed_metrics.txt", "w") as f:
        f.write("\n".join(failed_metrics))