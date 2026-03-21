"""
Document Chunker for AlphaQuery - CORRECTED VERSION
Uses BGE's native BERT tokenizer for accurate token counting

CRITICAL: Must use same tokenizer as embedding model!
"""

import json
from pathlib import Path
from typing import List, Dict
import logging
from scipy import stats
from tqdm import tqdm
import argparse
from transformers import AutoTokenizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/chunking.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CHUNKING CONFIGURATION
MODEL_NAME = 'BAAI/bge-m3'
MODEL_MAX_LENGTH = 8192
CHUNK_SIZE = 512
OVERLAP = 64
HEADROOM = 256

# Validation
assert CHUNK_SIZE + HEADROOM <= MODEL_MAX_LENGTH, "Insufficient headroom!"


class DocumentChunker:
    """
    Chunks documents using BGE's native tokenizer
    """
    
    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        # CRITICAL: Use BGE's actual tokenizer!
        logger.info(f"Loading tokenizer for {MODEL_NAME}...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        
        logger.info(f"Tokenizer loaded: {self.tokenizer.__class__.__name__}")
        logger.info(f"Vocab size: {self.tokenizer.vocab_size}")
        logger.info(f"Model max length: {self.tokenizer.model_max_length}")
        logger.info(f"Chunk size: {chunk_size} tokens")
        logger.info(f"Overlap: {overlap} tokens")
        logger.info(f"Headroom: {HEADROOM} tokens")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using BGE's tokenizer"""
        return len(self.tokenizer.encode(text, add_special_tokens=True))
    
    def chunk_text(self, text: str, section_name: str = None) -> List[Dict]:
        """
        Chunk text into fixed-size segments using BGE tokenizer
        
        Args:
            text: Text to chunk
            section_name: Optional section name for metadata
            
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []
        
        # Tokenize with BGE's tokenizer
        # add_special_tokens=False for chunking (we'll add them during embedding)
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        
        if len(tokens) == 0:
            return []
        
        chunks = []
        start_idx = 0
        chunk_num = 0
        
        while start_idx < len(tokens):
            # Extract chunk (400 tokens max)
            end_idx = min(start_idx + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)
            
            # Get actual token count (with special tokens for validation)
            actual_tokens = len(self.tokenizer.encode(chunk_text, add_special_tokens=True))
            
            # Validation: ensure we're under limit
            if actual_tokens > self.chunk_size + 20:  # Allow small buffer for special tokens
                logger.warning(f"Chunk exceeded size: {actual_tokens} > {self.chunk_size}")
            
            # Validate headroom
            if actual_tokens > MODEL_MAX_LENGTH - 50:  # 50 token safety margin
                logger.error(f"CRITICAL: Chunk too large! {actual_tokens} tokens (limit: {MODEL_MAX_LENGTH})")
            
            # Create chunk metadata
            chunk = {
                'text': chunk_text.strip(),
                'token_count': actual_tokens,
                'chunk_index': chunk_num,
                'section': section_name or 'unknown',
                'start_token': start_idx,
                'end_token': end_idx
            }
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start_idx += (self.chunk_size - self.overlap)
            chunk_num += 1
        
        return chunks
    
    def chunk_document(self, doc_path: Path) -> Dict:
        """
        Chunk a single parsed document
        
        Args:
            doc_path: Path to parsed JSON file
            
        Returns:
            Dictionary with chunked document and metadata
        """
        try:
            # Load parsed document
            with open(doc_path, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            
            # Extract metadata
            ticker = doc.get('ticker', 'UNKNOWN')
            form_type = doc.get('form_type', 'UNKNOWN')
            filing_date = doc.get('filing_date', 'UNKNOWN')
            sections = doc.get('sections', {})
            
            # Chunk each section
            all_chunks = []
            
            for section_name, section_text in sections.items():
                if not section_text or not section_text.strip():
                    continue
                
                # Chunk this section
                section_chunks = self.chunk_text(section_text, section_name)
                
                # Add document metadata to each chunk
                for chunk in section_chunks:
                    chunk['ticker'] = ticker
                    chunk['form_type'] = form_type
                    chunk['filing_date'] = filing_date
                    chunk['source_file'] = str(doc_path)
                    
                    # Create unique chunk ID
                    chunk_id = f"{ticker}_{form_type}_{filing_date}_sec{section_name}_chunk{chunk['chunk_index']:04d}"
                    chunk['chunk_id'] = chunk_id
                
                all_chunks.extend(section_chunks)
            
            return {
                'ticker': ticker,
                'form_type': form_type,
                'filing_date': filing_date,
                'total_chunks': len(all_chunks),
                'chunks': all_chunks
            }
            
        except Exception as e:
            logger.error(f"Error chunking {doc_path.name}: {e}")
            return None
    
    def save_chunks(self, chunked_doc: Dict, output_dir: Path):
        """Save chunked document to JSON"""
        if not chunked_doc:
            return
        
        ticker = chunked_doc['ticker']
        form_type = chunked_doc['form_type']
        filing_date = chunked_doc['filing_date']
        
        filename = f"{ticker}_{form_type}_{filing_date}_chunks.json"
        output_path = output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunked_doc, f, indent=2, ensure_ascii=False)
        
        return output_path


def chunk_all_documents(
    input_dir: str = 'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/text',
    output_dir: str = 'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/chunks',
    max_files: int = None
):
    """
    Chunk all parsed documents with BGE tokenizer
    """
    # Setup
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all parsed files
    json_files = list(input_path.glob('*.json'))
    
    if max_files:
        json_files = json_files[:max_files]
    
    total_files = len(json_files)
    
    logger.info(f"\n{'#'*60}")
    logger.info(f"DOCUMENT CHUNKING - BGE Tokenizer")
    logger.info(f"{'#'*60}")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Input: {input_dir}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Files to process: {total_files}")
    logger.info(f"Chunk size: {CHUNK_SIZE} tokens")
    logger.info(f"Overlap: {OVERLAP} tokens")
    logger.info(f"Headroom: {HEADROOM} tokens")
    logger.info(f"{'#'*60}\n")
    
    # Initialize chunker
    chunker = DocumentChunker(chunk_size=CHUNK_SIZE, overlap=OVERLAP)
    
    # Statistics
    stats = {
        'total_files': total_files,
        'processed': 0,
        'failed': 0,
        'total_chunks': 0,
        'total_tokens': 0,
        'max_chunk_size': 0,
        'chunks_by_form': {}
    }
    
    # Process files
    for json_file in tqdm(json_files, desc="Chunking documents"):
        try:
            # Chunk document
            chunked = chunker.chunk_document(json_file)
            
            if chunked:
                # Save chunks
                chunker.save_chunks(chunked, output_path)
                
                # Update stats
                stats['processed'] += 1
                stats['total_chunks'] += chunked['total_chunks']
                
                # Track by form type
                form = chunked['form_type']
                if form not in stats['chunks_by_form']:
                    stats['chunks_by_form'][form] = 0
                stats['chunks_by_form'][form] += chunked['total_chunks']
                
                # Track max chunk size
                for chunk in chunked['chunks']:
                    stats['total_tokens'] += chunk['token_count']
                    stats['max_chunk_size'] = max(
                        stats['max_chunk_size'],
                        chunk['token_count']
                    )
            else:
                stats['failed'] += 1
                
        except Exception as e:
            logger.error(f"Failed to process {json_file.name}: {e}")
            stats['failed'] += 1
    
    # Final report
    logger.info(f"\n{'#'*60}")
    logger.info(f"CHUNKING COMPLETE!")
    logger.info(f"{'#'*60}")
    logger.info(f"Files processed: {stats['processed']}")
    logger.info(f"Files failed: {stats['failed']}")
    logger.info(f"Total chunks created: {stats['total_chunks']:,}")
    logger.info(f"Total tokens: {stats['total_tokens']:,}")
    processed = stats['processed'] or 1
    logger.info(f"Average chunks/file: {stats['total_chunks']//processed:,}")
    total_chunks = stats['total_chunks'] or 1
    logger.info(f"Average tokens/chunk: {stats['total_tokens']//total_chunks:.0f}")
    logger.info(f"Max chunk size: {stats['max_chunk_size']} tokens")
    logger.info(f"\nChunks by form type:")
    for form, count in sorted(stats['chunks_by_form'].items()):
        logger.info(f"  {form}: {count:,} chunks")
    logger.info(f"{'#'*60}\n")
    
    # Validation checks
    if stats['max_chunk_size'] > CHUNK_SIZE + 20:  # Allow for special tokens
        logger.warning(f"⚠️  WARNING: Some chunks exceeded {CHUNK_SIZE} tokens!")
    else:
        logger.info(f"✓ All chunks within {CHUNK_SIZE} token limit")
    
    headroom_actual = MODEL_MAX_LENGTH - stats['max_chunk_size']
    if headroom_actual < 50:
        logger.error(f"❌ CRITICAL: Insufficient headroom! Only {headroom_actual} tokens")
    else:
        logger.info(f"✓ Safe headroom: {headroom_actual} tokens minimum")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Chunk parsed SEC documents with BGE tokenizer')
    parser.add_argument(
        '--input', 
        default='D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/text', 
        help='Input directory')
    parser.add_argument(
        '--output', 
        default='D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/chunks', 
        help='Output directory')
    parser.add_argument(
        '--test', 
        action='store_true', 
        help='Test with 10 files')
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("TEST MODE: Processing 10 files only")
        chunk_all_documents(
            input_dir=args.input,
            output_dir=args.output,
            max_files=10
        )
    else:
        chunk_all_documents(
            input_dir=args.input,
            output_dir=args.output
        )
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("TEST MODE: Processing 10 files only")
        chunk_all_documents(
            input_dir=args.input,
            output_dir=args.output,
            max_files=10
        )
    else:
        chunk_all_documents(
            input_dir=args.input,
            output_dir=args.output
        )


if __name__ == '__main__':
    main()