"""
Advanced SEC Filing Parser - AlphaQuery
Preserves table structure, section hierarchy, and financial data integrity

Features:
- Markdown table conversion (preserves financial data)
- SEC Item/section detection (10-K, 10-Q structure)
- Header hierarchy preservation
- List formatting (Markdown)
- Smart text cleaning
"""

import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup, Tag, NavigableString
from typing import Dict, List, Optional, Tuple
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/parser.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AdvancedSECParser:
    """
    Advanced parser for SEC filings with structure preservation
    """
    
    # SEC form sections (10-K, 10-Q)
    SEC_ITEMS = {
        '10-K': [
            'Item 1.', 'Item 1A.', 'Item 1B.', 'Item 1C.',
            'Item 2.', 'Item 3.', 'Item 4.',
            'Item 5.', 'Item 6.', 'Item 7.', 'Item 7A.', 'Item 8.', 'Item 9.', 'Item 9A.', 'Item 9B.', 'Item 9C.',
            'Item 10.', 'Item 11.', 'Item 12.', 'Item 13.', 'Item 14.', 'Item 15.', 'Item 16.'
        ],
        '10-Q': [
            'Part I', 'Part II',
            'Item 1.', 'Item 2.', 'Item 3.', 'Item 4.'
        ]
    }
    
    def __init__(self, output_dir: str = "data/processed/text"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def table_to_markdown(self, table: Tag) -> str:
        """
        Convert HTML table to Markdown format
        
        Preserves financial data structure for better LLM understanding
        """
        rows = table.find_all('tr')
        
        if not rows:
            return ""
        
        markdown_rows = []
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            
            # Extract cell text and clean
            cell_texts = []
            for cell in cells:
                text = cell.get_text(strip=True)
                # Clean up common financial formatting
                text = text.replace('\n', ' ').replace('\r', '')
                text = re.sub(r'\s+', ' ', text)
                cell_texts.append(text)
            
            # Create Markdown row
            markdown_row = '| ' + ' | '.join(cell_texts) + ' |'
            markdown_rows.append(markdown_row)
        
        if not markdown_rows:
            return ""
        
        # Add separator after header row (if exists)
        if len(markdown_rows) > 1:
            # Count columns from first row
            num_cols = markdown_rows[0].count('|') - 1
            separator = '|' + '---|' * num_cols
            markdown_rows.insert(1, separator)
        
        return '\n'.join(markdown_rows)
    
    def list_to_markdown(self, list_tag: Tag) -> str:
        """Convert HTML list to Markdown format"""
        items = list_tag.find_all('li', recursive=False)
        
        if not items:
            return ""
        
        is_ordered = list_tag.name == 'ol'
        markdown_lines = []
        
        for i, item in enumerate(items, 1):
            text = item.get_text(strip=True)
            text = re.sub(r'\s+', ' ', text)
            
            if is_ordered:
                markdown_lines.append(f"{i}. {text}")
            else:
                markdown_lines.append(f"- {text}")
        
        return '\n'.join(markdown_lines)
    
    def extract_with_structure(self, soup: BeautifulSoup) -> str:
        """
        Extract text while preserving structure
        
        Converts:
        - Tables → Markdown tables
        - Lists → Markdown lists
        - Headers → Markdown headers
        """
        # Remove unwanted elements
        for element in soup(['script', 'style', 'meta', 'link']):
            element.decompose()
        
        output = []
        
        # Process elements in order
        for element in soup.find_all(['p', 'table', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']):
            
            # Skip if already processed (nested in parent)
            if element.find_parent(['table', 'ul', 'ol']):
                continue
            
            if element.name == 'table':
                # Convert table to Markdown
                markdown_table = self.table_to_markdown(element)
                if markdown_table:
                    output.append('\n' + markdown_table + '\n')
            
            elif element.name in ['ul', 'ol']:
                # Convert list to Markdown
                markdown_list = self.list_to_markdown(element)
                if markdown_list:
                    output.append('\n' + markdown_list + '\n')
            
            elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Convert header to Markdown
                level = int(element.name[1])
                text = element.get_text(strip=True)
                if text:
                    output.append('\n' + '#' * level + ' ' + text + '\n')
            
            elif element.name in ['p', 'div']:
                # Regular paragraph
                text = element.get_text(strip=True)
                if text:
                    output.append(text + '\n')
        
        return '\n'.join(output)
    
    def detect_sections(self, text: str, form_type: str) -> Dict[str, str]:
        """
        Detect SEC Item sections in document
        
        Returns dict of {section_name: section_text}
        """
        sections = {}
        
        if form_type not in self.SEC_ITEMS:
            # No section detection for this form type
            sections['full_document'] = text
            return sections
        
        # Build regex pattern for all items
        items = self.SEC_ITEMS[form_type]
        
        # Find all section headers
        section_positions = []
        
        for item in items:
            # Case-insensitive search for item headers
            pattern = re.escape(item).replace(r'\.', r'\.?\s*')
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                section_positions.append({
                    'item': item,
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Sort by position
        section_positions.sort(key=lambda x: x['start'])
        
        if not section_positions:
            # No sections detected, return full text
            sections['full_document'] = text
            return sections
        
        # Extract text for each section
        for i, section in enumerate(section_positions):
            item_name = section['item']
            start = section['end']
            
            # End is start of next section (or end of document)
            if i < len(section_positions) - 1:
                end = section_positions[i + 1]['start']
            else:
                end = len(text)
            
            section_text = text[start:end].strip()
            
            if section_text:
                sections[item_name] = section_text
        
        # If no sections extracted, use full document
        if not sections:
            sections['full_document'] = text
        
        return sections
    
    def clean_text(self, text: str) -> str:
        """Advanced text cleaning"""
        # Remove excessive whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove excessive newlines (more than 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove page numbers
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove "Table of Contents" noise
        text = re.sub(r'Table of Contents', '', text, flags=re.IGNORECASE)
        
        # Remove excessive dashes/underscores (decorative elements)
        text = re.sub(r'[-_]{10,}', '', text)
        
        # Normalize Unicode characters
        text = text.replace('\xa0', ' ')  # Non-breaking space
        text = text.replace('\u200b', '')  # Zero-width space
        
        return text.strip()
    
    def parse_html_file(self, filepath: Path) -> Optional[Dict]:
        """
        Parse single SEC filing with advanced structure preservation
        """
        try:
            # Read HTML
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Extract structured text
            structured_text = self.extract_with_structure(soup)
            
            # Clean text
            cleaned_text = self.clean_text(structured_text)
            
            # Parse filename for metadata
            filename = filepath.stem
            parts = filename.split('_')
            
            if len(parts) >= 3:
                ticker = parts[0]
                form_type = parts[1]
                filing_date = parts[2]
            else:
                ticker = "UNKNOWN"
                form_type = "UNKNOWN"
                filing_date = "UNKNOWN"
            
            # Detect sections (Item 1, Item 7, etc.)
            sections = self.detect_sections(cleaned_text, form_type)
            
            result = {
                'ticker': ticker,
                'form_type': form_type,
                'filing_date': filing_date,
                'source_file': str(filepath),
                'sections': sections,
                'word_count': len(cleaned_text.split()),
                'char_count': len(cleaned_text),
                'num_sections': len(sections)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"[FAIL] Error parsing {filepath.name}: {e}")
            return None
    
    def save_parsed_document(self, parsed_doc: Dict) -> Path:
        """Save parsed document to JSON"""
        filename = f"{parsed_doc['ticker']}_{parsed_doc['form_type']}_{parsed_doc['filing_date']}.json"
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_doc, f, indent=2, ensure_ascii=False)
        
        return output_path


def parse_file_worker(filepath: Path) -> Optional[Dict]:
    """Worker function for parallel processing"""
    parser = AdvancedSECParser()
    result = parser.parse_html_file(filepath)
    
    if result:
        parser.save_parsed_document(result)
        return {
            'status': 'success',
            'file': filepath.name,
            'words': result['word_count'],
            'sections': result['num_sections']
        }
    else:
        return {'status': 'failed', 'file': filepath.name}


def parse_all_filings(input_dirs: List[str] = ['data/raw/10-K', 'data/raw/10-Q', 'data/raw/8-K'],
                     workers: int = 4):
    """Parse all SEC filings in parallel with advanced structure preservation"""
    
    # Collect all files
    all_files = []
    for input_dir in input_dirs:
        path = Path(input_dir)
        if path.exists():
            all_files.extend(list(path.glob('*.html')))
    
    total_files = len(all_files)
    logger.info(f"\n{'#'*60}")
    logger.info(f"ADVANCED SEC PARSER - Structure Preservation Mode")
    logger.info(f"{'#'*60}")
    logger.info(f"Total files: {total_files}")
    logger.info(f"Workers: {workers}")
    logger.info(f"Output: data/processed/text/")
    logger.info(f"\nFeatures:")
    logger.info(f"  ✓ Markdown table conversion")
    logger.info(f"  ✓ SEC Item/section detection")
    logger.info(f"  ✓ List formatting")
    logger.info(f"  ✓ Header hierarchy")
    logger.info(f"{'#'*60}\n")
    
    # Statistics
    stats = {
        'total': total_files,
        'success': 0,
        'failed': 0,
        'total_words': 0,
        'total_sections': 0
    }
    
    # Process in parallel with progress bar
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(parse_file_worker, f): f for f in all_files}
        
        with tqdm(total=total_files, desc="Parsing SEC filings") as pbar:
            for future in as_completed(futures):
                result = future.result()
                
                if result and result['status'] == 'success':
                    stats['success'] += 1
                    stats['total_words'] += result.get('words', 0)
                    stats['total_sections'] += result.get('sections', 0)
                else:
                    stats['failed'] += 1
                
                pbar.update(1)
                pbar.set_postfix({
                    'success': stats['success'],
                    'failed': stats['failed']
                })
    
    # Final summary
    logger.info(f"\n{'#'*60}")
    logger.info(f"PARSING COMPLETE!")
    logger.info(f"{'#'*60}")
    logger.info(f"Total files: {stats['total']}")
    logger.info(f"Successfully parsed: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Success rate: {(stats['success']/stats['total'])*100:.1f}%")
    logger.info(f"\nExtracted content:")
    logger.info(f"  Total words: {stats['total_words']:,}")
    logger.info(f"  Average words/document: {stats['total_words']//stats['success']:,}")
    logger.info(f"  Total sections detected: {stats['total_sections']:,}")
    logger.info(f"  Average sections/document: {stats['total_sections']/stats['success']:.1f}")
    logger.info(f"{'#'*60}\n")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Advanced SEC filing parser with structure preservation')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--test', action='store_true', help='Test with 10 files only')
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("TEST MODE: Processing 10 files from each category")
        
        # Get 10 files from each type
        test_files = []
        for form_dir in ['data/raw/10-K', 'data/raw/10-Q', 'data/raw/8-K']:
            files = list(Path(form_dir).glob('*.html'))[:10]
            test_files.extend(files)
        
        logger.info(f"Testing with {len(test_files)} files total")
        
        for file in test_files:
            result = parse_file_worker(file)
            if result and result['status'] == 'success':
                logger.info(f"[OK] {result['file']} - {result['words']} words, {result['sections']} sections")
            else:
                logger.error(f"[FAIL] {file.name}")
    else:
        # Full processing
        parse_all_filings(workers=args.workers)


if __name__ == '__main__':
    main()