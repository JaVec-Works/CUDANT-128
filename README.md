# CUDANT

**Fidelity-gated GPU quantum & physics simulator with MCP agent interface.**

CUDANT gives an LLM agent direct access to a GPU quantum simulator that **refuses to answer when it cannot be trusted.** No silently wrong results. No hallucinated qubits. If the bond dimension is too small, it tells you. If the gate syntax is ambiguous, it tells you. You get a result or you get a reason.

## What it does

| Tool | Qubits | Backend | Purpose |
|------|--------|---------|---------|
| run_lion | 2-16 | PyTorch dense (exact) | Fast small circuits, Bell pairs, GHZ |
| run_mps | 17-128 | CUDA-Q tensornet-mps (GPU) | Large entangled states, fidelity-gated |
| settle_field | - | PyTorch conv3d (GPU) | 3D diffusion/heat/field simulation |
| widen_search | 2-16 | PyTorch batched Grover | Parallel search, hit-rate stats |

## The fidelity gate

run_mps runs every circuit TWICE (at chi_max and chi_max x 4). If the top-1 probability differs by more than epsilon, it REFUSES and returns advice on how to fix it. The LLM reads the advice, retries, and gets a confirmed answer. No human in the loop.



## Requirements

- NVIDIA GPU (Pascal or newer, 4GB+ VRAM)
- Windows 11 + WSL2 (or native Linux)
- Python 3.10+

## Install

For a detailed, step-by-step guide (written for beginners), see INSTALL.md. - Or continue here if you know what you are doing.

### WSL2 (Windows)

    wsl --install -d Ubuntu-24.04

Reboot. Inside Ubuntu:

    sudo apt update
    sudo apt install -y python3-pip python3.12-venv
    python3 -m venv ~/cudant
    source ~/cudant/bin/activate
    pip install -r requirements.txt

### Verify GPU

    nvidia-smi

Should show your GPU. If not, install the latest NVIDIA Windows driver.

### Run the server

    python3 cudant_mcp.py

You should see the FastMCP banner. The server is now listening on stdio.

## Connect to an LLM (Pi)

In ~/.pi/agent/mcp.json:

    {
      "mcpServers": {
        "cudant": {
          "command": "wsl",
          "args": ["-d", "Ubuntu-24.04", "--", "/home/USER/cudant/bin/python", "/home/USER/cudant_mcp.py"],
          "exposure": "direct",
          "description": "GPU quantum/physics simulator. Tools: run_lion (exact, 2-16 qubits), run_mps (fidelity-gated, 17-128 qubits), settle_field (3D GPU field), widen_search (batch Grover)."
        }
      }
    }

Replace USER with your username. Restart your LLM client.



## Gate syntax

    H0  X1  Z2          Single-qubit (letter + index)
    CNOT01              CNOT qubits 0-9 (no underscore)
    CNOT9_10            CNOT qubits 10+ (underscore REQUIRED)
    CNOT10_11           CNOT qubits 10+

Gates are comma-separated: "H0,CNOT01,CNOT1_2,CNOT9_10"

## Example prompts

| Prompt | Tool | Result |
|--------|------|--------|
| "Run a Bell pair on 2 qubits" | run_lion | 00: 0.5, 11: 0.5 |
| "Prepare a GHZ state on 20 qubits with bond dimension 16" | run_mps | Fidelity-confirmed 50/50 |
| "Run 1000 parallel Grover searches for target 1010 on 4 qubits" | widen_search | Hit rate ~100% |
| "Settle a 64-cubed field with center 0.9, neighbor 0.004, 100 steps" | settle_field | Energy/spread stats |

## Architecture

    LLM Agent (Pi, Claude, etc.)
        |
        |  MCP (stdio, JSON-RPC)
        v
    cudant_mcp.py  (FastMCP server)
        |
        +-- run_lion ----> PyTorch CUDA (dense, exact)
        +-- run_mps -----> CUDA-Q tensornet-mps (MPS, fidelity-gated)
        +-- settle_field-> PyTorch conv3d (3D field)
        +-- widen_search-> PyTorch batched Grover

## Tested

| Qubits | Path | Result |
|--------|------|--------|
| 4 | run_lion | 50/50 exact |
| 16 | run_lion | 50/50 exact |
| 32 | run_mps | 492/508 confirmed |
| 64 | run_mps | 532/468 confirmed |
| 128 | run_mps | 510/490 confirmed |

Hardware: Quadro RTX 4000 (8GB VRAM), i9-9880H, WSL2 on Windows 11.

## License

MIT
