# Quantum Setup Generator (QSetup)
### Automated Design of Quantum Optical Experiments
**PhysisTechne Symposium 2026 — Machine Learning Problem Statement**

---

## Abstract

QSetup is an AI system that autonomously designs photonic quantum optical experiments to prepare specified multi-qubit target states. Given a target quantum state ρ_output, the system uses a **Genetic Algorithm** to search over a fixed component library, evolving circuit candidates and evaluating them using real quantum physics simulation via **QuTiP**. Fidelity is computed using the exact formula from the problem statement:

```
F(ρ_target, ρ_out) = ( Tr √( √ρ_target · ρ_out · √ρ_target ) )²
```

The system also integrates a **TF-IDF RAG pipeline** over uploaded research papers, grounding the search in published experimental literature.

---

## Repository Structure

```
PhysisTechneSymposium_Hackathon/
  backend/
    main.py              ← Full backend: GA + physics engine + Flask API
    requirements.txt     ← Python dependencies
    Procfile             ← Render.com deployment config
    runtime.txt          ← Python version pin (3.11.8)
    .env.example         ← Environment variable template
  qsetup/
    pages/index.js       ← Next.js frontend (QSetup UI)
    components/
      OpticalBench.js    ← Physics-accurate SVG optical diagram
      MathPanel.js       ← Mathematical output panel
    styles/globals.css
    package.json
  ml-genetic-algo.ipynb  ← Main Kaggle notebook (verified working)
  README.md
```

---

## How to Reproduce

### Option 1 — Live Website
- **Frontend:** https://57d78659-d9db-4cbe-af40-a8dbb4c82391-00-3cmvq71seus2h.picard.replit.dev
- **Backend API:** https://qsetup-backend.onrender.com
- **Health check:** https://qsetup-backend.onrender.com/health

### Option 2 — Run Locally (Kaggle)
1. Upload `ml-genetic-algo.ipynb` to Kaggle
2. Attach the research papers dataset from HuggingFace:
   `sourishdutta/PhysisTechneSymposium`
3. Enable Internet access in notebook settings
4. Run all cells in order
5. The last cell starts the Flask server and prints the public URL

### Option 3 — Run Backend Locally
```bash
git clone https://github.com/sourishkumardutta/PhysisTechneSymposium_Hackathon
cd PhysisTechneSymposium_Hackathon/backend
pip install -r requirements.txt
export HF_REPO=sourishdutta/PhysisTechneSymposium
python main.py
# Server runs at http://localhost:8000
```

### API Usage
```bash
# Health check
curl https://qsetup-backend.onrender.com/health

# Design query (POST)
curl -X POST https://qsetup-backend.onrender.com/query \
  -H "Content-Type: application/json" \
  -d '{"query": "design a Bell state experiment"}'

# List all supported states
curl https://qsetup-backend.onrender.com/targets

# List component library
curl https://qsetup-backend.onrender.com/components
```

---

## Component Library

All components are physically modelled with their correct unitary matrices.

| Component | Purpose | Unitary |
|---|---|---|
| **PhaseShifter** | Applies arbitrary phase shift φ to a spatial/polarization mode | `U_PS(φ) = diag(1, e^{iφ})` |
| **HWP** | Half-wave plate: rotates polarization by twice the plate angle θ | `U_HWP(θ) = [[cos2θ, sin2θ], [sin2θ, -cos2θ]]` |
| **QWP** | Quarter-wave plate: introduces 90° phase retardation | `U_QWP(θ) = (1/√2)[[1-i·cos2θ, -i·sin2θ], [-i·sin2θ, 1+i·cos2θ]]` |
| **BS** | 50:50 beam splitter: coherent mixing of two spatial modes | `U_BS(r) = [[√(1-r), i√r], [i√r, √(1-r)]]` |
| **PBS** | Polarizing beam splitter: transmits H, reflects V polarization | Projects onto H/V basis |
| **SPDC** | Spontaneous Parametric Down-Conversion: produces polarization-entangled Bell state \|Φ⁺⟩ via phase-matched nonlinear crystal (BBO, Type-II) | Output: `\|Φ⁺⟩ = (\|HH⟩ + \|VV⟩)/√2` |
| **CrossKerr** | Cross-Kerr nonlinear crystal: conditional phase shift e^{iφ·n̂_a·n̂_b} | `U_CK = diag(1,1,1,e^{iφ})` |
| **ThresholdDetector** | On/off detector: distinguishes vacuum from ≥1 photon | Click/no-click |
| **PNRDetector** | Photon-number-resolving detector: measures exact photon number | Number-resolving |
| **PostSelection** | Keeps only runs matching required coincidence pattern | Classical post-processing |
| **Heralding** | Uses ancilla detector click to conditionally accept prepared state | Conditional acceptance |
| **VacuumAncilla** | Injects vacuum state \|0⟩ into a spatial mode for interference | `\|0⟩` input |

