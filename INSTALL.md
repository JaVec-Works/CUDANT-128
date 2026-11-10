

```
# Installing CUDANT-128

This guide walks you through installing CUDANT-128 step by step.
No prior experience needed. If you can install a game, you can do this.

---

## Before you start: what you need

| What | Why | How to check |
|------|-----|--------------|
| An NVIDIA graphics card | The math runs on the GPU | Right-click desktop → "NVIDIA Control Panel" (if it opens, you have one) |
| 4GB or more VRAM | The quantum states need memory | Open NVIDIA Control Panel → "System" → look for "Video Memory" |
| Windows 11, Linux, or macOS | The operating system | You know which one you have |

**If you have an AMD or Intel graphics card:** CUDANT-128 will not work. It requires NVIDIA. This is a limitation of the CUDA-Q engine, not of CUDANT itself.

**If you have no GPU at all:** You can still run CUDANT-128 on CPU, but it will be very slow and limited to about 16 qubits. See "macOS / CPU-only" below.

---

## Pick your path

| I am using... | Go to... | Difficulty |
|---------------|----------|------------|
| Windows 11 (most common) | **Path A: WSL2** | Medium (30 min) |
| Any OS + I already use Docker | **Path B: Docker** | Easy (10 min) |
| Linux (Ubuntu, Fedora, etc.) | **Path C: Native Linux** | Easy (15 min) |
| macOS (Apple) | **Path D: CPU-only** | Easy (10 min) |
| Windows, no WSL2, no Docker | **Path E: Limited** | Easy (10 min) |

**Which one can do what:**

| Path | run_lion (2-16 qubits) | run_mps (17-128 qubits) | settle_field | widen_search |
|------|:---:|:---:|:---:|:---:|
| A: WSL2 | ✅ GPU | ✅ GPU | ✅ GPU | ✅ GPU |
| B: Docker | ✅ GPU | ✅ GPU | ✅ GPU | ✅ GPU |
| C: Native Linux | ✅ GPU | ✅ GPU | ✅ GPU | ✅ GPU |
| D: macOS CPU | ✅ CPU (slow) | ❌ | ✅ CPU (slow) | ✅ CPU (slow) |
| E: Windows limited | ✅ GPU | ❌ | ✅ GPU | ✅ GPU |

**"GPU" means fast. "CPU" means it works but slowly. "❌" means that tool is not available on that path.**

---

## Path A: Windows 11 + WSL2 (recommended for most Windows users)

WSL2 is a feature built into Windows 11 that lets you run a real Linux system inside Windows. Think of it as a Linux computer that lives inside your Windows computer.

### Step 1: Install WSL2

1. Press the **Windows key** on your keyboard
2. Type **PowerShell**
3. Right-click "Windows PowerShell" → **"Run as administrator"**
4. A blue window opens. Type this and press Enter:
```

wsl --install -d Ubuntu-24.04

```

5. Wait. It will download and install. This takes 5-10 minutes.
6. When it says "Restart," **restart your computer.**
7. After restart, an **Ubuntu** window will pop up automatically.
8. It will ask you to create a **username** and **password.**
   - Type a username (e.g., `prowler`) → press Enter
   - Type a password → press Enter (you will NOT see characters appear as you type — this is normal, just type and press Enter)
   - Type the password again → press Enter

**You now have Linux running inside Windows.** The Ubuntu window is your Linux terminal.

### Step 2: Install the software

In the Ubuntu window, type these commands one at a time (type, press Enter, wait, then next):
```

sudo apt update

```
(If it asks for a password, type your Ubuntu password. You won't see it. Press Enter.)
```

sudo apt install -y python3-pip python3.12-venv

python3 -m venv ~/cudant

source ~/cudant/bin/activate

```

**After this command, your prompt changes.** It now starts with `(cudant)` like this:
```

(cudant) yourname@computer:~$

```
That means you're "inside" a safe sandbox. Everything you install now goes into this sandbox, not your system.
```

pip install torch numpy cudaq fastmcp

```

**This is the big download.** It's about 3GB. Give it 10-20 minutes depending on your internet. You'll see progress bars. Let it finish. Don't close the window.

### Step 3: Check your GPU is visible
```

nvidia-smi

```

**If you see a table with your GPU name (e.g., "Quadro RTX 4000" or "GeForce RTX 3060"):** you're good. Press Ctrl+C to exit the table.

**If it says "command not found":** your Windows NVIDIA driver is not set up for WSL. Update your GPU driver from [nvidia.com/drivers](https://www.nvidia.com/drivers), restart, and try again.

### Step 4: Download and run CUDANT-128
```

