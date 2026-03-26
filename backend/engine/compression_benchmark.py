import asyncio
import numpy as np
from typing import List, Optional, Tuple, Dict
from ..models.contracts import CompressionMethodResult, CompressionSummary, ConnectionSummary
from ..models.runtime import RunContext

COST_PER_GB_MONTH = 0.095  # USD


def quantize_int8(vectors: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Scalar quantize to int8."""
    min_vals = vectors.min(axis=0)
    max_vals = vectors.max(axis=0)
    scale = (max_vals - min_vals) / 255.0
    scale = np.where(scale == 0, 1.0, scale)
    quantized = np.clip(np.round((vectors - min_vals) / scale), 0, 255).astype(np.uint8)
    return quantized, min_vals, scale


def dequantize_int8(quantized: np.ndarray, min_vals: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return quantized.astype(np.float32) * scale + min_vals


def quantize_int4(vectors: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    min_vals = vectors.min(axis=0)
    max_vals = vectors.max(axis=0)
    scale = (max_vals - min_vals) / 15.0
    scale = np.where(scale == 0, 1.0, scale)
    quantized = np.clip(np.round((vectors - min_vals) / scale), 0, 15).astype(np.uint8)
    return quantized, min_vals, scale


def dequantize_int4(quantized: np.ndarray, min_vals: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return quantized.astype(np.float32) * scale + min_vals


def random_rotation_matrix(dims: int) -> np.ndarray:
    """Random orthogonal rotation matrix via QR decomposition."""
    A = np.random.randn(dims, dims).astype(np.float32)
    Q, _ = np.linalg.qr(A)
    return Q


def compute_recall_at_k(query_vecs: np.ndarray, db_vecs: np.ndarray,
                         approx_db: np.ndarray, k: int = 10) -> float:
    """Compute approximate recall@k against exact nearest neighbors."""
    n_queries = min(len(query_vecs), 100)
    query_vecs = query_vecs[:n_queries]

    recalls = []
    for q in query_vecs:
        # Exact neighbors from original
        exact_scores = db_vecs @ q
        exact_top = set(np.argsort(exact_scores)[-k:].tolist())

        # Approx neighbors from quantized
        approx_scores = approx_db @ q
        approx_top = set(np.argsort(approx_scores)[-k:].tolist())

        recall = len(exact_top & approx_top) / k
        recalls.append(recall)

    return float(np.mean(recalls)) if recalls else 0.0


async def run_compression_benchmark(ctx: RunContext, run_manager, es_service=None):
    """Run compression benchmark in background."""
    summary = ctx.summary

    if not summary.vectorField or not summary.vectorDims:
        ctx.compression = CompressionSummary(
            available=False,
            status='skipped',
        )
        await run_manager.publish(ctx.run_id, {
            "type": "compression.updated",
            "payload": ctx.compression.model_dump()
        })
        return

    ctx.compression = CompressionSummary(
        available=True,
        vectorField=summary.vectorField,
        vectorDims=summary.vectorDims,
        status='running',
        methods=[
            CompressionMethodResult(method='float32', sizeBytes=0, recallAt10=1.0,
                                    estimatedMonthlyCostUsd=0, sizeReductionPct=0, status='running'),
            CompressionMethodResult(method='int8', sizeBytes=0, recallAt10=0,
                                    estimatedMonthlyCostUsd=0, sizeReductionPct=0, status='pending'),
            CompressionMethodResult(method='int4', sizeBytes=0, recallAt10=0,
                                    estimatedMonthlyCostUsd=0, sizeReductionPct=0, status='pending'),
            CompressionMethodResult(method='rotated_int4', sizeBytes=0, recallAt10=0,
                                    estimatedMonthlyCostUsd=0, sizeReductionPct=0, status='pending'),
        ]
    )

    await run_manager.publish(ctx.run_id, {
        "type": "compression.updated",
        "payload": ctx.compression.model_dump()
    })

    dims = summary.vectorDims
    doc_count = min(summary.docCount, 2000)

    try:
        if ctx.mode == 'demo':
            # Use synthetic vectors for demo
            rng = np.random.RandomState(42)
            db_vecs = rng.randn(doc_count, dims).astype(np.float32)
            # Normalize
            norms = np.linalg.norm(db_vecs, axis=1, keepdims=True)
            db_vecs = db_vecs / np.where(norms == 0, 1, norms)

            query_vecs = rng.randn(min(100, doc_count // 10), dims).astype(np.float32)
            query_norms = np.linalg.norm(query_vecs, axis=1, keepdims=True)
            query_vecs = query_vecs / np.where(query_norms == 0, 1, query_norms)
        else:
            # For live mode, try to fetch vectors from ES
            # This is optional - if not available, skip
            ctx.compression.status = 'skipped'
            ctx.compression.available = False
            await run_manager.publish(ctx.run_id, {
                "type": "compression.updated",
                "payload": ctx.compression.model_dump()
            })
            return

        # float32 baseline
        float32_bytes = doc_count * dims * 4
        float32_cost = (float32_bytes / 1e9) * COST_PER_GB_MONTH

        ctx.compression.methods[0] = CompressionMethodResult(
            method='float32',
            sizeBytes=float32_bytes,
            recallAt10=1.0,
            estimatedMonthlyCostUsd=round(float32_cost, 2),
            sizeReductionPct=0.0,
            status='done',
        )
        await _publish_compression(ctx, run_manager)
        await asyncio.sleep(0.3)

        # int8
        ctx.compression.methods[1].status = 'running'
        await _publish_compression(ctx, run_manager)

        q8, min8, scale8 = quantize_int8(db_vecs)
        deq8 = dequantize_int8(q8, min8, scale8)
        recall8 = compute_recall_at_k(query_vecs, db_vecs, deq8, k=10)
        int8_bytes = doc_count * dims * 1
        int8_cost = (int8_bytes / 1e9) * COST_PER_GB_MONTH

        ctx.compression.methods[1] = CompressionMethodResult(
            method='int8',
            sizeBytes=int8_bytes,
            recallAt10=round(recall8, 4),
            estimatedMonthlyCostUsd=round(int8_cost, 2),
            sizeReductionPct=round((1 - int8_bytes / float32_bytes) * 100, 1),
            status='done',
        )
        await _publish_compression(ctx, run_manager)
        await asyncio.sleep(0.3)

        # int4
        ctx.compression.methods[2].status = 'running'
        await _publish_compression(ctx, run_manager)

        q4, min4, scale4 = quantize_int4(db_vecs)
        deq4 = dequantize_int4(q4, min4, scale4)
        recall4 = compute_recall_at_k(query_vecs, db_vecs, deq4, k=10)
        int4_bytes = doc_count * dims // 2
        int4_cost = (int4_bytes / 1e9) * COST_PER_GB_MONTH

        ctx.compression.methods[2] = CompressionMethodResult(
            method='int4',
            sizeBytes=int4_bytes,
            recallAt10=round(recall4, 4),
            estimatedMonthlyCostUsd=round(int4_cost, 2),
            sizeReductionPct=round((1 - int4_bytes / float32_bytes) * 100, 1),
            status='done',
        )
        await _publish_compression(ctx, run_manager)
        await asyncio.sleep(0.3)

        # rotated_int4
        ctx.compression.methods[3].status = 'running'
        await _publish_compression(ctx, run_manager)

        rotation = random_rotation_matrix(dims)
        rotated = (db_vecs @ rotation.T)
        q4r, min4r, scale4r = quantize_int4(rotated)
        deq4r = dequantize_int4(q4r, min4r, scale4r)

        # For recall, reconstruct and unrotate
        deq4r_unrotated = deq4r @ rotation
        recall4r = compute_recall_at_k(query_vecs, db_vecs, deq4r_unrotated, k=10)
        rot4_bytes = int4_bytes  # same storage
        rot4_cost = (rot4_bytes / 1e9) * COST_PER_GB_MONTH

        ctx.compression.methods[3] = CompressionMethodResult(
            method='rotated_int4',
            sizeBytes=rot4_bytes,
            recallAt10=round(recall4r, 4),
            estimatedMonthlyCostUsd=round(rot4_cost, 2),
            sizeReductionPct=round((1 - rot4_bytes / float32_bytes) * 100, 1),
            status='done',
            note="Random orthogonal rotation applied before quantization",
        )

        # Best recommendation
        # Find method with recall > 0.97 and highest savings
        good_methods = [m for m in ctx.compression.methods[1:] if m.recallAt10 >= 0.97]
        if good_methods:
            best = max(good_methods, key=lambda m: m.sizeReductionPct)
            ctx.compression.bestRecommendation = best.method
            ctx.compression.projectedMonthlySavingsUsd = round(
                float32_cost - best.estimatedMonthlyCostUsd, 2
            )

        ctx.compression.status = 'done'
        ctx.metrics.projectedMonthlySavingsUsd = ctx.compression.projectedMonthlySavingsUsd

        await _publish_compression(ctx, run_manager)

    except asyncio.CancelledError:
        return
    except Exception as e:
        ctx.compression.status = 'error'
        await _publish_compression(ctx, run_manager)


async def _publish_compression(ctx: RunContext, run_manager):
    await run_manager.publish(ctx.run_id, {
        "type": "compression.updated",
        "payload": ctx.compression.model_dump()
    })
