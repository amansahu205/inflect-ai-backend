"""
S&P 500 Company List Scraper - Direct Table Extraction
Scrapes the S&P 500 table directly from Wikipedia HTML
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

def scrape_sp500_table():
    """
    Scrape S&P 500 companies directly from Wikipedia table
    
    Returns:
        DataFrame with columns: ticker, name, sector, cik
    """
    
    print("Scraping S&P 500 table from Wikipedia...")
    
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    # Add User-Agent to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # Fetch the page
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the S&P 500 constituents table (it has id='constituents')
        table = soup.find('table', {'id': 'constituents'})
        
        if not table:
            print("✗ Could not find constituents table")
            return None
        
        # Extract table rows
        rows = table.find_all('tr')[1:]  # Skip header row
        
        companies = []
        
        for row in rows:
            cols = row.find_all('td')
            
            if len(cols) >= 8:  # Make sure row has all columns
                ticker = cols[0].text.strip()
                name = cols[1].text.strip()
                sector = cols[2].text.strip()
                cik = cols[6].text.strip()  # CIK is 7th column (index 6)
                
                companies.append({
                    'ticker': ticker,
                    'name': name,
                    'sector': sector,
                    'cik': cik.zfill(10)  # Pad CIK to 10 digits
                })
        
        # Convert to DataFrame
        df = pd.DataFrame(companies)
        
        print(f"✓ Scraped {len(df)} companies successfully!")
        
        print(f"\nSample companies:")
        print(df.head(10))
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Network error: {e}")
        return None
    except Exception as e:
        print(f"✗ Error scraping table: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_company_list(df, output_dir='data-pipeline'):
    """Save company list to CSV and JSON"""
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Save as CSV
    csv_path = f"{output_dir}/sp500_companies.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n✓ Saved {len(df)} companies to {csv_path}")
    
    # Save as JSON (easier to read programmatically)
    json_path = f"{output_dir}/sp500_companies.json"
    df.to_json(json_path, orient='records', indent=2)
    print(f"✓ Saved to {json_path}")
    
    # Print some stats
    print(f"\nSector breakdown:")
    sector_counts = df['sector'].value_counts()
    for sector, count in sector_counts.head(10).items():
        print(f"  {sector:30} {count:3}")
    
    # Show some example CIKs to verify padding
    print(f"\nSample CIK numbers (should be 10 digits):")
    for _, row in df.head(5).iterrows():
        print(f"  {row['ticker']:6} → CIK: {row['cik']}")
    
    return csv_path, json_path


if __name__ == "__main__":
    print("=" * 60)
    print("S&P 500 Company List Scraper")
    print("=" * 60)
    print()
    
    # Scrape the data
    companies = scrape_sp500_table()
    
    if companies is not None and len(companies) > 0:
        # Save to files
        csv_file, json_file = save_company_list(companies)
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS!")
        print("=" * 60)
        print(f"\nYou now have {len(companies)} S&P 500 companies with CIK numbers.")
        print(f"\nFiles created:")
        print(f"  - {csv_file}")
        print(f"  - {json_file}")
        print("\nNext step: Run SEC scraper to download filings!")
        
    else:
        print("\n✗ Scraping failed. Creating fallback list with 10 major companies...")
        
        # Fallback: Create starter list
        starter_data = {
            'ticker': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'JPM', 'V', 'WMT'],
            'name': [
                'Apple Inc.', 'Microsoft Corporation', 'Alphabet Inc.', 
                'Amazon.com Inc.', 'NVIDIA Corporation', 'Tesla Inc.',
                'Meta Platforms Inc.', 'JPMorgan Chase & Co.', 'Visa Inc.', 'Walmart Inc.'
            ],
            'sector': [
                'Information Technology', 'Information Technology', 'Communication Services',
                'Consumer Discretionary', 'Information Technology', 'Consumer Discretionary',
                'Communication Services', 'Financials', 'Financials', 'Consumer Staples'
            ],
            'cik': [
                '0000320193', '0000789019', '0001652044', '0001018724', '0001045810',
                '0001318605', '0001326801', '0000019617', '0001403161', '0000104169'
            ]
        }
        
        starter_df = pd.DataFrame(starter_data)
        csv_file, json_file = save_company_list(starter_df)
        
        print("\n✓ Created starter list with 10 companies")
        print("   This is enough to test your pipeline!")