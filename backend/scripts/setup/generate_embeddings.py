"""
GPU-Accelerated Embedding Generation — LOCAL SAVE
Saves embeddings to JSONL file instead of Pinecone.
Team can decide on vector DB tomorrow.
"""

import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import logging
import os
import time
import torch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/embeddings.log',
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
MODEL_NAME      = 'BAAI/bge-m3'
BATCH_SIZE      = 64
JSONL_FILE      = 'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/all_chunks.jsonl'
CHECKPOINT_FILE = 'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/embedding_checkpoint.txt'
OUTPUT_FILE     = 'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/sec_filings/processed/embeddings_1024.jsonl'


class GPUEmbeddingPipeline:
    """
    GPU-accelerated embedding generation.
    Saves embeddings locally to JSONL file.
    Upload to Pinecone / pgvector / FAISS later.
    """

    def __init__(self):
        logger.info("Initializing local embedding pipeline...")

        # ── GPU check ────────────────────────────────────────────────────────
        if torch.cuda.is_available():
            device = 'cuda'
            gpu_name   = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"✓ GPU detected: {gpu_name}")
            logger.info(f"✓ GPU memory:   {gpu_memory:.1f} GB")
        else:
            device = 'cpu'
            logger.warning("⚠️  No GPU detected — using CPU (will be slower)")

        # ── Load model ───────────────────────────────────────────────────────
        logger.info(f"Loading model: {MODEL_NAME} on {device}...")
        self.model = SentenceTransformer(MODEL_NAME, device=device)
        dims = self.model.get_sentence_embedding_dimension()
        logger.info(f"✓ Model loaded on {device}")
        logger.info(f"✓ Embedding dimension: {dims}")
        assert dims == 1024, f"Expected 1024 dims, got {dims}"

        # ── Open output file (append mode — safe to resume) ──────────────────
        self.output_file = open(OUTPUT_FILE, 'a', encoding='utf-8')
        logger.info(f"✓ Output file: {OUTPUT_FILE}")

        # ── Resume from checkpoint ───────────────────────────────────────────
        self.start_line = self._get_checkpoint()
        if self.start_line > 0:
            logger.info(f"Resuming from line: {self.start_line:,}")

    # ── Checkpoint helpers ────────────────────────────────────────────────────

    def _get_checkpoint(self) -> int:
        if Path(CHECKPOINT_FILE).exists():
            try:
                val = Path(CHECKPOINT_FILE).read_text().strip()
                return int(val) if val else 0
            except Exception:
                return 0
        return 0

    def _save_checkpoint(self, line_num: int):
        Path(CHECKPOINT_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(CHECKPOINT_FILE).write_text(str(line_num))

    # ── Count lines ───────────────────────────────────────────────────────────

    def count_total_lines(self) -> int:
        logger.info("Counting total chunks...")
        with open(JSONL_FILE, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def process_and_save(self):
        total_lines = self.count_total_lines()
        remaining   = total_lines - self.start_line

        logger.info(f"\n{'='*70}")
        logger.info(f"GPU-ACCELERATED EMBEDDING PIPELINE — LOCAL SAVE")
        logger.info(f"{'='*70}")
        logger.info(f"Model:        {MODEL_NAME}")
        logger.info(f"Device:       {self.model.device}")
        logger.info(f"Input:        {JSONL_FILE}")
        logger.info(f"Output:       {OUTPUT_FILE}")
        logger.info(f"Total chunks: {total_lines:,}")
        logger.info(f"Starting from:{self.start_line:,}")
        logger.info(f"Remaining:    {remaining:,}")
        logger.info(f"Batch size:   {BATCH_SIZE}")
        logger.info(f"{'='*70}\n")

        if remaining == 0:
            logger.info("✓ All chunks already processed!")
            self.output_file.close()
            return

        stats = {
            'processed':   0,
            'saved':       0,
            'errors':      0,
            'start_time':  time.time(),
            'batch_times': []
        }

        batch_texts  = []
        batch_chunks = []
        current_line = 0

        with open(JSONL_FILE, 'r', encoding='utf-8') as f:
            pbar = tqdm(
                total=total_lines,
                initial=self.start_line,
                desc="Embedding",
                unit="chunks",
                smoothing=0.1
            )

            for line in f:
                current_line += 1

                # Skip already processed lines
                if current_line <= self.start_line:
                    continue

                try:
                    chunk = json.loads(line)
                    batch_texts.append(chunk['text'])
                    batch_chunks.append(chunk)

                    if len(batch_texts) >= BATCH_SIZE:
                        batch_start = time.time()
                        self._process_batch(batch_texts, batch_chunks, stats)
                        batch_time = time.time() - batch_start
                        stats['batch_times'].append(batch_time)

                        # Speed display
                        recent = stats['batch_times'][-10:]
                        avg_speed = BATCH_SIZE / (sum(recent) / len(recent))
                        pbar.set_postfix({
                            'speed': f'{avg_speed:.0f} chunks/s',
                            'saved': f"{stats['saved']:,}"
                        })

                        self._save_checkpoint(current_line)
                        batch_texts  = []
                        batch_chunks = []

                    pbar.update(1)

                except Exception as e:
                    logger.error(f"Error at line {current_line}: {e}")
                    stats['errors'] += 1

            # Final partial batch
            if batch_texts:
                self._process_batch(batch_texts, batch_chunks, stats)
                self._save_checkpoint(current_line)

            pbar.close()

        # Close output file
        self.output_file.close()

        # Final report
        elapsed = time.time() - stats['start_time']
        logger.info(f"\n{'='*70}")
        logger.info(f"PIPELINE COMPLETE!")
        logger.info(f"{'='*70}")
        logger.info(f"Chunks processed: {stats['processed']:,}")
        logger.info(f"Embeddings saved: {stats['saved']:,}")
        logger.info(f"Errors:           {stats['errors']:,}")
        logger.info(f"Time elapsed:     {elapsed/60:.1f} min ({elapsed/3600:.2f} hrs)")
        logger.info(f"Average speed:    {stats['processed']/elapsed:.1f} chunks/sec")
        logger.info(f"Output file:      {OUTPUT_FILE}")

        # File size
        size_gb = Path(OUTPUT_FILE).stat().st_size / (1024**3)
        logger.info(f"Output size:      {size_gb:.2f} GB")
        logger.info(f"{'='*70}\n")

        logger.info("Tomorrow's options:")
        logger.info("  A) Upload embeddings_1024.jsonl → Pinecone (inflect-prod-v2)")
        logger.info("  B) Upload embeddings_1024.jsonl → Supabase pgvector")
        logger.info("  C) Build FAISS index locally from embeddings_1024.jsonl")

    # ── Batch processor ───────────────────────────────────────────────────────

    def _process_batch(self, texts, chunks, stats):
        """Generate embeddings on GPU and save to local JSONL"""
        try:
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32,
                convert_to_numpy=True
            )

            for chunk, embedding in zip(chunks, embeddings):
                record = {
                    'chunk_id':   chunk.get('chunk_id', ''),
                    'ticker':     chunk.get('ticker', ''),
                    'form_type':  chunk.get('form_type', ''),
                    'filing_date':chunk.get('filing_date', ''),
                    'section':    chunk.get('section', ''),
                    'token_count':chunk.get('token_count', 0),
                    'text':       chunk.get('text', '')[:1000],
                    'embedding':  embedding.tolist()   # 1024 floats
                }
                self.output_file.write(
                    json.dumps(record, ensure_ascii=False) + '\n'
                )

            self.output_file.flush()
            stats['processed'] += len(texts)
            stats['saved']     += len(texts)

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            stats['errors'] += len(texts)
            raise


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if torch.cuda.is_available():
        logger.info(f"\n{'='*70}")
        logger.info(f"GPU ACCELERATION ENABLED!")
        logger.info(f"10-50x faster than CPU!")
        logger.info(f"{'='*70}\n")

    pipeline = GPUEmbeddingPipeline()
    pipeline.process_and_save()


if __name__ == '__main__':
    main()