**Constraints enforced (per PS):**
- Maximum 3 SPDC sources per design
- Maximum 4-qubit states
- Any number of VacuumAncilla inputs allowed

---

## Supported Target States (16 total)

| State | Qubits | Mathematical Form |
|---|---|---|
| `bell_phi_plus` | 2 | `(\|HH⟩ + \|VV⟩)/√2` |
| `bell_phi_minus` | 2 | `(\|HH⟩ - \|VV⟩)/√2` |
| `bell_psi_plus` | 2 | `(\|HV⟩ + \|VH⟩)/√2` |
| `bell_psi_minus` | 2 | `(\|HV⟩ - \|VH⟩)/√2` |
| `ghz_3` | 3 | `(\|HHH⟩ + \|VVV⟩)/√2` |
| `ghz_4` | 4 | `(\|HHHH⟩ + \|VVVV⟩)/√2` |
| `w_3` | 3 | `(\|HVV⟩ + \|VHV⟩ + \|VVH⟩)/√3` |
| `w_4` | 4 | `(\|HVVV⟩ + \|VHVV⟩ + \|VVHV⟩ + \|VVVH⟩)/2` |
| `cluster_linear_3` | 3 | `CZ₁₂·CZ₂₃·\|+⟩⊗³` |
| `cluster_linear_4` | 4 | `CZ₁₂·CZ₂₃·CZ₃₄·\|+⟩⊗⁴` |
| `cluster_square_4` | 4 | `CZ₁₂·CZ₂₃·CZ₃₄·CZ₄₁·\|+⟩⊗⁴` |
| `dicke_4_1` | 4 | `D(4,1)`: equal superposition of all 1-excitation states |
| `dicke_4_2` | 4 | `D(4,2)`: equal superposition of all 2-excitation states |
| `star_3` | 3 | `CZ₀₁·CZ₀₂·\|+⟩⊗³` (star graph) |
| `star_4` | 4 | `CZ₀₁·CZ₀₂·CZ₀₃·\|+⟩⊗⁴` (star graph) |
| `ring_4` | 4 | `CZ₁₂·CZ₂₃·CZ₃₄·CZ₄₁·\|+⟩⊗⁴` (cycle graph) |

---

## Algorithm

### 1. Genetic Algorithm (Core AI)

The GA autonomously discovers photonic circuits without hardcoded templates.

```
Chromosome  : ordered list of component types
              e.g. ["SPDC", "SPDC", "BS", "HWP", "PostSelection", "PNRDetector"]

Fitness     : F(ρ_target, ρ_out) − λ₁·(n_SPDC − 1) − λ₂·(n_components − 6)
              Primary: real QuTiP fidelity
              Secondary: penalties for resource usage

Selection   : Tournament selection (k=3)
Crossover   : Single-point crossover (rate=0.60)
Mutation    : Replace / Insert / Delete / Swap a gene (rate=0.25)
Elitism     : Top 2 individuals preserved each generation
Constraints : max 3 SPDC, max 12 components (hard constraints)
```

**Default hyperparameters** (all tunable via environment variables):

