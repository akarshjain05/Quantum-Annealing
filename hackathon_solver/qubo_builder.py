def build_qubo(corridors, lot_size=10000, n_bits=7, n_slack_bits=None, budget=None):
    if n_slack_bits is None:
        n_slack_bits = n_bits

    Q = {}
    var_index = {}
    
    # We want to minimize \sum V_i + P * \sum (V_i - S_i - volume_i)^2
    # V_i = \sum 2^k x_k
    # S_i = \sum 2^k y_k
    
    P = 1000000.0 # Penalty weight
    
    idx = 0
    for c in corridors:
        v_idx = list(range(idx, idx + n_bits))
        idx += n_bits
        
        s_idx = list(range(idx, idx + n_slack_bits))
        idx += n_slack_bits
        
        var_index[c['name']] = v_idx
        
        vol = c['volume'] / lot_size  # scaled
        
        # Objective: minimize V_i. We add lot_size * V_i to the cost
        for k in range(n_bits):
            Q[(v_idx[k], v_idx[k])] = Q.get((v_idx[k], v_idx[k]), 0) + lot_size * (2**k) * 0.01
            
        # Penalty: P * (V_i - S_i - vol)^2
        # = P * (V_i^2 + S_i^2 + vol^2 - 2 V_i S_i - 2 vol V_i + 2 vol S_i)
        
        # V_i^2 = (\sum 2^k x_k)^2 = \sum 2^{2k} x_k + 2 \sum_{k<l} 2^{k+l} x_k x_l
        for k in range(n_bits):
            # linear term from V_i^2
            Q[(v_idx[k], v_idx[k])] = Q.get((v_idx[k], v_idx[k]), 0) + P * (2**(2*k))
            # linear term from -2 vol V_i
            Q[(v_idx[k], v_idx[k])] = Q.get((v_idx[k], v_idx[k]), 0) - P * 2 * vol * (2**k)
            for l in range(k + 1, n_bits):
                Q[(v_idx[k], v_idx[l])] = Q.get((v_idx[k], v_idx[l]), 0) + P * 2 * (2**(k+l))
                
        # S_i^2
        for k in range(n_slack_bits):
            Q[(s_idx[k], s_idx[k])] = Q.get((s_idx[k], s_idx[k]), 0) + P * (2**(2*k))
            # linear term from 2 vol S_i
            Q[(s_idx[k], s_idx[k])] = Q.get((s_idx[k], s_idx[k]), 0) + P * 2 * vol * (2**k)
            for l in range(k + 1, n_slack_bits):
                Q[(s_idx[k], s_idx[l])] = Q.get((s_idx[k], s_idx[l]), 0) + P * 2 * (2**(k+l))
                
        # -2 V_i S_i
        for k in range(n_bits):
            for l in range(n_slack_bits):
                Q[(v_idx[k], s_idx[l])] = Q.get((v_idx[k], s_idx[l]), 0) - P * 2 * (2**(k+l))
                
    return Q, var_index

def decode_solution(bits, var_index, corridors, lot_size, n_bits):
    funded = {}
    for c in corridors:
        v_idx = var_index[c['name']]
        v = sum(bits[v_idx[k]] * (2**k) for k in range(n_bits))
        funded[c['name']] = v * lot_size
    return funded