cd ~  
git clone [https://github.com/JaVec-Works/CUDANT-128](https://github.com/JaVec-Works/CUDANT-128)

```
(If it says "git: command not found," run `sudo apt install -y git` first, then try again.)
```

cd CUDANT-128

python3 cudant_mcp.py

```

**You should see a banner that says "CUDANT Engine" and "Starting MCP server."** That means it's running. Leave this window open.

### Step 5: Test it

Open a **second** Ubuntu window (right-click the Ubuntu icon in your taskbar → "New Window"). Type:
```

source ~/cudant/bin/activate  
cd ~/CUDANT-128  
python3 -c "from cudant_mcp import run_lion; print(run_lion(2, 'H0,CNOT01'))"

```

**If you see this, you're done:**
```

{  
"qubits": 2,  
"probabilities": {  
"|00>": 0.5,  
"|11>": 0.5  
},  
"answer": "|00>",  
"confidence": 0.5  
}

```

**Congratulations. You just ran a quantum circuit on your GPU.**

---

## Path B: Docker (easiest, works on any OS)

Docker is a way to run a complete, pre-built software environment in a "box." You don't install anything on your system — the box has everything inside it.

### What you need first:

1. **Docker Desktop** — download from [docker.com/products/docker-desktop](https://docker.com/products/docker-desktop)
   - Windows: install it, restart, launch it from your Start menu
   - macOS: install it, it appears in your menu bar
   - Linux: `sudo apt install -y docker.io` then `sudo systemctl start docker`

2. **NVIDIA Container Toolkit** (only if you have an NVIDIA GPU):
   - Windows: Docker Desktop handles this automatically
   - Linux: follow the instructions at [docs.nvidia.com/datacenter/cloud-native/container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

3. **A free NVIDIA account** (for pulling the CUDA-Q image):
   - Go to [ngc.nvidia.com](https://ngc.nvidia.com)
   - Click "Sign Up" (free)
   - Go to [ngc.nvidia.com/setup/api-key](https://ngc.nvidia.com/setup/api-key)
   - Click "Create API Key" → copy the key

### Step 1: Log in to NVIDIA's image registry

Open a terminal (PowerShell on Windows, Terminal on macOS/Linux). Type:
```

echo "nvapi-YOUR_API_KEY_HERE" | docker login nvcr.io -u '$oauthtoken' --password-stdin

```

Replace `YOUR_API_KEY_HERE` with the key you copied. **Keep the single quotes around `$oauthtoken`** — do not remove them.

**Expected:** `Login Succeeded`

### Step 2: Pull the CUDA-Q image
```

docker pull nvcr.io/nvidia/quantum/cuda-quantum:cu13-0.16.0

```

This downloads about 4GB. Give it 10-20 minutes.

### Step 3: Run CUDANT-128
```

docker run --gpus all -it --rm  
-v $(pwd):/app  
nvcr.io/nvidia/quantum/cuda-quantum:cu13-0.16.0  
bash -c "pip install torch fastmcp && python3 cudant_mcp.py"

```

**Wait** — you need the file inside the container. The easier way:
```

git clone [https://github.com/JaVec-Works/CUDANT-128](https://github.com/JaVec-Works/CUDANT-128)  
cd CUDANT-128  
docker run --gpus all -it --rm  
-v $(pwd):/app -w /app  
nvcr.io/nvidia/quantum/cuda-quantum:cu13-0.16.0  
bash -c "pip install torch fastmcp && python3 cudant_mcp.py"

```

**On Windows (PowerShell), replace `$(pwd)` with `$(Get-Location)` or just use the full path:**
```

docker run --gpus all -it --rm -v "D:\PROJECTS\CUDANT-128:/app" -w /app nvcr.io/nvidia/quantum/cuda-quantum:cu13-0.16.0 bash -c "pip install torch fastmcp && python3 cudant_mcp.py"

```

**You should see the "CUDANT Engine" banner.** The server is running inside the Docker box.

### What "Docker" means in plain English:

- `docker pull` = "download the box"
- `docker run` = "open the box and run the thing inside it"
- `--gpus all` = "let the box use your graphics card"
- `-v` = "let the box see files from your computer"
- `--rm` = "delete the box when I'm done"

You don't need to understand all of this. Just run the commands.

---

## Path C: Native Linux (Ubuntu, Fedora, etc.)

If you're already on Linux, this is the easiest path.

### Step 1: Install prerequisites
```

sudo apt update  
sudo apt install -y python3-pip python3-venv git

```

(On Fedora: `sudo dnf install -y python3-pip python3-venv git`)

### Step 2: Create a sandbox
```

python3 -m venv ~/cudant  
source ~/cudant/bin/activate

```

Your prompt now shows `(cudant)`. Good.

### Step 3: Install
```

pip install torch numpy cudaq fastmcp

```

### Step 4: Check GPU
```

nvidia-smi

```

Should show your GPU. If not, install the NVIDIA driver for your distro.

### Step 5: Run
```

git clone [https://github.com/JaVec-Works/CUDANT-128](https://github.com/JaVec-Works/CUDANT-128)  
cd ~/CUDANT-128  
python3 cudant_mcp.py

```

**Done.** Same test as Path A, Step 5.

---

## Path D: macOS / CPU-only (no GPU)

If you're on a Mac (Apple silicon) or don't have an NVIDIA GPU, you can still use CUDANT-128 but:
- It runs on CPU (slower)
- `run_mps` (17-128 qubits) **will not work** (it requires a GPU)
- `run_lion`, `settle_field`, `widen_search` work fine up to 16 qubits

### Step 1: Install Python (if you don't have it)
```

brew install python

```

(If you don't have Homebrew: go to [brew.sh](https://brew.sh), copy the install command, paste it in Terminal.)

### Step 2: Install CUDANT-128
```

python3 -m venv ~/cudant  
source ~/cudant/bin/activate  
pip install torch numpy cudaq fastmcp  
git clone [https://github.com/JaVec-Works/CUDANT-128](https://github.com/JaVec-Works/CUDANT-128)  
cd ~/CUDANT-128  
python3 cudant_mcp.py

```

**Note:** `cudaq` on macOS uses the CPU backend (`qpp-cpu`). The `run_mps` tool will return an error if you try to use it. That's expected.

---

## Path E: Windows without WSL2 or Docker (limited)

This gives you `run_lion`, `settle_field`, and `widen_search` on your GPU. It does **not** give you `run_mps` (the 17-128 qubit path requires Linux).

### Step 1: Install Python

Go to [python.org](https://python.org), download Python 3.10+, install it. **Check the box that says "Add Python to PATH"** during install.

### Step 2: Open a terminal

Press Windows key → type **cmd** → press Enter.

### Step 3: Install
```

pip install torch numpy fastmcp

```

(Note: `cudaq` is NOT installed here — it requires Linux.)

### Step 4: Run (modified — MPS tools will error)
```

git clone [https://github.com/JaVec-Works/CUDANT-128](https://github.com/JaVec-Works/CUDANT-128)  
cd CUDANT-128  
python cudant_mcp.py

````

If it errors on the `import cudaq` line, add this to the top of `cudant_mcp.py` (after the copyright header):

```python
try:
    import cudaq
except ImportError:
    cudaq = None
````

And in `run_mps`, the first line should be:

```
if cudaq is None:
    return json.dumps({"error": "run_mps requires Linux/WSL2. Not available on native Windows."})
```

**This path is a compromise.** For the full experience, use Path A (WSL2) or Path B (Docker).

---

## Verify it works (all paths)

Once the server is running, open a second terminal and run:

**Test 1: Bell pair (2 qubits, exact)**

```
python3 -c "import sys; sys.path.insert(0,'.'); from cudant_mcp import run_lion; print(run_lion(2, 'H0,CNOT01'))"
```

Expected: `|00>: 0.5, |11>: 0.5`

**Test 2: 4-qubit GHZ (exact)**

```
python3 -c "import sys; sys.path.insert(0,'.'); from cudant_mcp import run_lion; print(run_lion(4, 'H0,CNOT0_1,CNOT1_2,CNOT2_3'))"
```

Expected: `|0000>: 0.5, |1111>: 0.5`

**Test 3: 20-qubit GHZ (MPS, GPU only)**

```
python3 -c "import sys; sys.path.insert(0,'.'); from cudant_mcp import run_mps; g='H0,'+','.join(f'CNOT{i}_{i+1}' for i in range(19)); print(run_mps(20, g, chi_max=16))"
```

Expected: `"fidelity": "confirmed"` with all-zeros and all-ones at ~50% each.

**If all three pass, your install is complete.**

---

## Troubleshooting

|   |   |
|---|---|
|Problem|Fix|
|`nvidia-smi: command not found` (WSL2)|Update your NVIDIA **Windows** driver. Don't install a Linux driver inside WSL.|
|`pip install cudaq` fails|Make sure you're inside the venv (prompt shows `(cudant)`).|
|`ModuleNotFoundError: No module named 'torch'`|You're not in the venv. Run `source ~/cudant/bin/activate` first.|
|Docker: `--gpus all` fails|Install the NVIDIA Container Toolkit. On Linux: `sudo apt install -y nvidia-container-toolkit` then `sudo systemctl restart docker`.|
|Docker: `unauthorized: authentication required`|You need to log in to nvcr.io first (Path B, Step 1).|
|`run_mps` returns an error|You're on a CPU-only path (macOS or native Windows). MPS requires a GPU + Linux.|
|Server starts but LLM can't see tools|Restart your LLM client. It caches the server list.|

---

## What "MCP" means (for the curious)

MCP (Model Context Protocol) is a standard way for AI assistants to "plug in" tools. Think of it like a USB port for AI. CUDANT-128 is the USB stick. Your LLM (Pi, Claude, etc.) is the computer. Once plugged in, the LLM can "see" your four tools and call them by name.

You don't need to understand the protocol. You just need to tell your LLM client where the server is (the Pi config in the main README).

---