| Parameter | Default | Env var |
|---|---|---|
| Population size | 20 | `GA_POP_SIZE` |
| Generations | 30 | `GA_GENERATIONS` |
| Mutation rate | 0.25 | `GA_MUTATION` |
| Crossover rate | 0.60 | `GA_CROSSOVER` |
| Max SPDC | 3 | `GA_MAX_SPDC` |

### 2. Physics Simulation (QuTiP)

Each candidate circuit is simulated using exact quantum mechanics:

1. **Input state**: tensor product of Bell pairs from each SPDC source
   `ρ_in = \|Φ⁺⟩⟨Φ⁺\| ⊗ ... ⊗ \|Φ⁺⟩⟨Φ⁺\|`

2. **Component application**: each component applies its unitary
   `ρ → U · ρ · U†`

3. **Post-selection**: partial trace over ancilla modes
   `ρ_out = Tr_ancilla(ρ)`

4. **Fidelity**: computed via QuTiP's `qt.fidelity()`
   `F = (Tr√(√ρ_t · ρ_out · √ρ_t))²`

### 3. RAG Pipeline (TF-IDF)

Research papers from `sourishdutta/PhysisTechneSymposium` (HuggingFace) are:
- Chunked (1400 chars, 250 overlap)
- Indexed with TF-IDF (30,000 features, bigrams)
- Retrieved at query time to provide experimental context

### 4. Natural Language Interface

Queries are parsed using:
- Regex-based parameter extraction (wavelength, crystal type, angles)
- Alias matching for state names
- Intent classification (design vs. Q&A vs. general)
- Nonsense query rejection (non-domain token ratio check)

---

## Fidelity Results (typical)

| Target State | Fidelity | Source | SPDC Count |
|---|---|---|---|
| Bell Φ⁺ | ~0.85–0.94 | QuTiP simulation | 1 |
| GHZ-3 | ~0.72–0.84 | QuTiP simulation | 2 |
| GHZ-4 | ~0.65–0.78 | QuTiP simulation | 2 |
| W-3 | ~0.70–0.80 | QuTiP simulation | 1 |
| Cluster-4 | ~0.62–0.76 | QuTiP simulation | 2 |

*Results vary per GA run due to stochastic search.*

---

## Algorithm Runtime

| State | GA Generations | Population | Typical Runtime |
|---|---|---|---|
| 2-qubit (Bell) | 30 | 20 | ~3–8s |
| 3-qubit (GHZ-3, W-3) | 30 | 20 | ~8–15s |
| 4-qubit (GHZ-4, Cluster) | 30 | 20 | ~15–30s |

Runtime scales with `O(pop_size × generations × simulate_circuit_cost)`.

---

## Dependencies

```
flask==3.0.3
flask-cors==4.0.1
pypdf==4.2.0
scikit-learn==1.4.2
numpy==1.26.4
qutip==4.7.6
huggingface_hub==0.23.0
gunicorn==22.0.0
```

Python version: 3.11.8

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `HF_REPO` | HuggingFace dataset with research PDFs | `sourishdutta/PhysisTechneSymposium` |
| `HF_TOKEN` | HuggingFace token (only if private dataset) | `hf_xxxx` |
| `GA_POP_SIZE` | GA population size | `20` |
| `GA_GENERATIONS` | GA generations | `30` |
| `PDF_DIR` | Directory to store downloaded PDFs | `/tmp/pdfs` |

---

## Judging Criteria Mapping

| Criterion | Implementation |
|---|---|
| **Beauty of the algorithm** | Genetic Algorithm with tournament selection, crossover, mutation, elitism — clean evolutionary search over component space |
| **Reproducibility** | Fixed random seed (42), deterministic QuTiP simulation, all hyperparameters exposed as env vars |
| **Algorithm runtime** | ~3–30s depending on qubit count; configurable via `GA_GENERATIONS` and `GA_POP_SIZE` |
| **Autonomous design capability** | GA discovers circuits from scratch — no hardcoded templates, works for any target state including unseen ones |

---

## Team

**PhysisTechne Symposium 2026**
Repository: https://github.com/sourishkumardutta/PhysisTechneSymposium_Hackathon
Research papers: https://huggingface.co/datasets/sourishdutta/PhysisTechneSymposium
