"""
SEC Edgar Scraper - AlphaQuery Data Pipeline
Downloads 10-K, 10-Q, and 8-K filings from SEC EDGAR

PRD Reference: F-001 (Document Ingestion Pipeline)
"""

import os
import time
import json
import requests
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Configure logging WITHOUT emoji (Windows compatibility)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SECEdgarScraper:
    """
    Scraper for SEC EDGAR filings with rate limiting and error handling.
    """
    
    BASE_URL = "https://data.sec.gov"
    EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
    RATE_LIMIT_DELAY = 0.11  # 110ms = ~9 req/sec (safe under 10 req/sec limit)
    
    def __init__(self, user_agent: str, output_dir: str = "data/raw"):
        """
        Initialize scraper
        
        Args:
            user_agent: Required by SEC (format: "Name email@example.com")
            output_dir: Where to save downloaded filings
        """
        self.user_agent = user_agent
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'application/json'
        })
        
        # Create output directories
        for form_type in ['10-K', '10-Q', '8-K']:
            (self.output_dir / form_type).mkdir(parents=True, exist_ok=True)
        
        # Progress tracking
        self.download_index_path = Path('data/download_index.json')
        self.download_index = self._load_download_index()
    
    def _load_download_index(self) -> Dict:
        """Load existing download index or create new one"""
        if self.download_index_path.exists():
            with open(self.download_index_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_download_index(self):
        """Save download index"""
        with open(self.download_index_path, 'w') as f:
            json.dump(self.download_index, f, indent=2)
    
    def _is_already_downloaded(self, ticker: str, form_type: str, filing_date: str) -> bool:
        """Check if filing already downloaded"""
        if ticker not in self.download_index:
            return False
        if form_type not in self.download_index[ticker]:
            return False
        return filing_date in self.download_index[ticker][form_type]
    
    def _mark_as_downloaded(self, ticker: str, form_type: str, filing_date: str):
        """Mark filing as downloaded"""
        if ticker not in self.download_index:
            self.download_index[ticker] = {}
        if form_type not in self.download_index[ticker]:
            self.download_index[ticker][form_type] = []
        
        if filing_date not in self.download_index[ticker][form_type]:
            self.download_index[ticker][form_type].append(filing_date)
        
        self._save_download_index()
    
    def get_company_filings(self, cik: str, ticker: str) -> Optional[Dict]:
        """
        Fetch company filings metadata from SEC
        
        Args:
            cik: Company CIK (must be exactly 10 digits)
            ticker: Stock ticker
            
        Returns:
            Dictionary with filing information or None if failed
        """
        # CRITICAL FIX: Ensure CIK is exactly 10 digits with leading zeros
        cik_padded = str(cik).zfill(10)
        
        url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"
        
        try:
            time.sleep(self.RATE_LIMIT_DELAY)  # Rate limiting
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"[OK] Fetched filings for {ticker} (CIK: {cik_padded})")
            return data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"[FAIL] HTTP error for {ticker} (CIK: {cik_padded}): {e}")
            return None
        except Exception as e:
            logger.error(f"[FAIL] Error fetching {ticker}: {e}")
            return None
    
    def download_filing(self, cik: str, ticker: str, accession_number: str, 
                       primary_document: str, form_type: str, filing_date: str) -> bool:
        """
        Download a single filing
        
        Args:
            cik: Company CIK
            ticker: Stock ticker
            accession_number: SEC accession number
            primary_document: Primary document filename
            form_type: Form type (10-K, 10-Q, 8-K)
            filing_date: Filing date (YYYY-MM-DD)
            
        Returns:
            True if successful, False otherwise
        """
        # Check if already downloaded
        if self._is_already_downloaded(ticker, form_type, filing_date):
            logger.info(f"[SKIP] {ticker} {form_type} {filing_date} (already downloaded)")
            return True
        
        # Ensure CIK is properly formatted (strip leading zeros for URL path)
        cik_numeric = str(int(cik))  # Remove leading zeros for file path
        
        # Construct URL
        accession_no_clean = accession_number.replace('-', '')
        doc_url = f"{self.EDGAR_ARCHIVES}/{cik_numeric}/{accession_no_clean}/{primary_document}"
        
        try:
            time.sleep(self.RATE_LIMIT_DELAY)  # Rate limiting
            response = self.session.get(doc_url)
            response.raise_for_status()
            
            # Save file
            filename = f"{ticker}_{form_type}_{filing_date}.html"
            filepath = self.output_dir / form_type / filename
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Mark as downloaded
            self._mark_as_downloaded(ticker, form_type, filing_date)
            
            size_kb = len(response.content) / 1024
            logger.info(f"[OK] Downloaded {ticker} {form_type} {filing_date} ({size_kb:.1f} KB)")
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"[FAIL] HTTP error downloading {ticker} {form_type}: {e}")
            return False
        except Exception as e:
            logger.error(f"[FAIL] Error downloading {ticker} {form_type}: {e}")
            return False
    
    def scrape_company(self, cik: str, ticker: str, forms: List[str] = ['10-K', '10-Q'], 
                      max_filings_per_type: int = 5) -> Dict:
        """
        Scrape all filings for a single company
        
        Args:
            cik: Company CIK
            ticker: Stock ticker
            forms: List of form types to download
            max_filings_per_type: Max number of each form type to download
            
        Returns:
            Statistics dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping {ticker} (CIK: {str(cik).zfill(10)})")
        logger.info(f"{'='*60}")
        
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        # Get company filings
        data = self.get_company_filings(cik, ticker)
        if not data:
            stats['failed'] += 1
            return stats
        
        # Extract recent filings
        recent_filings = data['filings']['recent']
        
        # Process each form type
        for form_type in forms:
            count = 0
            for i in range(len(recent_filings['form'])):
                if recent_filings['form'][i] == form_type:
                    if count >= max_filings_per_type:
                        break
                    
                    filing_date = recent_filings['filingDate'][i]
                    accession_number = recent_filings['accessionNumber'][i]
                    primary_document = recent_filings['primaryDocument'][i]
                    
                    # Download
                    success = self.download_filing(
                        cik, ticker, accession_number, primary_document,
                        form_type, filing_date
                    )
                    
                    if success:
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
                    
                    count += 1
        
        return stats
    
    def scrape_all(self, companies_file: str = 'data-pipeline/sp500_companies.csv',
                   forms: List[str] = ['10-K', '10-Q'],
                   max_filings_per_type: int = 5,
                   max_companies: Optional[int] = None):
        """
        Scrape filings for all companies in CSV
        
        Args:
            companies_file: Path to CSV with company list
            forms: List of form types to download
            max_filings_per_type: Max filings per type per company
            max_companies: Limit number of companies (for testing)
        """
        # Load companies - CRITICAL: Keep CIK as string to preserve leading zeros
        df = pd.read_csv(companies_file, dtype={'cik': str})
        
        if max_companies:
            df = df.head(max_companies)
        
        total_companies = len(df)
        logger.info(f"\n{'#'*60}")
        logger.info(f"Starting SEC filing download for {total_companies} companies")
        logger.info(f"Forms: {forms}")
        logger.info(f"Max per type: {max_filings_per_type}")
        logger.info(f"{'#'*60}\n")
        
        overall_stats = {'success': 0, 'failed': 0, 'skipped': 0, 'companies_processed': 0}
        start_time = time.time()
        
        # Process each company
        for idx, row in df.iterrows():
            ticker = row['ticker']
            cik = row['cik']
            
            try:
                stats = self.scrape_company(cik, ticker, forms, max_filings_per_type)
                overall_stats['success'] += stats['success']
                overall_stats['failed'] += stats['failed']
                overall_stats['skipped'] += stats['skipped']
                overall_stats['companies_processed'] += 1
                
                # Progress update (every 10 companies)
                if (idx + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = (idx + 1) / elapsed
                    eta = (total_companies - (idx + 1)) / rate if rate > 0 else 0
                    
                    logger.info(f"\n[PROGRESS] {idx+1}/{total_companies} companies")
                    logger.info(f"   Success: {overall_stats['success']} | Failed: {overall_stats['failed']} | Skipped: {overall_stats['skipped']}")
                    logger.info(f"   ETA: {eta/60:.1f} minutes\n")
            
            except Exception as e:
                logger.error(f"[FAIL] Unexpected error processing {ticker}: {e}")
                overall_stats['failed'] += 1
        
        # Final summary
        elapsed = time.time() - start_time
        logger.info(f"\n{'#'*60}")
        logger.info(f"SCRAPING COMPLETE!")
        logger.info(f"{'#'*60}")
        logger.info(f"Companies processed: {overall_stats['companies_processed']}")
        logger.info(f"Filings downloaded: {overall_stats['success']}")
        logger.info(f"Filings skipped: {overall_stats['skipped']}")
        logger.info(f"Failures: {overall_stats['failed']}")
        logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
        logger.info(f"Average: {elapsed/total_companies:.1f} seconds per company")
        logger.info(f"{'#'*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Download SEC filings for S&P 500 companies')
    parser.add_argument('--companies', type=int, help='Number of companies to scrape (for testing)')
    parser.add_argument('--all', action='store_true', help='Scrape all companies')
    parser.add_argument('--forms', nargs='+', default=['10-K', '10-Q'], help='Form types to download')
    parser.add_argument('--max-per-type', type=int, default=5, help='Max filings per type')
    
    args = parser.parse_args()
    
    # User agent (REQUIRED by SEC)
    USER_AGENT = "Aman Kumar Sahu aman.sahu205@gmail.com"
    
    # Initialize scraper
    scraper = SECEdgarScraper(user_agent=USER_AGENT)
    
    # Determine number of companies
    max_companies = None
    if args.companies:
        max_companies = args.companies
    elif not args.all:
        # Default: scrape 10 companies for testing
        max_companies = 10
        logger.info("No --companies or --all specified. Defaulting to 10 companies for testing.")
        logger.info("Use --all to scrape all 503 companies.")
    
    # Run scraper
    scraper.scrape_all(
        forms=args.forms,
        max_filings_per_type=args.max_per_type,
        max_companies=max_companies
    )


if __name__ == "__main__":
    main()