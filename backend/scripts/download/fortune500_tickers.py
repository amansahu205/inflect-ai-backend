import pandas as pd

df = pd.read_csv("sp500_companies.csv")
tickers = df['ticker'].tolist()
print(f"Total tickers: {len(tickers)}")
print(tickers[:10])

# Save for other scripts
with open("tickers.txt", "w") as f:
    f.write("\n".join(tickers))