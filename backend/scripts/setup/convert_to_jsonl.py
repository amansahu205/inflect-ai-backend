"""
Convert chunked JSON files to single JSONL file for efficient streaming
"""

import json
from pathlib import Path
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_to_jsonl(
    input_dir: str = 'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/chunks',
    output_file: str = 'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/all_chunks.jsonl'
):
    """
    Convert all JSON chunk files to single JSONL file
    """
    input_path = Path(input_dir)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    json_files = list(input_path.glob('*.json'))
    
    logger.info(f"Converting {len(json_files)} JSON files to JSONL...")
    
    total_chunks = 0
    
    with open(output_path, 'w', encoding='utf-8') as out:
        for json_file in tqdm(json_files, desc="Converting"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Write each chunk as one line
                for chunk in data['chunks']:
                    out.write(json.dumps(chunk, ensure_ascii=False) + '\n')
                    total_chunks += 1
                    
            except Exception as e:
                logger.error(f"Error processing {json_file.name}: {e}")
    
    logger.info(f"\n{'#'*60}")
    logger.info(f"Conversion complete!")
    logger.info(f"{'#'*60}")
    logger.info(f"Input files: {len(json_files)}")
    logger.info(f"Output file: {output_path}")
    logger.info(f"Total chunks: {total_chunks:,}")
    
    # Check output size
    size_gb = output_path.stat().st_size / (1024**3)
    logger.info(f"File size: {size_gb:.2f} GB")
    logger.info(f"{'#'*60}")
    
    return total_chunks

if __name__ == '__main__':
    convert_to_jsonl()