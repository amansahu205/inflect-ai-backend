import yfinance as yf
import pandas as pd
import json
import os
import time
from tqdm import tqdm
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


# Load tickers from your SP500 CSV
df = pd.read_csv("sp500_companies.csv")
TICKERS = df['ticker'].tolist()

os.makedirs("data/prices", exist_ok=True)
os.makedirs("data/fundamentals", exist_ok=True)

failed = []

print(f"=== Downloading {len(TICKERS)} tickers ===\n")

for ticker in tqdm(TICKERS):
    try:
        stock = yf.Ticker(ticker)
        
        # 10 year OHLCV
        hist = stock.history(period="10y")
        if not hist.empty:
            hist.to_csv(f"data/prices/{ticker}.csv")
        
        # Fundamentals
        info = stock.info
        fundamentals = {
            "ticker": ticker,
            "name": info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get(
                "priceToSalesTrailing12Months"),
            "eps": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),
            "gross_margins": info.get("grossMargins"),
            "operating_margins": info.get("operatingMargins"),
            "profit_margins": info.get("profitMargins"),
            "ebitda": info.get("ebitda"),
            "ebitda_margins": info.get("ebitdaMargins"),
            "total_cash": info.get("totalCash"),
            "total_debt": info.get("totalDebt"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "fcf": info.get("freeCashflow"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "description": info.get("longBusinessSummary"),
            "employees": info.get("fullTimeEmployees"),
            "website": info.get("website"),
            "ceo": info.get("companyOfficers", 
                [{}])[0].get("name") if info.get(
                "companyOfficers") else None,
        }
        
        with open(
            f"data/fundamentals/{ticker}.json", "w"
        ) as f:
            json.dump(fundamentals, f, indent=2)
        
        # Avoid rate limiting
        time.sleep(0.3)
        
    except Exception as e:
        failed.append(ticker)
        tqdm.write(f"✗ {ticker}: {e}")

print(f"\n=== Done ===")
print(f"Success: {len(TICKERS) - len(failed)}")
print(f"Failed: {len(failed)}")
if failed:
    print(f"Failed tickers: {failed}")
    with open("failed_tickers.txt", "w") as f:
        f.write("\n".join(failed))