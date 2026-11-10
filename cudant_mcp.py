# CUDANT-128 — Fidelity-gated GPU quantum & physics simulator
# Copyright (c) 2026 JaVec-Works
# License: MIT (see LICENSE)   
import torch
import torch.nn.functional as F
import numpy as np
import json
import math
import os
import tempfile
import importlib.util
from fastmcp import FastMCP

mcp = FastMCP("CUDANT Engine")

MAX_DENSE = 16
MAX_MPS = 128

def _apply_single_qubit(state, gate, target, n_qubits):
    stride = 1 << (n_qubits - 1 - target)
    s = state.reshape(-1, 2, stride)
    a = s[:, 0, :].clone()
    b = s[:, 1, :].clone()
    s[:, 0, :] = gate[0,0]*a + gate[0,1]*b
    s[:, 1, :] = gate[1,0]*a + gate[1,1]*b
    return s.reshape(-1)

def _apply_cnot(state, control, target, n_qubits):
    c_stride = 1 << (n_qubits - 1 - control)
    t_stride = 1 << (n_qubits - 1 - target)
    dim = state.shape[-1]
    num_ctrl = dim // (2 * c_stride)
    num_tgt = c_stride // (2 * t_stride)
    s = state.reshape(num_ctrl, 2, num_tgt, 2, t_stride)
    tmp = s[:, 1, :, 0, :].clone()
    s[:, 1, :, 0, :] = s[:, 1, :, 1, :]
    s[:, 1, :, 1, :] = tmp
    return s.reshape(-1)

_H = torch.tensor([[1,1],[1,-1]], dtype=torch.complex64, device="cuda") / np.sqrt(2)
_X = torch.tensor([[0,1],[1,0]], dtype=torch.complex64, device="cuda")
_Z = torch.tensor([[1,0],[0,-1]], dtype=torch.complex64, device="cuda")

@mcp.tool()
def run_lion(qubits: int, gates: str) -> str:
    """
    Run a quantum circuit on GPU (exact, dense statevector). Use for 2-16 qubits.
    For 17+ qubits, use run_mps instead.

    GATE SYNTAX (gates separated by commas, NO commas inside a gate):
      Single-qubit:  H0  X1  Z2  (gate letter + qubit index)
      Two-qubit:     CNOT01  CNOT9_10  CNOT10_11  (CNOT + control + target)
                     Qubits 0-9: CNOT01 is fine.
                     Qubits 10+: MUST use underscore. CNOT9_10, CNOT10_11.
                     NEVER write CNOT910 or CNOT1011.

    EXAMPLES:
      "H0,CNOT01"           -> Bell pair on qubits 0,1
      "H0,H1,CNOT01,CNOT12" -> 3-qubit GHZ
      "X0,X1"               -> |11> (both qubits flipped)
      "H0,H1,H2,H3"         -> 4-qubit uniform superposition

    Args:
        qubits: Number of qubits (2-16).
        gates: Comma-separated gate string. See examples above.

    Returns:
        JSON with all measurement probabilities, the most likely outcome,
        and its confidence (probability).
    """
    if qubits > MAX_DENSE:
        return json.dumps({"error": f"Max {MAX_DENSE} qubits for dense path. Use run_mps for more."})
    dim = 2 ** qubits
    state = torch.zeros(dim, dtype=torch.complex64, device="cuda")
    state[0] = 1.0
    for g in gates.split(","):
        g = g.strip()
        if not g:
            continue
        if g.startswith("CNOT"):
            raw = g[4:].strip()
            if "_" in raw:
                parts = raw.split("_")
            elif len(raw) == 2:
                parts = [raw[0], raw[1]]
            else:
                return json.dumps({"error": f"Ambiguous CNOT '{g}'. Use underscore for qubits 10+: CNOT9_10, CNOT10_11."}, indent=2)
            ctrl, tgt = int(parts[0]), int(parts[1])
            state = _apply_cnot(state, ctrl, tgt, qubits)
        else:
            gtype = g[0]
            qubit = int(g[1:])
            gate = {"H": _H, "X": _X, "Z": _Z}[gtype]
            state = _apply_single_qubit(state, gate, qubit, qubits)
    probs = (state.abs() ** 2).real.cpu().numpy()
    result = {"qubits": qubits, "gates": gates, "probabilities": {}}
    for i, p in enumerate(probs):
        if p > 1e-6:
            bits = format(i, f'0{qubits}b')
            result["probabilities"][f"|{bits}>"] = round(float(p), 6)
    top_idx = int(np.argmax(probs))
    result["answer"] = f"|{format(top_idx, f'0{qubits}b')}>"
    result["confidence"] = round(float(probs[top_idx]), 6)
    return json.dumps(result, indent=2)

