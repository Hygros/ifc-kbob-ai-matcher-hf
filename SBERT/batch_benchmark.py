import os
import time

import torch
from sentence_transformers import SentenceTransformer


def parse_benchmark_batch_sizes(raw: str | None = None) -> list[int]:
    source = raw if raw is not None else os.environ.get("SBERT_BENCH_BATCH_SIZES", "16,32,64,128,256")
    sizes: list[int] = []
    for part in source.split(","):
        token = part.strip()
        if token.isdigit() and int(token) > 0:
            sizes.append(int(token))
    deduped = sorted(set(sizes))
    return deduped if deduped else [16, 32, 64, 128, 256]


def recommend_batch_size(
    queries: list[str],
    device: str,
    model: SentenceTransformer,
    normalize_embeddings: bool,
    default_batch_size: int,
    verbose: bool = True,
    candidate_sizes: list[int] | None = None,
    sample_limit: int | None = None,
) -> int:
    if not queries:
        if verbose:
            print("Batch benchmark skipped: no IFC queries found. Using default batch size.")
        return default_batch_size

    if candidate_sizes is None:
        candidate_sizes = parse_benchmark_batch_sizes()
    if not candidate_sizes:
        return default_batch_size

    if sample_limit is None:
        sample_limit = int(os.environ.get("SBERT_BENCH_SAMPLE_LIMIT", "1500"))
    benchmark_texts = queries[:sample_limit] if sample_limit > 0 else queries

    results: list[tuple[int, float, float, str]] = []

    if verbose:
        print(f"Batch benchmark on {device} with {len(benchmark_texts)} sample queries")

    for batch_size in candidate_sizes:
        try:
            if device == "cuda":
                torch.cuda.empty_cache()

            with torch.inference_mode():
                start = time.perf_counter()
                _ = model.encode(
                    benchmark_texts,
                    batch_size=batch_size,
                    convert_to_tensor=True,
                    normalize_embeddings=normalize_embeddings,
                    show_progress_bar=False,
                )
                if device == "cuda":
                    torch.cuda.synchronize()
                elapsed = max(time.perf_counter() - start, 1e-9)

            throughput = len(benchmark_texts) / elapsed
            results.append((batch_size, elapsed, throughput, "ok"))
            if verbose:
                print(f"  batch={batch_size:>4} | {elapsed:>7.3f}s | {throughput:>9.1f} q/s")
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                results.append((batch_size, float("inf"), 0.0, "oom"))
                if verbose:
                    print(f"  batch={batch_size:>4} | OOM")
                if device == "cuda":
                    torch.cuda.empty_cache()
                continue
            raise

    viable = [row for row in results if row[3] == "ok"]
    if not viable:
        if verbose:
            print("No viable batch size found in benchmark. Falling back to default.")
        return default_batch_size

    best_batch_size = max(viable, key=lambda row: row[2])[0]
    if verbose:
        print(f"Recommended SBERT_BATCH_SIZE={best_batch_size}")
    return best_batch_size
