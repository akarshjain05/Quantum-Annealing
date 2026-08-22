import numpy as np

def find_independent_blocks(Q, block_sizes):
    """Connected components of the block-coupling graph. Two blocks are
    'coupled' iff any off-diagonal entry between them is nonzero."""
    n_blocks = len(block_sizes)
    offsets = np.cumsum([0] + list(block_sizes))
    adj = [[False] * n_blocks for _ in range(n_blocks)]
    for a in range(n_blocks):
        for b in range(a + 1, n_blocks):
            sub = Q[offsets[a]:offsets[a+1], offsets[b]:offsets[b+1]]
            if np.any(np.abs(sub) > 1e-12):
                adj[a][b] = adj[b][a] = True
    visited = [False] * n_blocks
    components = []
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


def extract_submatrix(Q, block_sizes, block_group):
    offsets = np.cumsum([0] + list(block_sizes))
    idx = []
    sub_block_sizes = []
    for b in block_group:
        idx.extend(range(offsets[b], offsets[b+1]))
        sub_block_sizes.append(block_sizes[b])
    idx = np.array(idx)
    Q_sub = Q[np.ix_(idx, idx)]
    return Q_sub, idx, sub_block_sizes


def stitch_solution(num_vars, chunk_solutions):
    x_full = np.zeros(num_vars)
    for idx, x_sub in chunk_solutions:
        x_full[idx] = x_sub
    return x_full


# ---------------------------------------------------------------------
# TEST 1: base case (mirrors current seed data - one netted pair, rest independent)
# 4 corridor blocks of size 8: blocks 0,1 coupled (like USD_EUR/EUR_USD netting),
# blocks 2,3 fully independent.
# ---------------------------------------------------------------------
rng = np.random.default_rng(7)
block_sizes = [8, 8, 8, 8]
n = sum(block_sizes)
Q = np.zeros((n, n))
offsets = np.cumsum([0] + block_sizes)

for i in range(4):
    a, b = offsets[i], offsets[i+1]
    B = rng.normal(size=(8, 8))
    Bs = (B + B.T) / 2
    Q[a:b, a:b] = Bs

cross = rng.normal(size=(8, 8))
Q[offsets[0]:offsets[1], offsets[1]:offsets[2]] = cross
Q[offsets[1]:offsets[2], offsets[0]:offsets[1]] = cross.T

components = find_independent_blocks(Q, block_sizes)
assert sorted(components) == [[0, 1], [2], [3]], f"unexpected components: {components}"
print(f"TEST 1 (netted pair + 2 independent): components = {components}  [PASS: matches expected grouping]")

# Energy additivity + stitching round-trip, 500 random trials
max_err = 0.0
for _ in range(500):
    x = rng.integers(0, 2, size=n).astype(float)
    full_e = float(x @ Q @ x)
    total = 0.0
    chunk_solutions = []
    for comp in components:
        Q_sub, idx, _ = extract_submatrix(Q, block_sizes, comp)
        x_sub = x[idx]
        total += float(x_sub @ Q_sub @ x_sub)
        chunk_solutions.append((idx, x_sub))
    max_err = max(max_err, abs(full_e - total))
    x_stitched = stitch_solution(n, chunk_solutions)
    assert np.allclose(x_stitched, x), "stitching did not reproduce original x"

print(f"TEST 1 energy additivity over 500 random trials: max |full_E - sum(chunk_E)| = {max_err:.2e}  [PASS]")

# ---------------------------------------------------------------------
# TEST 2: global cap active -> every block coupled to a slack block ->
# must collapse to ONE component spanning everything (no valid decomposition)
# ---------------------------------------------------------------------
block_sizes2 = [8, 8, 8, 8, 32]  # 4 corridors + slack block (like the cap penalty case)
n2 = sum(block_sizes2)
Q2 = np.zeros((n2, n2))
offsets2 = np.cumsum([0] + block_sizes2)
for i in range(5):
    a, b = offsets2[i], offsets2[i+1]
    sz = block_sizes2[i]
    B = rng.normal(size=(sz, sz))
    Q2[a:b, a:b] = (B + B.T) / 2
# cap penalty couples EVERY pair of variables globally -> couple every block to every other
for i in range(5):
    for j in range(i+1, 5):
        ai, bi = offsets2[i], offsets2[i+1]
        aj, bj = offsets2[j], offsets2[j+1]
        cross2 = rng.normal(size=(block_sizes2[i], block_sizes2[j])) * 0.001 + 0.0001  # nonzero, however small
        Q2[ai:bi, aj:bj] = cross2
        Q2[aj:bj, ai:bi] = cross2.T

components2 = find_independent_blocks(Q2, block_sizes2)
assert len(components2) == 1 and components2[0] == [0, 1, 2, 3, 4], f"expected single fused component, got {components2}"
print(f"TEST 2 (global cap active): components = {components2}  [PASS: correctly collapses to one block -> no decomposition possible, must fall back to classical]")

print("\nAll decomposition + stitching invariants verified.")