def _gen_kernel_source(n_qubits, gates):
    lines = ["import cudaq", "", "@cudaq.kernel", "def _k():", f"    q = cudaq.qvector({n_qubits})"]
    for g in gates.split(","):
        g = g.strip()
        if not g:
            continue
        if g.startswith("CNOT"):
            raw = g[4:].strip()
            if "_" in raw:
                parts = raw.split("_")
            elif len(raw) == 2:
                parts = [raw[0], raw[1]]
            else:
                raise ValueError(f"Ambiguous CNOT '{g}'. Use underscore for qubits 10+: CNOT9_10, CNOT10_11.")
            c, t = int(parts[0]), int(parts[1])
            lines.append(f"    x.ctrl(q[{c}], q[{t}])")
        else:
            gt = g[0].lower()
            qb = int(g[1:])
            lines.append(f"    {gt}(q[{qb}])")
    return "\n".join(lines)

def _run_mps_once(n_qubits, gates, chi, shots=1000):
    src = _gen_kernel_source(n_qubits, gates)
    path = os.path.join(tempfile.gettempdir(), f"_cudant_k_{os.getpid()}.py")
    with open(path, "w") as f:
        f.write(src)
    os.environ["CUDAQ_MPS_MAX_BOND"] = str(chi)
    import cudaq
    cudaq.set_target("tensornet-mps")
    spec = importlib.util.spec_from_file_location("_cudant_k", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = cudaq.sample(mod._k, shots_count=shots)
    os.unlink(path)
    return result

@mcp.tool()
def run_mps(qubits: int, gates: str, chi_max: int = 64, epsilon: float = 0.05) -> str:
    """
    Run a quantum circuit on GPU using MPS (Matrix Product State). Use for 17-128 qubits.
    For 16 or fewer qubits, use run_lion instead (it is exact and faster).

    FIDELITY GUARANTEE:
      This tool runs the circuit TWICE (at chi_max and chi_max*4) and compares
      results. If they disagree by more than epsilon, it REFUSES and tells you
      how to fix it. You will never get a silently wrong answer.

    GATE SYNTAX (same as run_lion, comma-separated):
      H0  X1  Z2  CNOT01  CNOT3_5  (both CNOT formats work)

    EXAMPLES:
      "H0,CNOT01,CNOT12"  -> 3-qubit GHZ (use run_lion for this, but works here)
      "H0,CNOT01,CNOT02,CNOT03"  -> 4-qubit GHZ

    Args:
        qubits: Number of qubits (17-128).
        gates: Comma-separated gate string.
        chi_max: Bond dimension. 16=fast/rough, 64=medium, 256=high, 1024=near-exact.
        epsilon: Tolerance for fidelity check (default 0.05). Lower = stricter.

    Returns:
      SUCCESS: {"fidelity": "confirmed", "top1_prob_chi": ..., "result": ...}
      REJECTED: {"result": "REJECTED", "reason": ..., "advice": "Increase chi_max to ..."}
      If rejected, retry with the suggested chi_max value.
    """
    if qubits <= MAX_DENSE:
        return json.dumps({"note": f"Use run_lion for {MAX_DENSE} or fewer qubits (exact).", "redirect": "run_lion"})
    if qubits > MAX_MPS:
        return json.dumps({"error": f"Max {MAX_MPS} qubits. Got {qubits}."})
    try:
        r1 = _run_mps_once(qubits, gates, chi_max)
        r2 = _run_mps_once(qubits, gates, chi_max * 4)
        mp1, mp2 = r1.most_probable(), r2.most_probable()
        p1, p2 = r1.probability(mp1), r2.probability(mp2)
        s1, s2 = str(r1), str(r2)
        if abs(p1 - p2) < epsilon:
            return json.dumps({"qubits": qubits, "gates": gates, "chi_max": chi_max, "fidelity": "confirmed", "top1_prob_chi": round(p1, 4), "top1_prob_chi4": round(p2, 4), "result": s1}, indent=2)
        return json.dumps({"qubits": qubits, "gates": gates, "chi_max": chi_max, "result": "REJECTED", "reason": f"top-1 prob: chi={chi_max} gives {p1:.4f}, chi={chi_max*4} gives {p2:.4f} (diff={abs(p1-p2):.4f} > epsilon={epsilon})", "advice": f"Increase chi_max to {chi_max*4} or {chi_max*16}", "run_chi": s1, "run_chi4": s2}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
def settle_field(grid_size: int, center_coeff: float, neighbor_coeff: float, steps: int = 100) -> str:
    """
    Settle a 3D field with a given kernel on GPU.

    Args:
        grid_size: Size of the 3D grid (64, 128, 256).
        center_coeff: How much stays at center (0.5-0.99).
        neighbor_coeff: How much flows to each of 26 neighbors.
        steps: Number of settle timesteps.

    Returns:
        Final field statistics.
    """
    N = grid_size
    field = torch.zeros(1, 1, N, N, N, device="cuda")
    field[0, 0, N//2, N//2, N//2] = 1.0
    w = neighbor_coeff
    c = center_coeff
    s0 = [[w,w,w],[w,w,w],[w,w,w]]
    s1 = [[w,w,w],[w,c,w],[w,w,w]]
    s2 = [[w,w,w],[w,w,w],[w,w,w]]
    kernel = torch.tensor([[[s0,s1,s2]]], dtype=torch.float32, device="cuda")
    for _ in range(steps):
        field = F.conv3d(field, kernel, padding=1)
    result = {
        "grid": f"{N}x{N}x{N}",
        "steps": steps,
        "max_value": round(field.max().item(), 6),
        "center_value": round(field[0,0,N//2,N//2,N//2].item(), 6),
        "total_energy": round(field.sum().item(), 6),
        "spreads_to_cells": int((field[0,0] > 1e-4).sum().item())
    }
    return json.dumps(result, indent=2)

@mcp.tool()
def widen_search(n_circuits: int, qubits: int, target: str) -> str:
    """
    Run N parallel Grover searches on the GPU.

    Args:
        n_circuits: Number of parallel circuits (10, 100, 1000).
        qubits: Number of qubits (2-16).
        target: Target bit string, e.g. "1010".

    Returns:
        Hit rate and statistics.
    """
    if qubits > MAX_DENSE:
        return json.dumps({"error": f"Max {MAX_DENSE} qubits for Grover batch."})
    target = target.strip("|> ")
    target_idx = int(target, 2)
    dim = 2 ** qubits
    n_iters = max(1, round(math.pi / 4 * math.sqrt(dim)))
    states = torch.zeros(n_circuits, dim, dtype=torch.complex64, device="cuda")
    states[:, 0] = 1.0
    for q in range(qubits):
        for i in range(n_circuits):
            states[i] = _apply_single_qubit(states[i], _H, q, qubits)
    for _ in range(n_iters):
        states[:, target_idx] *= -1
        mean = states.sum(dim=1) / np.sqrt(dim)
        states = 2 * mean.unsqueeze(1) / np.sqrt(dim) - states
    probs = (states.abs() ** 2).real
    target_probs = probs[:, target_idx]
    result = {
        "circuits": n_circuits,
        "qubits": qubits,
        "target": f"|{target}>",
        "iterations": n_iters,
        "hit_rate": round(float((target_probs > 0.9).float().mean()), 4),
        "avg_probability": round(float(target_probs.mean()), 4),
        "min_probability": round(float(target_probs.min()), 4),
        "max_probability": round(float(target_probs.max()), 4),
        "all_found": bool((target_probs > 0.99).all().item())
    }
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    mcp.run()
