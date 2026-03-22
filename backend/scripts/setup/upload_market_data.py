"""
Upload fundamentals, news, metrics, 
recommendations to Snowflake
"""

import json
import snowflake.connector
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import os

load_dotenv(Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/.env'))

DATA_DIR = Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/data')

def connect():
    return snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

def upload_fundamentals(cursor, conn):
    files = list(
        (DATA_DIR / 'fundamentals').glob('*.json'))
    print(f"Uploading {len(files)} fundamentals...")
    
    for f in tqdm(files):
        try:
            data = json.loads(f.read_text())
            ticker = f.stem.upper()
            cursor.execute("""
                MERGE INTO FUNDAMENTALS t
                USING (SELECT %s as TICKER) s
                ON t.TICKER = s.TICKER
                WHEN MATCHED THEN UPDATE SET
                    PE_RATIO=%s, EPS=%s,
                    REVENUE=%s, GROSS_MARGIN=%s,
                    PROFIT_MARGIN=%s,
                    DEBT_EQUITY=%s,
                    MARKET_CAP=%s, BETA=%s,
                    ROE=%s, FCF=%s
                WHEN NOT MATCHED THEN INSERT
                    (TICKER, PE_RATIO, EPS,
                     REVENUE, GROSS_MARGIN,
                     PROFIT_MARGIN, DEBT_EQUITY,
                     MARKET_CAP, BETA, ROE, FCF)
                VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                ticker,
                data.get('trailingPE'),
                data.get('trailingEps'),
                data.get('totalRevenue'),
                data.get('grossMargins'),
                data.get('profitMargins'),
                data.get('debtToEquity'),
                data.get('marketCap'),
                data.get('beta'),
                data.get('returnOnEquity'),
                data.get('freeCashflow'),
                ticker,
                data.get('trailingPE'),
                data.get('trailingEps'),
                data.get('totalRevenue'),
                data.get('grossMargins'),
                data.get('profitMargins'),
                data.get('debtToEquity'),
                data.get('marketCap'),
                data.get('beta'),
                data.get('returnOnEquity'),
                data.get('freeCashflow')
            ))
        except Exception as e:
            pass
    conn.commit()
    print("Fundamentals done!")

def upload_news(cursor, conn):
    files = list(
        (DATA_DIR / 'news').glob('*.json'))
    print(f"Uploading news for {len(files)} tickers...")
    
    for f in tqdm(files):
        try:
            articles = json.loads(f.read_text())
            ticker = f.stem.upper()
            
            for article in articles[:20]:
                cursor.execute("""
                    INSERT INTO NEWS
                    (ID, TICKER, HEADLINE,
                     SUMMARY, SOURCE, URL,
                     PUBLISHED_AT)
                    SELECT %s, %s, %s, %s,
                           %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM NEWS
                        WHERE ID = %s
                    )
                """, (
                    str(article.get('id',
                        hash(article.get(
                            'headline','')))),
                    ticker,
                    str(article.get(
                        'headline',''))[:500],
                    str(article.get(
                        'summary',''))[:2000],
                    str(article.get(
                        'source',''))[:100],
                    str(article.get(
                        'url',''))[:500],
                    article.get('datetime'),
                    str(article.get('id',
                        hash(article.get(
                            'headline',''))))
                ))
        except Exception as e:
            pass
    conn.commit()
    print("News done!")

def upload_metrics(cursor, conn):
    files = list(
        (DATA_DIR / 'metrics').glob('*.json'))
    print(f"Uploading {len(files)} metrics...")
    
    for f in tqdm(files):
        try:
            data = json.loads(f.read_text())
            ticker = f.stem.upper()
            metric = data.get('metric', {})
            
            cursor.execute("""
                MERGE INTO METRICS t
                USING (SELECT %s as TICKER) s
                ON t.TICKER = s.TICKER
                WHEN MATCHED THEN UPDATE SET
                    HIGH_52W=%s, LOW_52W=%s,
                    BETA=%s,
                    REVENUE_GROWTH=%s
                WHEN NOT MATCHED THEN INSERT
                    (TICKER, HIGH_52W, LOW_52W,
                     BETA, REVENUE_GROWTH)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                ticker,
                metric.get('52WeekHigh'),
                metric.get('52WeekLow'),
                metric.get('beta'),
                metric.get('revenueGrowthTTMYoy'),
                ticker,
                metric.get('52WeekHigh'),
                metric.get('52WeekLow'),
                metric.get('beta'),
                metric.get('revenueGrowthTTMYoy')
            ))
        except Exception as e:
            pass
    conn.commit()
    print("Metrics done!")

def upload_recommendations(cursor, conn):
    files = list(
        (DATA_DIR / 'recommendations').glob(
            '*.json'))
    print(
        f"Uploading {len(files)} recommendations...")
    
    for f in tqdm(files):
        try:
            recs = json.loads(f.read_text())
            ticker = f.stem.upper()
            
            for rec in recs[:12]:
                period = rec.get('period', '')
                cursor.execute("""
                    MERGE INTO RECOMMENDATIONS t
                    USING (SELECT %s as TICKER,
                           %s as PERIOD) s
                    ON t.TICKER = s.TICKER
                    AND t.PERIOD = s.PERIOD
                    WHEN MATCHED THEN UPDATE SET
                        STRONG_BUY=%s, BUY=%s,
                        HOLD=%s, SELL=%s,
                        STRONG_SELL=%s
                    WHEN NOT MATCHED THEN INSERT
                        (TICKER, PERIOD,
                         STRONG_BUY, BUY,
                         HOLD, SELL, STRONG_SELL)
                    VALUES
                        (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    ticker, period,
                    rec.get('strongBuy', 0),
                    rec.get('buy', 0),
                    rec.get('hold', 0),
                    rec.get('sell', 0),
                    rec.get('strongSell', 0),
                    ticker, period,
                    rec.get('strongBuy', 0),
                    rec.get('buy', 0),
                    rec.get('hold', 0),
                    rec.get('sell', 0),
                    rec.get('strongSell', 0)
                ))
        except Exception as e:
            pass
    conn.commit()
    print("Recommendations done!")

def main():
    print("Connecting to Snowflake...")
    conn = connect()
    cursor = conn.cursor()
    print("Connected!")

    upload_fundamentals(cursor, conn)
    upload_news(cursor, conn)
    upload_metrics(cursor, conn)
    upload_recommendations(cursor, conn)

    cursor.close()
    conn.close()
    print("\nAll market data uploaded!")
    print("Verify:")
    print("SELECT COUNT(*) FROM FUNDAMENTALS;")
    print("SELECT COUNT(*) FROM NEWS;")
    print("SELECT COUNT(*) FROM METRICS;")
    print("SELECT COUNT(*) FROM RECOMMENDATIONS;")

if __name__ == '__main__':
    main()