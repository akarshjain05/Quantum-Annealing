"""
QUBO block decomposition for chunked QAOA execution.

Drop this in: backend/app/optimization/decomposition.py

WHY THIS IS EXACT, NOT APPROXIMATE:
docs/qubo-mathematics.md §3 documents that the base QUBO (no FX netting
groups, no global liquidity cap) is exactly block-diagonal across
corridors. This module generalizes that claim to the ACTUAL matrix
qubo.py produces today, which is only block-diagonal in the base case -
FX netting groups (§2.5 in qubo.py) and the global cap penalty (§4 in
qubo.py) both introduce real cross-block terms. Rather than assume
block-diagonality, this module *detects* the true coupling graph from the
Q matrix itself and decomposes along its connected components - which is
exact regardless of which terms happen to be active, because:

    x^T Q x = sum over components C of (x_C^T Q_C x_C)

whenever no nonzero Q entry crosses between two different components -
which is exactly the definition of "connected component" here. This is
verified directly (energy additivity + stitching round-trip) rather than
asserted - see the accompanying test file.

CRITICAL CAVEAT: when a global liquidity cap is active, EVERY variable is
coupled to every other (via the cap penalty's cross terms), so the
coupling graph collapses into a single component spanning the whole
matrix. In that case there is no valid decomposition - see
`has_valid_decomposition()` below. Callers must check this before
attempting to route a capped run through chunked QAOA.
"""
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class Chunk:
    block_indices: List[int]      # which one-hot blocks (corridor/slack indices) are in this chunk
    var_indices: np.ndarray       # global variable indices belonging to this chunk
    Q_sub: np.ndarray             # the exact submatrix for this chunk
    block_sizes: List[int]        # one-hot block sizes within this chunk, in order
    num_vars: int                 # = sum(block_sizes) = Q_sub.shape[0]


def find_independent_blocks(Q: np.ndarray, block_sizes: List[int], tol: float = 1e-12) -> List[List[int]]:
    """Connected components of the block-coupling graph. Two one-hot
    blocks are 'coupled' iff any off-diagonal entry between them is
    nonzero (within a block, off-diagonal entries always exist - that's
    the one-hot penalty - and don't count as cross-block coupling)."""
    n_blocks = len(block_sizes)
    offsets = np.cumsum([0] + list(block_sizes))
    adj = [[False] * n_blocks for _ in range(n_blocks)]
    for a in range(n_blocks):
        for b in range(a + 1, n_blocks):
            sub = Q[offsets[a]:offsets[a + 1], offsets[b]:offsets[b + 1]]
            if np.any(np.abs(sub) > tol):
                adj[a][b] = adj[b][a] = True

    visited = [False] * n_blocks
    components: List[List[int]] = []
    for start in range(n_blocks):
        if visited[start]:
            continue
        stack, comp = [start], []
        visited[start] = True
        while stack:
            node = stack.pop()
            comp.append(node)
            for nb in range(n_blocks):
                if adj[node][nb] and not visited[nb]:
                    visited[nb] = True
                    stack.append(nb)
        components.append(sorted(comp))
    return components


def build_chunks(Q: np.ndarray, block_sizes: List[int]) -> List[Chunk]:
    """Decompose Q into independent Chunks. Each Chunk's Q_sub captures
    every term that touches its variables - nothing is dropped or
    approximated, per the additivity property verified in
    test_decomposition.py."""
    offsets = np.cumsum([0] + list(block_sizes))
    components = find_independent_blocks(Q, block_sizes)
    chunks = []
    for comp in components:
        idx = []
        sub_sizes = []
        for b in comp:
            idx.extend(range(offsets[b], offsets[b + 1]))
            sub_sizes.append(block_sizes[b])
        idx = np.array(idx)
        Q_sub = Q[np.ix_(idx, idx)]
        chunks.append(Chunk(
            block_indices=comp, var_indices=idx, Q_sub=Q_sub,
            block_sizes=sub_sizes, num_vars=len(idx),
        ))
    return chunks


def has_valid_decomposition(chunks: List[Chunk], total_num_vars: int, max_single_chunk_frac: float = 0.6) -> bool:
    """Refuses a decomposition that isn't really a decomposition - e.g.
    when a global liquidity cap is active, coupling collapses everything
    into one chunk spanning most/all of the matrix. In that case chunked
    QAOA buys nothing (there's only one chunk = the whole problem) and
    the caller should fall back to classical SA entirely rather than
    silently running a single giant "chunk"."""
    if not chunks:
        return False
    largest = max(c.num_vars for c in chunks)
    return (largest / total_num_vars) <= max_single_chunk_frac


def stitch_solution(num_vars: int, chunk_results: List[Tuple[np.ndarray, np.ndarray]]) -> np.ndarray:
    """chunk_results: list of (var_indices, x_sub) pairs. Returns the full
    global x vector. This is an exact inverse of build_chunks' slicing -
    verified via round-trip test."""
    x_full = np.zeros(num_vars)
    for idx, x_sub in chunk_results:
        x_full[idx] = x_sub
    return x_full
