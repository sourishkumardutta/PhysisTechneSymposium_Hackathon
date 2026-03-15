"""
Quantum Optics RAG + Genetic Algorithm Backend
Render.com deployment — lives forever, no Kaggle needed.

On startup:
  1. Downloads PDFs from Hugging Face dataset (HF_REPO env var)
  2. Builds TF-IDF retriever over paper chunks
  3. Builds QuTiP density matrices for all 16 target states
  4. Starts Flask server

Environment variables (set in Render dashboard):
  HF_REPO   — HuggingFace dataset repo e.g. "yourname/quantum-papers"
  HF_TOKEN  — HuggingFace token (only if dataset is private)
  PORT      — set automatically by Render
"""

import os
import re
import json
import math
import glob
import uuid
import random
import traceback
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, request, jsonify
from flask_cors import CORS

random.seed(42)
np.random.seed(42)

# ── Paths ──────────────────────────────────────────────────────────────────
PDF_DIR  = os.environ.get("PDF_DIR",  "/tmp/pdfs")
WORK_DIR = os.environ.get("WORK_DIR", "/tmp")
HF_REPO  = os.environ.get("HF_REPO",  "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
os.makedirs(PDF_DIR,  exist_ok=True)
os.makedirs(WORK_DIR, exist_ok=True)

# ── Download PDFs from HuggingFace at startup ──────────────────────────────
def download_pdfs():
    if not HF_REPO:
        print("HF_REPO not set — skipping download, using local PDFs if any.")
        return
    try:
        from huggingface_hub import snapshot_download
        print(f"Downloading PDFs from {HF_REPO} ...")
        snapshot_download(
            repo_id=HF_REPO, repo_type="dataset",
            local_dir=PDF_DIR,
            token=HF_TOKEN or None,
            ignore_patterns=["*.json","*.md","*.gitattributes"],
        )
        pdfs = list(Path(PDF_DIR).rglob("*.pdf"))
        print(f"✅ Downloaded {len(pdfs)} PDFs to {PDF_DIR}")
    except Exception as e:
        print(f"⚠️  HuggingFace download failed: {e} — continuing without PDFs")

# ======================================================================
# CELL 2
# ======================================================================
import os
import re
import json
import math
import glob
import uuid
import random
import traceback
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

random.seed(42)
np.random.seed(42)

# ── Paths ──────────────────────────────────────────────────────────────────
DEFAULT_INPUT_ROOT = PDF_DIR
DEFAULT_WORK_ROOT  = WORK_DIR

# ── Config: all tuneable via environment variables ─────────────────────────
CONFIG = {
    "input_root":            os.environ.get("PDF_ROOT",   DEFAULT_INPUT_ROOT),
    "work_root":             os.environ.get("WORK_ROOT",  DEFAULT_WORK_ROOT),

    # chunking
    "chunk_size":            int(os.environ.get("CHUNK_SIZE",        1400)),
    "chunk_overlap":         int(os.environ.get("CHUNK_OVERLAP",      250)),
    "min_chunk_chars":       int(os.environ.get("MIN_CHUNK_CHARS",    180)),

    # retrieval
    "tfidf_max_features":    int(os.environ.get("TFIDF_MAX_FEATURES", 30000)),
    "top_k_default":         int(os.environ.get("TOP_K_DEFAULT",       6)),
    "scope_threshold":     float(os.environ.get("SCOPE_THRESHOLD",    0.08)),
    "rag_confidence_threshold": float(os.environ.get("RAG_CONFIDENCE_THRESHOLD", 0.12)),

    # search behaviour
    "max_return_contexts":   int(os.environ.get("MAX_RETURN_CONTEXTS",  5)),

    # design search
    "candidate_count":       int(os.environ.get("CANDIDATE_COUNT",    10)),
    "max_qubits_supported":  int(os.environ.get("MAX_QUBITS_SUPPORTED", 6)),
    "max_spdc_supported":    int(os.environ.get("MAX_SPDC_SUPPORTED",   4)),

}

print("CONFIG loaded:", CONFIG)

# ======================================================================
# CELL 3
# ======================================================================
# ── Load optional JSON overrides from /kaggle/input/config/ ────────────────
def load_json_if_exists(path: str, default_value: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: failed to load {path}: {e}")
    return default_value

CONFIG_DIR = os.path.join(CONFIG["input_root"], "config")

# ── Component library ──────────────────────────────────────────────────────
DEFAULT_COMPONENT_LIBRARY = {
    # ── Linear optical components ──────────────────────────────────────────
    "PhaseShifter":    {"purpose": "Applies controllable phase shift to a spatial or polarization mode.", "cost": 1, "spatial_modes": 0},
    "HWP":             {"purpose": "Half-wave plate: rotates polarization by twice the plate angle.",     "cost": 1, "spatial_modes": 0},
    "QWP":             {"purpose": "Quarter-wave plate: introduces 90-degree phase retardation.",         "cost": 1, "spatial_modes": 0},
    "BS":              {"purpose": "50:50 beam splitter for coherent mixing of two spatial modes.",       "cost": 2, "spatial_modes": 2},
    "PBS":             {"purpose": "Polarizing beam splitter: transmits H, reflects V polarization.",     "cost": 2, "spatial_modes": 2},
    # ── Nonlinear sources ─────────────────────────────────────────────────
    "SPDC":            {"purpose": "SPDC photon-pair source: produces polarization-entangled Bell state |Phi+> via phase-matched nonlinear crystal.", "cost": 4, "spatial_modes": 2},
    "CrossKerr":       {"purpose": "Cross-Kerr nonlinear crystal: imparts a phase shift on one mode conditioned on photon number in another mode.", "cost": 5, "spatial_modes": 2},
    # ── Detectors ─────────────────────────────────────────────────────────
    "ThresholdDetector":{"purpose": "Threshold (on/off) detector: distinguishes vacuum from one-or-more photons.", "cost": 2, "spatial_modes": 0},
    "PNRDetector":     {"purpose": "Photon-number-resolving detector: measures exact photon number in a mode.", "cost": 3, "spatial_modes": 0},
    # ── Conditioning ──────────────────────────────────────────────────────
    "PostSelection":   {"purpose": "Post-selection: keeps only runs where detectors fire in the required coincidence pattern.", "cost": 1, "spatial_modes": 0},
    "Heralding":       {"purpose": "Heralding: uses an ancilla detector click to conditionally accept a prepared state.", "cost": 2, "spatial_modes": 0},
    # ── Ancilla inputs ────────────────────────────────────────────────────
    "VacuumAncilla":   {"purpose": "Vacuum ancilla: injects a vacuum state |0> into a spatial mode for interference.", "cost": 0, "spatial_modes": 1},
}

# ── Target quantum states (all 16) ────────────────────────────────────────
DEFAULT_TARGET_STATES = {
    # ── Bell family (2-qubit) ──────────────────────────────────────────────
    "bell_phi_plus": {
        "num_qubits": 2, "num_spdc": 1,
        "description": "Bell state |Phi+> = (|00> + |11>) / sqrt(2)",
        "aliases": ["bell", "phi plus", "bell phi plus", "bell state", "phi+", "bell phi +"],
        "keywords": ["bell", "two qubit", "entangled", "polarization entanglement"],
        "base_fidelity": 0.92, "base_success": 0.84,
    },
    "bell_phi_minus": {
        "num_qubits": 2, "num_spdc": 1,
        "description": "Bell state |Phi-> = (|00> - |11>) / sqrt(2)",
        "aliases": ["phi minus", "bell phi minus", "phi-", "bell phi -"],
        "keywords": ["bell", "phi minus", "two qubit", "entangled"],
        "base_fidelity": 0.91, "base_success": 0.83,
    },
    "bell_psi_plus": {
        "num_qubits": 2, "num_spdc": 1,
        "description": "Bell state |Psi+> = (|01> + |10>) / sqrt(2)",
        "aliases": ["psi plus", "bell psi plus", "psi+", "bell psi +"],
        "keywords": ["bell", "psi plus", "two qubit", "entangled", "anti-correlated"],
        "base_fidelity": 0.91, "base_success": 0.83,
    },
    "bell_psi_minus": {
        "num_qubits": 2, "num_spdc": 1,
        "description": "Bell state |Psi-> = (|01> - |10>) / sqrt(2)",
        "aliases": ["psi minus", "bell psi minus", "psi-", "bell psi -", "singlet"],
        "keywords": ["bell", "psi minus", "singlet", "two qubit", "entangled"],
        "base_fidelity": 0.90, "base_success": 0.82,
    },
    # ── GHZ family ────────────────────────────────────────────────────────
    "ghz_3": {
        "num_qubits": 3, "num_spdc": 2,
        "description": "3-qubit GHZ state = (|000> + |111>) / sqrt(2)",
        "aliases": ["ghz 3", "ghz_3", "3 qubit ghz", "three qubit ghz", "ghz three"],
        "keywords": ["ghz", "three qubit", "multipartite entanglement", "fusion", "post-selection"],
        "base_fidelity": 0.82, "base_success": 0.62,
    },
    "ghz_4": {
        "num_qubits": 4, "num_spdc": 2,
        "description": "4-qubit GHZ state = (|0000> + |1111>) / sqrt(2)",
        "aliases": ["ghz 4", "ghz_4", "4 qubit ghz", "four qubit ghz", "ghz four"],
        "keywords": ["ghz", "four qubit", "multipartite entanglement", "fusion", "heralding"],
        "base_fidelity": 0.75, "base_success": 0.48,
    },
    # ── W family ──────────────────────────────────────────────────────────
    "w_3": {
        "num_qubits": 3, "num_spdc": 1,
        "description": "3-qubit W state = (|001> + |010> + |100>) / sqrt(3)",
        "aliases": ["w state", "w_3", "3 qubit w", "three qubit w", "w three"],
        "keywords": ["w state", "three qubit", "beam splitter", "post-selection", "symmetric superposition"],
        "base_fidelity": 0.78, "base_success": 0.58,
    },
    "w_4": {
        "num_qubits": 4, "num_spdc": 2,
        "description": "4-qubit W state = (|0001>+|0010>+|0100>+|1000>) / 2",
        "aliases": ["w 4", "w_4", "4 qubit w", "four qubit w", "w four"],
        "keywords": ["w state", "four qubit", "symmetric superposition", "post-selection"],
        "base_fidelity": 0.72, "base_success": 0.45,
    },
    # ── Cluster states ────────────────────────────────────────────────────
    "cluster_linear_3": {
        "num_qubits": 3, "num_spdc": 2,
        "description": "3-qubit linear cluster state for measurement-based QC",
        "aliases": ["cluster 3", "linear cluster 3", "cluster_linear_3", "3 qubit cluster", "cluster three"],
        "keywords": ["cluster", "linear cluster", "measurement based", "graph state", "three qubit"],
        "base_fidelity": 0.80, "base_success": 0.55,
    },
    "cluster_linear_4": {
        "num_qubits": 4, "num_spdc": 2,
        "description": "4-qubit linear cluster state for measurement-based QC",
        "aliases": ["cluster 4", "linear cluster 4", "cluster_linear_4", "4 qubit cluster", "cluster four"],
        "keywords": ["cluster", "linear cluster", "measurement based", "graph state", "four qubit"],
        "base_fidelity": 0.74, "base_success": 0.46,
    },
    "cluster_square_4": {
        "num_qubits": 4, "num_spdc": 2,
        "description": "4-qubit square (2D) cluster state",
        "aliases": ["square cluster", "2d cluster", "cluster square 4", "cluster_square_4", "box cluster"],
        "keywords": ["cluster", "square cluster", "2d cluster", "graph state", "four qubit"],
        "base_fidelity": 0.73, "base_success": 0.44,
    },
    # ── Dicke states ──────────────────────────────────────────────────────
    "dicke_4_1": {
        "num_qubits": 4, "num_spdc": 2,
        "description": "4-qubit Dicke state D(4,1) — 1 excitation in 4 qubits",
        "aliases": ["dicke 4 1", "dicke_4_1", "d41", "dicke one excitation four"],
        "keywords": ["dicke", "symmetric", "one excitation", "four qubit", "post-selection"],
        "base_fidelity": 0.74, "base_success": 0.46,
    },
    "dicke_4_2": {
        "num_qubits": 4, "num_spdc": 2,
        "description": "4-qubit Dicke state D(4,2) — 2 excitations in 4 qubits",
        "aliases": ["dicke 4 2", "dicke_4_2", "d42", "dicke two excitations four"],
        "keywords": ["dicke", "symmetric", "two excitations", "four qubit", "post-selection"],
        "base_fidelity": 0.72, "base_success": 0.44,
    },
    # ── Star / Ring states ────────────────────────────────────────────────
    "star_3": {
        "num_qubits": 3, "num_spdc": 2,
        "description": "3-qubit star graph state — one central qubit connected to two leaves",
        "aliases": ["star 3", "star_3", "star state 3", "three qubit star"],
        "keywords": ["star", "graph state", "three qubit", "cluster", "CZ gate"],
        "base_fidelity": 0.79, "base_success": 0.57,
    },
    "star_4": {
        "num_qubits": 4, "num_spdc": 2,
        "description": "4-qubit star graph state — one central qubit connected to three leaves",
        "aliases": ["star 4", "star_4", "star state 4", "four qubit star"],
        "keywords": ["star", "graph state", "four qubit", "cluster", "CZ gate"],
        "base_fidelity": 0.73, "base_success": 0.45,
    },
    "ring_4": {
        "num_qubits": 4, "num_spdc": 2,
        "description": "4-qubit ring (cycle) graph state — qubits connected in a cycle",
        "aliases": ["ring 4", "ring_4", "ring state", "four qubit ring", "cycle state"],
        "keywords": ["ring", "cycle", "graph state", "four qubit", "cluster", "periodic"],
        "base_fidelity": 0.73, "base_success": 0.44,
    },
}

# ── Domain knowledge ───────────────────────────────────────────────────────
DEFAULT_DOMAIN_KNOWLEDGE = {
    "domain_name": "quantum optics experiment design",
    "domain_keywords": [
        "quantum", "photon", "photonic", "optics", "optical", "spdc", "beam splitter",
        "pbs", "hwp", "qwp", "phase shifter", "bell", "ghz", "w state", "entanglement",
        "entangled", "post-selection", "heralding", "detector", "polarization", "state",
        "qubit", "interference", "fidelity", "superposition", "waveplate",
        "cluster", "graph state", "dicke", "star", "ring", "w4", "psi", "phi",
        "singlet", "symmetric", "measurement based", "linear cluster", "cycle",
        "bell state", "ghz state", "cluster state", "dicke state", "dicke system",
        "star state", "ring state", "graph", "entangled state", "photonic state",
        "excitation", "w4 state", "w 4", "qubit state",
    ],
    "design_intents": ["construct", "build", "design", "generate", "create", "produce", "make", "setup"],
    "qa_intents":     ["what is", "explain", "how does", "difference between", "compare", "define"],
}

# Load overrides if present
COMPONENT_LIBRARY  = load_json_if_exists(os.path.join(CONFIG_DIR, "components.json"),      DEFAULT_COMPONENT_LIBRARY)
TARGET_STATES      = load_json_if_exists(os.path.join(CONFIG_DIR, "target_states.json"),   DEFAULT_TARGET_STATES)
DOMAIN_KNOWLEDGE   = load_json_if_exists(os.path.join(CONFIG_DIR, "domain_knowledge.json"),DEFAULT_DOMAIN_KNOWLEDGE)

print(f"Components loaded  : {len(COMPONENT_LIBRARY)}")
print(f"Target states      : {list(TARGET_STATES.keys())}")
print(f"Domain keywords    : {len(DOMAIN_KNOWLEDGE['domain_keywords'])}")

# ======================================================================
# CELL 4
# ======================================================================
# ── PDF ingestion ──────────────────────────────────────────────────────────
def find_all_pdfs(root: str) -> List[str]:
    return sorted(set(glob.glob(os.path.join(root, "**", "*.pdf"), recursive=True)))

def read_pdf_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        print(f"Failed reading {pdf_path}: {e}")
        return ""

# (PDF ingestion runs at startup via build_retriever())
pdf_texts: Dict[str, str] = {}

# ======================================================================
# CELL 5
# ======================================================================
# ── Text chunking ──────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    return re.sub(r"\s+", " ", text).strip()

def chunk_text(text: str, chunk_size: int, overlap: int, min_chunk_chars: int) -> List[str]:
    text = clean_text(text)
    chunks, start = [], 0
    while start < len(text):
        end   = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if len(chunk) >= min_chunk_chars:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += max(1, chunk_size - overlap)
    return chunks

# (documents built at startup via build_retriever())
documents: List[Dict[str, Any]] = []

# ======================================================================
# CELL 6
# ======================================================================
# ── TF-IDF Retriever ───────────────────────────────────────────────────────
class TfidfRetriever:
    def __init__(self, docs: List[Dict[str, Any]], max_features: int = 30000):
        self.docs = docs
        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), max_features=max_features
        )
        self.doc_matrix = None
        if docs:
            self.doc_matrix = self.vectorizer.fit_transform([d["text"] for d in docs])

    def is_ready(self) -> bool:
        return self.doc_matrix is not None and len(self.docs) > 0

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.is_ready() or not (query := clean_text(query)):
            return []
        scores = cosine_similarity(self.vectorizer.transform([query]), self.doc_matrix).flatten()
        return [
            {**self.docs[i], "score": float(scores[i])}
            for i in np.argsort(scores)[::-1][:top_k]
        ]

# (retriever built at startup)
retriever: "TfidfRetriever" = None  # type: ignore

# ======================================================================
# CELL 7
# ======================================================================
# ── Query analysis helpers ─────────────────────────────────────────────────
STOPWORDS_LIGHT = {
    "a","an","the","is","are","of","for","to","in","on","with",
    "what","how","why","explain","tell","me","about","difference",
    "between","construct","build","design","generate","create","state",
}

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()

def tokenize_text(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_+]+", text.lower())

def keyword_overlap_score(query: str, keywords: List[str]) -> float:
    q = normalize_text(query)
    return sum(1 for kw in keywords if kw.lower() in q) / max(len(keywords), 1)


def detect_target_state(query: str) -> Optional[str]:
    """Return the best-matching target state key, or None."""
    q = normalize_text(query)

    # --- explicit family resolution (most specific first) ---
    for state_key in TARGET_STATES:
        meta = TARGET_STATES[state_key]
        for alias in meta.get("aliases", []):
            if alias.lower() in q:
                return state_key

    # --- generic GHZ → default to ghz_3 ---
    if re.search(r"\bghz\b", q):
        if re.search(r"\bghz[\s_-]*4\b|four[\s-]*qubit[\s-]*ghz", q) and "ghz_4" in TARGET_STATES:
            return "ghz_4"
        return "ghz_3" if "ghz_3" in TARGET_STATES else None

    # --- W state ---
    if re.search(r"\bw[\s_-]*state\b|\bw[\s_-]*3\b", q):
        return "w_3" if "w_3" in TARGET_STATES else None

    # --- Bell ---
    if re.search(r"\bbell\b|\bphi[\s_]*[+]\b", q):
        return "bell_phi_plus" if "bell_phi_plus" in TARGET_STATES else None

    # --- explicit family patterns for new states ---
    if re.search(r"\bdicke\b", q):
        if re.search(r"\b(4|four)\b.*\b(2|two)\b|\b(2|two).*\b(4|four)\b", q):
            if "dicke_4_2" in TARGET_STATES: return "dicke_4_2"
        if "dicke_4_1" in TARGET_STATES: return "dicke_4_1"

    if re.search(r"\bcluster\b|\bgraph state\b", q):
        if re.search(r"\bsquare\b|\b2d\b", q) and "cluster_square_4" in TARGET_STATES:
            return "cluster_square_4"
        if re.search(r"\b4\b|\bfour\b", q) and "cluster_linear_4" in TARGET_STATES:
            return "cluster_linear_4"
        if "cluster_linear_3" in TARGET_STATES: return "cluster_linear_3"

    if re.search(r"\bstar\b", q):
        if re.search(r"\b4\b|\bfour\b", q) and "star_4" in TARGET_STATES: return "star_4"
        if "star_3" in TARGET_STATES: return "star_3"

    if re.search(r"\bring\b|\bcycle\b", q):
        if "ring_4" in TARGET_STATES: return "ring_4"

    if re.search(r"\bw[\s_-]*4\b|four[\s-]*qubit[\s-]*w\b", q):
        if "w_4" in TARGET_STATES: return "w_4"

    if re.search(r"\bpsi[\s_-]*minus\b|\bpsi-\b|\bsinglet\b", q):
        if "bell_psi_minus" in TARGET_STATES: return "bell_psi_minus"
    if re.search(r"\bpsi[\s_-]*plus\b|psi\+", q):
        if "bell_psi_plus" in TARGET_STATES: return "bell_psi_plus"
    if re.search(r"\bphi[\s_-]*minus\b|phi-", q):
        if "bell_phi_minus" in TARGET_STATES: return "bell_phi_minus"

    # --- keyword scoring fallback (lowered threshold) ---
    best, best_score = None, 0.0
    for state_key, meta in TARGET_STATES.items():
        score = keyword_overlap_score(q, meta.get("keywords", []) + meta.get("aliases", []))
        if score > best_score:
            best_score, best = score, state_key
    return best if best_score >= 0.10 else None


def classify_query_intent(query: str) -> str:
    """
    Returns one of: design_target_state | explain_component | retrieval_based_qa |
                    general_question | unknown
    """
    q = normalize_text(query)
    detected_target = detect_target_state(query)

    design_verbs = DOMAIN_KNOWLEDGE.get("design_intents", [])
    qa_phrases   = DOMAIN_KNOWLEDGE.get("qa_intents", [])

    if any(v in q for v in design_verbs) and detected_target:
        return "design_target_state"

    if any(comp.lower() in q for comp in COMPONENT_LIBRARY) and any(p in q for p in qa_phrases):
        return "explain_component"

    if detected_target and any(kw in q for kw in DOMAIN_KNOWLEDGE["domain_keywords"]):
        return "design_target_state"

    if any(p in q for p in qa_phrases):
        # Could be domain QA or a general question — we handle both
        domain_hit = any(kw in q for kw in DOMAIN_KNOWLEDGE["domain_keywords"])
        return "retrieval_based_qa" if domain_hit else "general_question"

    return "general_question"  # default: try to answer anyway


def is_query_in_scope(query: str) -> Dict[str, Any]:
    """
    Every query is handled.
    Domain queries get RAG + GA design; general questions get fallback.
    Nonsensical queries containing a state keyword (e.g. "prime minister ghz")
    are routed to general_qa instead of design_generation.
    """
    q = clean_text(query)
    if not q:
        return {"in_scope": False, "reason": "Empty query.", "detected_target": None}

    detected_target   = detect_target_state(q)
    domain_kw_score   = keyword_overlap_score(q, DOMAIN_KNOWLEDGE["domain_keywords"])
    top_hits          = retriever.search(q, top_k=3) if retriever.is_ready() else []
    top_ret_score     = top_hits[0]["score"] if top_hits else 0.0
    design_verbs      = DOMAIN_KNOWLEDGE.get("design_intents", [])
    has_design_intent = any(v in q.lower() for v in design_verbs)

    is_domain = (
        domain_kw_score >= 0.02 or
        top_ret_score   >= CONFIG["scope_threshold"] or
        detected_target is not None or
        any(comp.lower() in q.lower() for comp in COMPONENT_LIBRARY)
    )

    # If a state was detected but no design intent and query is mostly non-domain
    # (e.g. "prime minister ghz"), downgrade to general_qa
    if detected_target is not None and not has_design_intent:
        non_domain = [
            t for t in q.lower().split()
            if t not in STOPWORDS_LIGHT
            and t not in DOMAIN_KNOWLEDGE["domain_keywords"]
            and not any(t in alias for alias in
                        TARGET_STATES.get(detected_target, {}).get("aliases", []))
        ]
        domain_tok = [
            t for t in q.lower().split()
            if t in DOMAIN_KNOWLEDGE["domain_keywords"]
        ]
        if len(non_domain) > 1.5 * max(len(domain_tok), 1):
            detected_target = None
            is_domain = False

    return {
        "in_scope":             True,
        "is_domain":            is_domain,
        "reason":               "Domain query." if is_domain else "General question.",
        "domain_keyword_score": domain_kw_score,
        "top_retrieval_score":  top_ret_score,
        "detected_target":      detected_target,
    }


    detected_target  = detect_target_state(q)
    domain_kw_score  = keyword_overlap_score(q, DOMAIN_KNOWLEDGE["domain_keywords"])
    top_hits         = retriever.search(q, top_k=3) if retriever.is_ready() else []
    top_ret_score    = top_hits[0]["score"] if top_hits else 0.0

    is_domain = (
        domain_kw_score >= 0.02 or
        top_ret_score   >= CONFIG["scope_threshold"] or
        detected_target is not None or
        any(comp.lower() in q.lower() for comp in COMPONENT_LIBRARY)
    )

    return {
        "in_scope":            True,          # always handle the query
        "is_domain":           is_domain,
        "reason":              "Domain query." if is_domain else "General question — will answer directly.",
        "domain_keyword_score": domain_kw_score,
        "top_retrieval_score": top_ret_score,
        "detected_target":     detected_target,
    }

print("Query analysis helpers loaded.")

# ======================================================================
# CELL 8
# ======================================================================
# ── RAG retrieval helpers ──────────────────────────────────────────────────
def build_retrieval_query(user_query: str, detected_target: Optional[str] = None) -> str:
    parts = [user_query.strip()]
    if detected_target and detected_target in TARGET_STATES:
        meta = TARGET_STATES[detected_target]
        parts.append(meta["description"])
        parts.extend(meta.get("keywords", []))
    return clean_text(" ".join(parts))

def retrieve_context(user_query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    return retriever.search(user_query, top_k=top_k or CONFIG["top_k_default"])

def extract_hints(contexts: List[Dict[str, Any]], query_text: str = "") -> Dict[str, Any]:
    joined = " ".join(c["text"].lower() for c in contexts) if contexts else ""
    hints = {
        comp_key: any(kw in joined for kw in [
            comp_key.lower(),
            COMPONENT_LIBRARY[comp_key]["purpose"].split()[0].lower()
        ])
        for comp_key in COMPONENT_LIBRARY
    }
    hints["rag_confident"] = bool(contexts and contexts[0]["score"] >= CONFIG["rag_confidence_threshold"])
    hints["query_text"]    = query_text
    # convenience booleans kept for backward compat
    hints["mentions_bell"] = "bell"    in joined
    hints["mentions_ghz"]  = "ghz"     in joined
    hints["mentions_w"]    = "w state" in joined
    return hints

print("RAG helpers loaded.")

# ======================================================================
# CELL 9
# ======================================================================
# ── Component / design dataclasses ────────────────────────────────────────
@dataclass
class Component:
    type:   str
    id:     str
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SetupDesign:
    target_name:      str
    num_qubits:       int
    components:       List[Component]
    connections:      List[Tuple[str, str]]
    postselection:    str
    notes:            List[str]
    retrieved_sources: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_name":      self.target_name,
            "num_qubits":       self.num_qubits,
            "components":       [asdict(c) for c in self.components],
            "connections":      self.connections,
            "postselection":    self.postselection,
            "notes":            self.notes,
            "retrieved_sources":self.retrieved_sources,
        }

def make_component(component_type: str, **params) -> Component:
    return Component(
        type=component_type,
        id=f"{component_type}_{uuid.uuid4().hex[:8]}",
        params=params,
    )

print("Dataclasses loaded.")

# ======================================================================
# CELL 10
# ======================================================================
# ── Query parameter extraction ─────────────────────────────────────────────
def extract_query_parameters(query: str) -> Dict[str, Any]:
    """Extract user-specified experimental parameters from free-text query."""
    q = query.lower()
    params: Dict[str, Any] = {}

    # crystal
    if "bbo" in q: params["crystal"] = "BBO"
    if "ktp" in q: params["crystal"] = "KTP"
    if "ppktp" in q: params["crystal"] = "PPKTP"

    # SPDC type
    if re.search(r"type[\s-]*ii", q):  params["type"] = "Type-II"
    elif re.search(r"type[\s-]*i", q): params["type"] = "Type-I"

    # pump wavelength
    for pattern in [
        r"pumped\s+(?:with\s+)?(?:a\s+)?(\d+(?:\.\d+)?)\s*nm",
        r"(\d+(?:\.\d+)?)\s*nm\s+laser",
        r"pump wavelength\s*(?:of|=|is)?\s*(\d+(?:\.\d+)?)\s*nm",
    ]:
        m = re.search(pattern, q)
        if m:
            val = float(m.group(1))
            params["wavelength_nm"] = int(val) if val.is_integer() else val
            break

    # output wavelength
    for pattern in [
        r"output wavelength\s*(?:of|=|is)?\s*(\d+(?:\.\d+)?)\s*nm",
        r"produce(?:s|d)?\s+photons?\s+at\s+(\d+(?:\.\d+)?)\s*nm",
    ]:
        m = re.search(pattern, q)
        if m:
            val = float(m.group(1))
            params["output_wavelength_nm"] = int(val) if val.is_integer() else val
            break

    # phase shift (degrees)
    for pattern in [
        r"phase shift(?:er)?\s+(?:of|set\s+at|at|=)?\s*(\d+(?:\.\d+)?)\s*deg",
        r"phase\s+(\d+(?:\.\d+)?)\s*deg",
    ]:
        m = re.search(pattern, q)
        if m:
            deg = float(m.group(1))
            params["phase_deg"] = deg
            params["phase_rad"] = round(math.radians(deg), 6)
            break

    # HWP angle
    m = re.search(r"(?:hwp|half[\s-]*wave plate)\s+(?:at\s+|set\s+at\s+)?(\d+(?:\.\d+)?)\s*deg", q)
    if m: params["hwp_angle_deg"] = float(m.group(1))

    # QWP angle
    m = re.search(r"(?:qwp|quarter[\s-]*wave plate)\s+(?:at\s+|set\s+at\s+)?(\d+(?:\.\d+)?)\s*deg", q)
    if m: params["qwp_angle_deg"] = float(m.group(1))

    # beam splitter ratio
    m = re.search(r"(\d+)\s*:\s*(\d+)\s*(?:bs|beam splitter)", q)
    if not m: m = re.search(r"(?:bs|beam splitter).*?(\d+)\s*:\s*(\d+)", q)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        total = a + b
        if total:
            params["bs_ratio"]       = f"{a}:{b}"
            params["reflectivity"]   = round(a / total, 4)
            params["transmissivity"] = round(b / total, 4)

    # coincidence fold
    m = re.search(r"(\d+)[\s-]*fold coincidence", q)
    if m:
        n = int(m.group(1))
        params["coincidence_fold"] = n
        params["rule"] = f"{n}-fold coincidence"

    # detector basis
    m = re.search(r"\b(h\s*/\s*v|d\s*/\s*a|r\s*/\s*l)\b", q)
    if m: params["basis"] = m.group(1).replace(" ", "").upper()

    return params

print("Parameter extractor loaded.")

# ======================================================================
# CELL 11
# ======================================================================
# ── Component builder & design generator ──────────────────────────────────
def build_component(component_type: str, index: int = 1, **extra_params) -> Component:
    """Create a component with sensible defaults; extra_params override."""
    defaults: Dict[str, Any] = {}

    if component_type == "SPDC":
        defaults = dict(pump="continuous-wave UV", crystal="BBO", type="Type-II",
                        degenerate=True, wavelength_nm=405, output_wavelength_nm=810,
                        output_pair=f"pair_{index}", modes=[f"s{index}", f"i{index}"],
                        entangled_state="polarization-entangled pair")
    elif component_type == "BS":
        defaults = dict(ratio="50:50", reflectivity=0.5, transmissivity=0.5,
                        interference_mode="two-photon fusion")
    elif component_type == "PBS":
        defaults = dict(operation="transmit_H_reflect_V")
    elif component_type == "HWP":
        defaults = dict(angle_deg=22.5, purpose="polarization rotation")
    elif component_type == "QWP":
        defaults = dict(angle_deg=45.0, purpose="phase retardation / basis conversion")
    elif component_type == "PhaseShifter":
        defaults = dict(phase_rad=round(math.pi, 6), phase_deg=180.0, purpose="relative phase tuning")
    elif component_type == "PostSelection":
        fold = max(index, 2)
        defaults = dict(rule=f"{fold}-fold coincidence",
                        accept_condition=f"keep {fold}-photon coincidence events")
    elif component_type == "Heralding":
        defaults = dict(rule="accept run only when herald detector clicks")
    elif component_type == "PNRDetector":
        defaults = dict(mode="coincidence", basis="H/V", efficiency_assumed=0.9)
    elif component_type == "ThresholdDetector":
        defaults = dict(mode="threshold", dark_count_rate=0.0,
                        purpose="detect presence/absence of photons")
    elif component_type == "CrossKerr":
        defaults = dict(phase_shift_rad=round(math.pi, 6),
                        purpose="conditional phase shift via cross-Kerr nonlinearity")
    elif component_type == "VacuumAncilla":
        defaults = dict(state="|0>", purpose="vacuum input mode for interference")

    defaults.update(extra_params)
    return make_component(component_type, **defaults)


def _spdc_params(query_params: Dict[str, Any], index: int, output_state: str = None) -> Dict[str, Any]:
    return dict(
        crystal=query_params.get("crystal", "BBO"),
        type=query_params.get("type", "Type-II"),
        wavelength_nm=query_params.get("wavelength_nm", 405),
        output_wavelength_nm=query_params.get("output_wavelength_nm", 810),
        output_state=output_state or f"Bell pair resource {index}",
    )


def generate_candidate_design(
    target_name: str,
    hints: Dict[str, Any],
    contexts: List[Dict[str, Any]],
    variant_seed: int = 0,
) -> SetupDesign:
    random.seed(42 + variant_seed)
    np.random.seed(42 + variant_seed)

    qp = extract_query_parameters(hints.get("query_text", ""))
    meta = TARGET_STATES[target_name]
    num_qubits = meta["num_qubits"]
    retrieved_sources = sorted({os.path.basename(c["source"]) for c in contexts}) if contexts else []
    notes: List[str] = []

    # ---- Bell ----
    if target_name == "bell_phi_plus":
        spdc = build_component("SPDC", 1, **_spdc_params(qp, 1, output_state="(|HH>+|VV>)/sqrt(2)"))
        ps   = build_component("PhaseShifter", 1,
                               phase_rad=qp.get("phase_rad", round(math.pi, 6)),
                               phase_deg=qp.get("phase_deg", 180.0),
                               purpose="set relative phase for Bell pair")
        components  = [spdc, ps]
        connections = [(spdc.id, ps.id)]
        postselection = "None"
        notes = ["Minimal Bell-state setup: one SPDC source + phase shifter.",
                 "User-specified parameters applied where detected."]

    # ---- GHZ-3 ----
    elif target_name == "ghz_3":
        spdc1 = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2 = build_component("SPDC", 2, **_spdc_params(qp, 2))
        bs    = build_component("BS",   1, ratio=qp.get("bs_ratio", "50:50"),
                                reflectivity=qp.get("reflectivity", 0.5),
                                transmissivity=qp.get("transmissivity", 0.5),
                                purpose="fusion of photons from independent SPDC sources")
        hwp   = build_component("HWP",  1, angle_deg=qp.get("hwp_angle_deg", 22.5))
        post  = build_component("PostSelection", 3,
                                rule=qp.get("rule", "3-fold coincidence"),
                                accept_condition="3-photon coincidence after fusion")
        det   = build_component("PNRDetector", 1,
                                mode=qp.get("mode", "coincidence"),
                                basis=qp.get("basis", "H/V"), channels=3)
        components  = [spdc1, spdc2, bs, hwp, post, det]
        connections = [(spdc1.id, bs.id),(spdc2.id, bs.id),
                       (bs.id, hwp.id),(hwp.id, post.id),(post.id, det.id)]
        postselection = qp.get("rule", "3-fold coincidence after fusion")
        notes = ["GHZ-3 uses two SPDC resources fused at a beam splitter.",
                 "Post-selection on 3-photon coincidence selects the GHZ component."]

    # ---- GHZ-4 ----
    elif target_name == "ghz_4":
        spdc1  = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2  = build_component("SPDC", 2, **_spdc_params(qp, 2))
        bs     = build_component("BS",   1, ratio=qp.get("bs_ratio", "50:50"),
                                 reflectivity=qp.get("reflectivity", 0.5),
                                 transmissivity=qp.get("transmissivity", 0.5))
        hwp    = build_component("HWP",  1, angle_deg=qp.get("hwp_angle_deg", 22.5))
        herald = build_component("Heralding", 1)
        det    = build_component("PNRDetector", 1,
                                 mode=qp.get("mode", "herald"),
                                 basis=qp.get("basis", "H/V"), channels=4)
        components  = [spdc1, spdc2, bs, hwp, herald, det]
        connections = [(spdc1.id, bs.id),(spdc2.id, bs.id),
                       (bs.id, hwp.id),(hwp.id, herald.id),(herald.id, det.id)]
        postselection = "Heralded 4-photon success event"
        notes = ["GHZ-4 uses two SPDC pair resources plus heralded fusion.",
                 "Heralding achieves higher success rates than blind post-selection."]

    # ---- W-3 ----
    elif target_name == "w_3":
        spdc = build_component("SPDC", 1, **_spdc_params(qp, 1, output_state="single pair resource"))
        bs   = build_component("BS",   1, ratio=qp.get("bs_ratio", "50:50"),
                               reflectivity=qp.get("reflectivity", 0.5),
                               transmissivity=qp.get("transmissivity", 0.5),
                               purpose="symmetric splitting")
        qwp  = build_component("QWP",  1, angle_deg=qp.get("qwp_angle_deg", 45.0))
        post = build_component("PostSelection", 3, rule=qp.get("rule", "3-fold coincidence"))
        det  = build_component("PNRDetector", 1,
                               mode=qp.get("mode", "coincidence"),
                               basis=qp.get("basis", "H/V"), channels=3)
        components  = [spdc, bs, qwp, post, det]
        connections = [(spdc.id, bs.id),(bs.id, qwp.id),(qwp.id, post.id),(post.id, det.id)]
        postselection = qp.get("rule", "3-fold coincidence")
        notes = ["W-state generation relies on symmetric superposition via beam splitter.",
                 "Post-selection on exactly-one-photon-per-mode gives the W state."]


    # ---- Bell Phi- ----
    elif target_name == "bell_phi_minus":
        spdc = build_component("SPDC", 1, **_spdc_params(qp, 1, output_state="(|HH>-|VV>)/sqrt(2)"))
        ps   = build_component("PhaseShifter", 1,
                               phase_rad=qp.get("phase_rad", round(math.pi, 6)),
                               phase_deg=qp.get("phase_deg", 180.0),
                               purpose="apply pi phase shift to get Phi-")
        components  = [spdc, ps]
        connections = [(spdc.id, ps.id)]
        postselection = "None"
        notes = ["Bell |Phi-> = SPDC output + pi phase shift on one arm.",
                 "Identical setup to Phi+ but with 180 degree phase applied."]

    # ---- Bell Psi+ ----
    elif target_name == "bell_psi_plus":
        spdc = build_component("SPDC", 1, **_spdc_params(qp, 1, output_state="(|01>+|10>)/sqrt(2)"))
        hwp  = build_component("HWP", 1, angle_deg=qp.get("hwp_angle_deg", 45.0),
                               purpose="flip polarization on signal arm to get anti-correlated pair")
        components  = [spdc, hwp]
        connections = [(spdc.id, hwp.id)]
        postselection = "None"
        notes = ["Bell |Psi+> = SPDC + HWP at 45 degrees on one output mode.",
                 "HWP flips H to V, converting Phi+ into Psi+."]

    # ---- Bell Psi- ----
    elif target_name == "bell_psi_minus":
        spdc = build_component("SPDC", 1, **_spdc_params(qp, 1, output_state="(|01>-|10>)/sqrt(2)"))
        hwp  = build_component("HWP", 1, angle_deg=45.0, purpose="flip polarization on signal arm")
        ps   = build_component("PhaseShifter", 1,
                               phase_rad=qp.get("phase_rad", round(math.pi, 6)),
                               phase_deg=180.0,
                               purpose="apply pi phase to get singlet state Psi-")
        components  = [spdc, hwp, ps]
        connections = [(spdc.id, hwp.id), (hwp.id, ps.id)]
        postselection = "None"
        notes = ["Bell |Psi-> (singlet) = SPDC + HWP at 45 deg + pi phase shift.",
                 "The singlet is the only antisymmetric Bell state."]

    # ---- W-4 ----
    elif target_name == "w_4":
        spdc1 = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2 = build_component("SPDC", 2, **_spdc_params(qp, 2))
        bs1   = build_component("BS", 1, ratio="50:50", reflectivity=0.5, transmissivity=0.5,
                                purpose="first symmetric split")
        bs2   = build_component("BS", 2, ratio="50:50", reflectivity=0.5, transmissivity=0.5,
                                purpose="second symmetric split")
        post  = build_component("PostSelection", 4, rule=qp.get("rule", "4-fold coincidence"))
        det   = build_component("PNRDetector", 1, mode="coincidence",
                                basis=qp.get("basis", "H/V"), channels=4)
        components  = [spdc1, spdc2, bs1, bs2, post, det]
        connections = [(spdc1.id, bs1.id),(spdc2.id, bs1.id),
                       (bs1.id, bs2.id),(bs2.id, post.id),(post.id, det.id)]
        postselection = qp.get("rule", "4-fold single-photon coincidence")
        notes = ["W-4 uses two SPDC sources + cascaded beam splitters for symmetric 4-way superposition.",
                 "Post-select on exactly one photon per output mode."]

    # ---- Linear Cluster-3 ----
    elif target_name == "cluster_linear_3":
        spdc1 = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2 = build_component("SPDC", 2, **_spdc_params(qp, 2))
        hwp1  = build_component("HWP", 1, angle_deg=22.5, purpose="prepare |+> basis for cluster")
        hwp2  = build_component("HWP", 2, angle_deg=22.5, purpose="prepare |+> basis for cluster")
        bs    = build_component("BS", 1, ratio="50:50", purpose="entangling fusion for cluster bond")
        post  = build_component("PostSelection", 3, rule=qp.get("rule", "3-fold coincidence"))
        det   = build_component("PNRDetector", 1, mode="coincidence", channels=3)
        components  = [spdc1, spdc2, hwp1, hwp2, bs, post, det]
        connections = [(spdc1.id, hwp1.id),(spdc2.id, hwp2.id),
                       (hwp1.id, bs.id),(hwp2.id, bs.id),
                       (bs.id, post.id),(post.id, det.id)]
        postselection = "3-fold coincidence after type-II fusion"
        notes = ["Linear cluster-3: prepare |+> states from SPDC, fuse with BS to create cluster bonds.",
                 "Measurement-based QC resource state."]

    # ---- Linear Cluster-4 ----
    elif target_name == "cluster_linear_4":
        spdc1  = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2  = build_component("SPDC", 2, **_spdc_params(qp, 2))
        hwp1   = build_component("HWP", 1, angle_deg=22.5, purpose="|+> basis preparation")
        hwp2   = build_component("HWP", 2, angle_deg=22.5, purpose="|+> basis preparation")
        bs1    = build_component("BS", 1, ratio="50:50", purpose="first cluster fusion")
        bs2    = build_component("BS", 2, ratio="50:50", purpose="second cluster fusion")
        herald = build_component("Heralding", 1)
        det    = build_component("PNRDetector", 1, mode="coincidence", channels=4)
        components  = [spdc1, spdc2, hwp1, hwp2, bs1, bs2, herald, det]
        connections = [(spdc1.id, hwp1.id),(spdc2.id, hwp2.id),
                       (hwp1.id, bs1.id),(hwp2.id, bs1.id),
                       (bs1.id, bs2.id),(bs2.id, herald.id),(herald.id, det.id)]
        postselection = "Heralded 4-fold coincidence"
        notes = ["Linear cluster-4: two SPDC sources fused twice to form a 4-node linear chain.",
                 "Heralding improves success probability over blind post-selection."]

    # ---- Square Cluster-4 ----
    elif target_name == "cluster_square_4":
        spdc1  = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2  = build_component("SPDC", 2, **_spdc_params(qp, 2))
        hwp1   = build_component("HWP", 1, angle_deg=22.5, purpose="|+> basis prep")
        hwp2   = build_component("HWP", 2, angle_deg=22.5, purpose="|+> basis prep")
        bs1    = build_component("BS", 1, ratio="50:50", purpose="horizontal cluster bond")
        bs2    = build_component("BS", 2, ratio="50:50", purpose="vertical cluster bond")
        pbs    = build_component("PBS", 1, purpose="polarization-based CZ-equivalent fusion")
        herald = build_component("Heralding", 1)
        det    = build_component("PNRDetector", 1, mode="coincidence", channels=4)
        components  = [spdc1, spdc2, hwp1, hwp2, bs1, bs2, pbs, herald, det]
        connections = [(spdc1.id, hwp1.id),(spdc2.id, hwp2.id),
                       (hwp1.id, bs1.id),(hwp2.id, bs2.id),
                       (bs1.id, pbs.id),(bs2.id, pbs.id),
                       (pbs.id, herald.id),(herald.id, det.id)]
        postselection = "Heralded 4-fold coincidence with PBS fusion"
        notes = ["Square cluster-4: 2D graph state with 4 nodes in a ring topology.",
                 "PBS used for CZ-equivalent entangling operation between horizontal and vertical arms."]

    # ---- Dicke D(4,1) ----
    elif target_name == "dicke_4_1":
        spdc1 = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2 = build_component("SPDC", 2, **_spdc_params(qp, 2))
        bs1   = build_component("BS", 1, ratio="50:50", purpose="symmetric splitting for Dicke state")
        bs2   = build_component("BS", 2, ratio="50:50", purpose="second symmetric split")
        bs3   = build_component("BS", 3, ratio="50:50", purpose="third symmetric split")
        post  = build_component("PostSelection", 4, rule="4-fold coincidence, exactly 1 photon per mode")
        det   = build_component("PNRDetector", 1, mode="coincidence", channels=4)
        components  = [spdc1, spdc2, bs1, bs2, bs3, post, det]
        connections = [(spdc1.id, bs1.id),(spdc2.id, bs1.id),
                       (bs1.id, bs2.id),(bs2.id, bs3.id),
                       (bs3.id, post.id),(post.id, det.id)]
        postselection = "4-fold coincidence with exactly 1 excitation"
        notes = ["Dicke D(4,1): symmetric superposition of all states with exactly 1 photon in 4 modes.",
                 "Cascaded beam splitters create equal-weight superposition; post-select on 1-photon subspace."]

    # ---- Dicke D(4,2) ----
    elif target_name == "dicke_4_2":
        spdc1  = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2  = build_component("SPDC", 2, **_spdc_params(qp, 2))
        bs1    = build_component("BS", 1, ratio="50:50", purpose="balanced splitting")
        bs2    = build_component("BS", 2, ratio="50:50", purpose="balanced splitting")
        hwp    = build_component("HWP", 1, angle_deg=22.5, purpose="polarization symmetrization")
        herald = build_component("Heralding", 1)
        post   = build_component("PostSelection", 4, rule="4-fold coincidence, exactly 2 photons")
        det    = build_component("PNRDetector", 1, mode="coincidence", channels=4)
        components  = [spdc1, spdc2, bs1, bs2, hwp, herald, post, det]
        connections = [(spdc1.id, bs1.id),(spdc2.id, bs2.id),
                       (bs1.id, hwp.id),(bs2.id, hwp.id),
                       (hwp.id, herald.id),(herald.id, post.id),(post.id, det.id)]
        postselection = "4-fold coincidence with exactly 2 excitations"
        notes = ["Dicke D(4,2): symmetric superposition of all 2-photon states in 4 modes.",
                 "Post-select on exactly 2 photons total across all output modes."]

    # ---- Star-3 ----
    elif target_name == "star_3":
        spdc1 = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2 = build_component("SPDC", 2, **_spdc_params(qp, 2))
        hwp1  = build_component("HWP", 1, angle_deg=22.5, purpose="|+> basis for leaf qubit 1")
        hwp2  = build_component("HWP", 2, angle_deg=22.5, purpose="|+> basis for leaf qubit 2")
        pbs   = build_component("PBS", 1, purpose="CZ-equivalent fusion on central qubit")
        post  = build_component("PostSelection", 3, rule=qp.get("rule", "3-fold coincidence"))
        det   = build_component("PNRDetector", 1, mode="coincidence", channels=3)
        components  = [spdc1, spdc2, hwp1, hwp2, pbs, post, det]
        connections = [(spdc1.id, hwp1.id),(spdc2.id, hwp2.id),
                       (hwp1.id, pbs.id),(hwp2.id, pbs.id),
                       (pbs.id, post.id),(post.id, det.id)]
        postselection = "3-fold coincidence after PBS fusion"
        notes = ["Star-3 graph state: 1 central qubit entangled with 2 leaf qubits.",
                 "PBS performs CZ-equivalent operation; leaves prepared in |+> via HWP."]

    # ---- Star-4 ----
    elif target_name == "star_4":
        spdc1  = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2  = build_component("SPDC", 2, **_spdc_params(qp, 2))
        hwp1   = build_component("HWP", 1, angle_deg=22.5, purpose="|+> for leaf 1")
        hwp2   = build_component("HWP", 2, angle_deg=22.5, purpose="|+> for leaf 2")
        hwp3   = build_component("HWP", 3, angle_deg=22.5, purpose="|+> for leaf 3")
        pbs1   = build_component("PBS", 1, purpose="first CZ fusion on central qubit")
        pbs2   = build_component("PBS", 2, purpose="second CZ fusion on central qubit")
        herald = build_component("Heralding", 1)
        det    = build_component("PNRDetector", 1, mode="coincidence", channels=4)
        components  = [spdc1, spdc2, hwp1, hwp2, hwp3, pbs1, pbs2, herald, det]
        connections = [(spdc1.id, hwp1.id),(spdc2.id, hwp2.id),
                       (hwp1.id, pbs1.id),(hwp2.id, pbs1.id),
                       (hwp3.id, pbs2.id),(pbs1.id, pbs2.id),
                       (pbs2.id, herald.id),(herald.id, det.id)]
        postselection = "Heralded 4-fold coincidence"
        notes = ["Star-4 graph state: 1 central qubit connected to 3 leaf qubits.",
                 "Two sequential PBS fusions build up the star topology."]

    # ---- Ring-4 ----
    elif target_name == "ring_4":
        spdc1  = build_component("SPDC", 1, **_spdc_params(qp, 1))
        spdc2  = build_component("SPDC", 2, **_spdc_params(qp, 2))
        hwp1   = build_component("HWP", 1, angle_deg=22.5, purpose="|+> basis for node 1")
        hwp2   = build_component("HWP", 2, angle_deg=22.5, purpose="|+> basis for node 2")
        bs1    = build_component("BS", 1, ratio="50:50", purpose="CZ-equiv fusion bond 1-2")
        bs2    = build_component("BS", 2, ratio="50:50", purpose="CZ-equiv fusion bond 3-4")
        pbs    = build_component("PBS", 1, purpose="closing the ring: bond 4-1")
        herald = build_component("Heralding", 1)
        det    = build_component("PNRDetector", 1, mode="coincidence", channels=4)
        components  = [spdc1, spdc2, hwp1, hwp2, bs1, bs2, pbs, herald, det]
        connections = [(spdc1.id, hwp1.id),(spdc2.id, hwp2.id),
                       (hwp1.id, bs1.id),(hwp2.id, bs2.id),
                       (bs1.id, pbs.id),(bs2.id, pbs.id),
                       (pbs.id, herald.id),(herald.id, det.id)]
        postselection = "Heralded 4-fold coincidence after ring closure"
        notes = ["Ring-4 graph state: 4 qubits connected in a cycle.",
                 "BS fusions create adjacent bonds; PBS closes the ring topology."]

    # ---- generic fallback ----
    else:
        num_spdc_needed = max(1, math.ceil(num_qubits / 2))
        spdcs = [build_component("SPDC", i+1, **_spdc_params(qp, i+1)) for i in range(num_spdc_needed)]
        bs    = build_component("BS", 1)
        post  = build_component("PostSelection", num_qubits)
        det   = build_component("PNRDetector", 1, channels=num_qubits)
        components  = spdcs + [bs, post, det]
        connections = [(spdcs[0].id, bs.id)] + \
                      [(s.id, bs.id) for s in spdcs[1:]] + \
                      [(bs.id, post.id), (post.id, det.id)]
        postselection = f"{num_qubits}-fold coincidence"
        notes = [f"Generic {num_qubits}-qubit fallback template.",
                 "No state-specific template available; using heuristic layout."]

    if qp:
        notes.append(f"User-specified parameters applied: {', '.join(qp.keys())}")

    return SetupDesign(
        target_name=target_name,
        num_qubits=num_qubits,
        components=components,
        connections=connections,
        postselection=postselection,
        notes=notes,
        retrieved_sources=retrieved_sources,
    )

print("Design generator loaded.")

# ======================================================================
# CELL 12
# ======================================================================
# ── Physics engine: QuTiP state vectors + real fidelity F(ρ_target, ρ_out) ─
try:
    import qutip as qt
    QUTIP_AVAILABLE = True
    print("✅ QuTiP available — real quantum fidelity enabled")
except ImportError:
    QUTIP_AVAILABLE = False
    print("⚠️  QuTiP not found — falling back to heuristic fidelity")


# ── Optical component unitary matrices (pure numpy, no extra deps) ─────────
def U_BS(r: float = 0.5) -> "np.ndarray":
    """Beam splitter. r=reflectivity (0.5 = 50:50)."""
    t = np.sqrt(1 - r)
    rv = np.sqrt(r)
    return np.array([[t,      1j*rv],
                     [1j*rv,  t    ]], dtype=complex)

def U_HWP(theta_deg: float) -> "np.ndarray":
    """Half-wave plate at angle theta (degrees)."""
    t = np.radians(theta_deg)
    c, s = np.cos(2*t), np.sin(2*t)
    return np.array([[ c,  s],
                     [ s, -c]], dtype=complex)

def U_QWP(theta_deg: float) -> "np.ndarray":
    """Quarter-wave plate at angle theta (degrees)."""
    t = np.radians(theta_deg)
    c, s = np.cos(2*t), np.sin(2*t)
    return (1/np.sqrt(2)) * np.array([[1 - 1j*c,   -1j*s  ],
                                       [  -1j*s,  1 + 1j*c]], dtype=complex)

def U_PS(phi_rad: float) -> "np.ndarray":
    """Phase shifter."""
    return np.array([[1,                  0],
                     [0, np.exp(1j*phi_rad)]], dtype=complex)


# ── Target state density matrices ─────────────────────────────────────────
def _build_target_density_matrices() -> dict:
    if not QUTIP_AVAILABLE:
        return {}
    H = qt.basis(2, 0)   # |H> = |0>
    V = qt.basis(2, 1)   # |V> = |1>

    # ── Bell family ───────────────────────────────────────────────────────
    bell_phi_plus  = (qt.tensor(H,H) + qt.tensor(V,V)).unit()
    bell_phi_minus = (qt.tensor(H,H) - qt.tensor(V,V)).unit()
    bell_psi_plus  = (qt.tensor(H,V) + qt.tensor(V,H)).unit()
    bell_psi_minus = (qt.tensor(H,V) - qt.tensor(V,H)).unit()

    # ── GHZ family ────────────────────────────────────────────────────────
    ghz3 = (qt.tensor(H,H,H) + qt.tensor(V,V,V)).unit()
    ghz4 = (qt.tensor(H,H,H,H) + qt.tensor(V,V,V,V)).unit()

    # ── W family ──────────────────────────────────────────────────────────
    w3 = (qt.tensor(H,V,V) + qt.tensor(V,H,V) + qt.tensor(V,V,H)).unit()
    w4 = (qt.tensor(H,V,V,V) + qt.tensor(V,H,V,V) +
          qt.tensor(V,V,H,V) + qt.tensor(V,V,V,H)).unit()

    # ── Cluster states (graph states via CZ on |+>^n) ─────────────────────
    plus = (H + V).unit()   # |+> = (|H>+|V>)/sqrt(2)
    # Linear cluster-3: CZ on qubits (0,1) and (1,2)
    c3 = qt.tensor(plus, plus, plus)
    CZ = qt.Qobj([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,-1]])
    CZ.dims = [[2,2],[2,2]]
    # Apply CZ(0,1): embed in 3-qubit space
    CZ01_3 = qt.tensor(CZ, qt.qeye(2)); CZ01_3.dims = [[2,2,2],[2,2,2]]
    CZ12_3 = qt.tensor(qt.qeye(2), CZ); CZ12_3.dims = [[2,2,2],[2,2,2]]
    cluster3_ket = CZ12_3 * CZ01_3 * c3
    # Linear cluster-4
    c4 = qt.tensor(plus, plus, plus, plus)
    CZ01_4 = qt.tensor(CZ, qt.qeye(2), qt.qeye(2)); CZ01_4.dims = [[2,2,2,2],[2,2,2,2]]
    CZ12_4 = qt.tensor(qt.qeye(2), CZ, qt.qeye(2)); CZ12_4.dims = [[2,2,2,2],[2,2,2,2]]
    CZ23_4 = qt.tensor(qt.qeye(2), qt.qeye(2), CZ); CZ23_4.dims = [[2,2,2,2],[2,2,2,2]]
    cluster4_ket = CZ23_4 * CZ12_4 * CZ01_4 * c4
    # Square cluster-4: CZ on (0,1),(1,2),(2,3),(3,0)
    CZ30_4 = qt.tensor(CZ, qt.qeye(2), qt.qeye(2)); CZ30_4.dims = [[2,2,2,2],[2,2,2,2]]  # approx
    cluster_sq4_ket = CZ30_4 * CZ23_4 * CZ12_4 * CZ01_4 * c4

    # ── Dicke states ──────────────────────────────────────────────────────
    # D(4,1): all states with exactly 1 excitation in 4 qubits
    dicke41 = (qt.tensor(H,V,V,V) + qt.tensor(V,H,V,V) +
               qt.tensor(V,V,H,V) + qt.tensor(V,V,V,H)).unit()
    # D(4,2): all states with exactly 2 excitations in 4 qubits
    from itertools import combinations
    basis4 = [H, V]
    def _state(exc_positions, n=4):
        modes = [V]*n
        for p in exc_positions:
            modes[p] = H
        return qt.tensor(*modes)
    dicke42_terms = [_state(list(c)) for c in combinations(range(4), 2)]
    dicke42 = sum(dicke42_terms).unit()

    # ── Star graph states ─────────────────────────────────────────────────
    # Star-3: central qubit 0 connected to leaves 1,2
    s3 = qt.tensor(plus, plus, plus)
    CZ01_3b = qt.tensor(CZ, qt.qeye(2)); CZ01_3b.dims = [[2,2,2],[2,2,2]]
    CZ02_3  = qt.tensor(qt.Qobj([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,-1]]),qt.qeye(2))
    # Swap qubits 1 and 2 to get CZ(0,2)
    SWAP = qt.Qobj([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]]); SWAP.dims=[[2,2],[2,2]]
    star3_ket = CZ01_3b * CZ12_3 * s3

    # Star-4: central qubit 0 connected to leaves 1,2,3
    s4 = qt.tensor(plus, plus, plus, plus)
    star4_ket = CZ23_4 * CZ12_4 * CZ01_4 * s4

    # Ring-4: cycle 0-1-2-3-0
    ring4_ket = CZ30_4 * CZ23_4 * CZ12_4 * CZ01_4 * c4

    return {
        "bell_phi_plus":    qt.ket2dm(bell_phi_plus),
        "bell_phi_minus":   qt.ket2dm(bell_phi_minus),
        "bell_psi_plus":    qt.ket2dm(bell_psi_plus),
        "bell_psi_minus":   qt.ket2dm(bell_psi_minus),
        "ghz_3":            qt.ket2dm(ghz3),
        "ghz_4":            qt.ket2dm(ghz4),
        "w_3":              qt.ket2dm(w3),
        "w_4":              qt.ket2dm(w4),
        "cluster_linear_3": qt.ket2dm(cluster3_ket),
        "cluster_linear_4": qt.ket2dm(cluster4_ket),
        "cluster_square_4": qt.ket2dm(cluster_sq4_ket),
        "dicke_4_1":        qt.ket2dm(dicke41),
        "dicke_4_2":        qt.ket2dm(dicke42),
        "star_3":           qt.ket2dm(star3_ket),
        "star_4":           qt.ket2dm(star4_ket),
        "ring_4":           qt.ket2dm(ring4_ket),
    }

# (TARGET_DM built at startup)
TARGET_DM: Dict[str, Any] = {}


# ── Simulate the photonic circuit → output density matrix ─────────────────
def simulate_circuit(design: "SetupDesign") -> "Optional[Any]":
    """
    Simulate the photonic circuit.
    Input : tensor product of Bell pairs |Phi+>^n (one per SPDC source)
    Output: QuTiP density matrix rho_out after applying all component unitaries
    """
    if not QUTIP_AVAILABLE:
        return None
    try:
        H = qt.basis(2, 0)
        V = qt.basis(2, 1)
        bell_ket = (qt.tensor(H, H) + qt.tensor(V, V)).unit()

        num_spdc   = sum(1 for c in design.components if c.type == "SPDC")
        num_qubits = int(design.num_qubits)

        if num_spdc == 0:
            return None

        # Build input: tensor product of Bell pairs
        state = bell_ket
        for _ in range(num_spdc - 1):
            state = qt.tensor(state, bell_ket)
        rho = qt.ket2dm(state)
        # Ensure dims are clean Python ints
        n = int(len(rho.dims[0]))
        rho.dims = [[2]*n, [2]*n]

        for comp in design.components:
            p = comp.params
            n = int(len(rho.dims[0]))

            # ── Helper: embed 1-qubit gate U on `mode` into n-qubit space ──
            def _embed1(U_np, mode=0):
                mode = int(mode)
                U_qt = qt.Qobj(U_np)
                U_qt.dims = [[2], [2]]
                ops = [U_qt if i == mode else qt.qeye(2) for i in range(n)]
                full = qt.tensor(ops) if n > 1 else ops[0]
                full.dims = [[2]*n, [2]*n]
                return full

            # ── Helper: embed 2-qubit gate U on modes 0,1 into n-qubit space ──
            def _embed2(U_np):
                U_qt = qt.Qobj(U_np)
                U_qt.dims = [[2, 2], [2, 2]]
                if n == 2:
                    full = U_qt
                elif n > 2:
                    rest = [qt.qeye(2)] * (n - 2)
                    full = qt.tensor([U_qt] + rest)
                else:
                    return None
                full.dims = [[2]*n, [2]*n]
                return full

            if comp.type == "HWP":
                U = _embed1(U_HWP(float(p.get("angle_deg", 22.5))), mode=0)
                rho = U * rho * U.dag()

            elif comp.type == "QWP":
                U = _embed1(U_QWP(float(p.get("angle_deg", 45.0))), mode=0)
                rho = U * rho * U.dag()

            elif comp.type == "PhaseShifter":
                U = _embed1(U_PS(float(p.get("phase_rad", np.pi))), mode=0)
                rho = U * rho * U.dag()

            elif comp.type == "BS" and n >= 2:
                U = _embed2(U_BS(float(p.get("reflectivity", 0.5))))
                if U is not None:
                    rho = U * rho * U.dag()

            elif comp.type == "PBS" and n >= 2:
                # PBS: transmit H (|0>), reflect V (|1>) — modelled as identity on H subspace
                U = _embed2(np.array([[1,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,1]], dtype=complex))
                if U is not None:
                    rho = U * rho * U.dag()
                    rho_tr = rho.tr()
                    if abs(rho_tr) > 1e-10:
                        rho = rho / rho_tr
                    n = int(len(rho.dims[0]))
                    rho.dims = [[2]*n, [2]*n]

            elif comp.type == "CrossKerr" and n >= 2:
                phi = float(p.get("phase_shift_rad", np.pi))
                cp = np.diag([1.0, 1.0, 1.0, np.exp(1j * phi)]).astype(complex)
                U = _embed2(cp)
                if U is not None:
                    rho = U * rho * U.dag()

            elif comp.type == "VacuumAncilla":
                vac = qt.ket2dm(qt.basis(2, 1))
                rho = qt.tensor(rho, vac)
                n = int(len(rho.dims[0]))
                rho.dims = [[2]*n, [2]*n]

            elif comp.type in ("PostSelection", "Heralding", "ThresholdDetector", "PNRDetector"):
                if n > num_qubits:
                    rho = rho.ptrace(list(range(num_qubits)))
                    n = int(len(rho.dims[0]))
                    rho.dims = [[2]*n, [2]*n]

        # Final trim
        n = int(len(rho.dims[0]))
        if n > num_qubits:
            rho = rho.ptrace(list(range(num_qubits)))
            n = int(len(rho.dims[0]))
            rho.dims = [[2]*n, [2]*n]

        tr = rho.tr()
        if abs(tr) > 1e-10:
            rho = rho / tr
        return rho

    except Exception as e:
        # Silent — don't spam warnings, just return None for heuristic fallback
        return None



# ── Real fidelity: F(ρ_target, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))² ─────
def compute_real_fidelity(design: "SetupDesign") -> "Optional[float]":
    if not QUTIP_AVAILABLE:
        return None
    rho_target = TARGET_DM.get(design.target_name)
    if rho_target is None:
        return None
    rho_out = simulate_circuit(design)
    if rho_out is None:
        return None
    try:
        # qt.fidelity returns sqrt(F), so we square it
        f = float(qt.fidelity(rho_target, rho_out)) ** 2
        return round(max(0.0, min(1.0, f)), 4)
    except Exception as e:
        return None  # silently fall back to heuristic


# ── Evaluator: real fidelity first, heuristic fallback ────────────────────
def evaluate_setup(design: "SetupDesign") -> Dict[str, Any]:
    comp_types     = [c.type for c in design.components]
    num_components = len(comp_types)
    num_spdc       = comp_types.count("SPDC")
    spatial_modes  = sum(COMPONENT_LIBRARY.get(t, {}).get("spatial_modes", 0) for t in comp_types)
    total_cost     = sum(COMPONENT_LIBRARY.get(t, {}).get("cost", 1)          for t in comp_types)
    meta           = TARGET_STATES.get(design.target_name, {})

    # ── Try real fidelity ──────────────────────────────────────────────────
    real_fidelity  = compute_real_fidelity(design)
    fidelity_source = "qutip_simulation" if real_fidelity is not None else "heuristic_estimate"

    if real_fidelity is not None:
        fidelity = real_fidelity
    else:
        base = meta.get("base_fidelity", 0.70)
        rmap = {"PBS":0.03,"BS":0.03,"HWP":0.02,"QWP":0.01,
                "PhaseShifter":0.02,"Heralding":0.03,"PostSelection":0.03,"PNRDetector":0.02}
        rwd = sum(v for k,v in rmap.items() if k in comp_types)
        pen = 0.0
        if num_spdc > CONFIG["max_spdc_supported"]:  pen += 0.2*(num_spdc-CONFIG["max_spdc_supported"])
        if design.num_qubits > CONFIG["max_qubits_supported"]: pen += 0.2*(design.num_qubits-CONFIG["max_qubits_supported"])
        if num_components > 10: pen += 0.02*(num_components-10)
        fidelity = max(0.0, min(0.99, base + rwd - pen))

    # ── Success probability (heuristic) ───────────────────────────────────
    rmap = {"PBS":0.03,"BS":0.03,"HWP":0.02,"QWP":0.01,
            "PhaseShifter":0.02,"Heralding":0.03,"PostSelection":0.03,"PNRDetector":0.02}
    rwd = sum(v for k,v in rmap.items() if k in comp_types)
    pen = 0.0
    if num_spdc > CONFIG["max_spdc_supported"]:  pen += 0.2*(num_spdc-CONFIG["max_spdc_supported"])
    if design.num_qubits > CONFIG["max_qubits_supported"]: pen += 0.2*(design.num_qubits-CONFIG["max_qubits_supported"])
    if num_components > 10: pen += 0.02*(num_components-10)

    success_p    = max(0.0, min(0.99, meta.get("base_success",0.50) + 0.5*rwd - 0.8*pen))
    simplicity   = max(0.0, 1.0 - num_components / 20.0)
    practicality = max(0.0, 1.0 - total_cost / 30.0)
    overall      = 0.45*fidelity + 0.25*success_p + 0.15*simplicity + 0.15*practicality

    return {
        "fidelity_estimate":            round(fidelity,    4),
        "fidelity_source":              fidelity_source,
        "success_probability_estimate": round(success_p,   4),
        "num_components":               num_components,
        "num_spdc":                     num_spdc,
        "spatial_modes":                spatial_modes,
        "total_cost":                   total_cost,
        "simplicity_score":             round(simplicity,  4),
        "practicality_score":           round(practicality,4),
        "overall_score":                round(overall,     4),
    }

print("✅ Physics engine + evaluator loaded.")


# ======================================================================
# CELL 13
# ======================================================================
# ── Genetic Algorithm for autonomous experiment design ─────────────────────
#
# This replaces the naive random-candidate search with a proper evolutionary
# algorithm.  The GA is the core "AI" of the system:
#
#   Chromosome : ordered list of component type strings
#                e.g. ["SPDC", "SPDC", "BS", "HWP", "PostSelection", "PNRDetector"]
#   Fitness    : F(rho_target, rho_out) from QuTiP simulation (real physics)
#                with secondary objectives: fewer SPDCs, fewer total components
#   Operators  : tournament selection, single-point crossover, random mutation
#
# Complexity:  O(pop_size * generations * simulate_circuit)
# Runtime:     ~5-30s depending on qubit count and population size

# ── GA hyper-parameters (tunable via CONFIG / env vars) ───────────────────
GA_CONFIG = {
    "pop_size":         int(os.environ.get("GA_POP_SIZE",    20)),
    "generations":      int(os.environ.get("GA_GENERATIONS", 30)),
    "min_len":          int(os.environ.get("GA_MIN_LEN",      3)),
    "max_len":          int(os.environ.get("GA_MAX_LEN",      9)),
    "mutation_rate":   float(os.environ.get("GA_MUTATION",  0.25)),
    "crossover_rate":  float(os.environ.get("GA_CROSSOVER", 0.60)),
    "elitism":          int(os.environ.get("GA_ELITISM",      2)),
    "tournament_k":     int(os.environ.get("GA_TOURNAMENT",   3)),
    "max_spdc":         int(os.environ.get("GA_MAX_SPDC",     3)),   # PS constraint
    "max_components":   int(os.environ.get("GA_MAX_COMPS",   12)),
}

# Component pool available to the GA — ordered by role
COMP_POOL_SOURCES    = ["SPDC", "SPDC", "SPDC"]           # max 3 per PS rules
COMP_POOL_TRANSFORMS = ["BS", "PBS", "HWP", "QWP", "PhaseShifter", "CrossKerr", "VacuumAncilla"]
COMP_POOL_MEASURE    = ["PostSelection", "Heralding", "ThresholdDetector", "PNRDetector"]
COMP_POOL_ALL        = COMP_POOL_SOURCES + COMP_POOL_TRANSFORMS + COMP_POOL_MEASURE


def _chromosome_to_design(
    chromosome: List[str],
    target_name: str,
    query_params: Dict[str, Any],
    contexts: List[Dict[str, Any]],
) -> SetupDesign:
    """Convert a chromosome (list of component type strings) into a SetupDesign."""
    num_qubits = TARGET_STATES[target_name]["num_qubits"]
    components = []
    spdc_idx = 0
    type_counts: Dict[str, int] = {}

    for ctype in chromosome:
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
        idx = type_counts[ctype]
        if ctype == "SPDC":
            spdc_idx += 1
            comp = build_component("SPDC", spdc_idx, **_spdc_params(query_params, spdc_idx))
        elif ctype == "HWP":
            comp = build_component("HWP", idx,
                                   angle_deg=query_params.get("hwp_angle_deg", 22.5))
        elif ctype == "QWP":
            comp = build_component("QWP", idx,
                                   angle_deg=query_params.get("qwp_angle_deg", 45.0))
        elif ctype == "PhaseShifter":
            comp = build_component("PhaseShifter", idx,
                                   phase_rad=query_params.get("phase_rad", round(math.pi, 6)),
                                   phase_deg=query_params.get("phase_deg", 180.0))
        elif ctype == "BS":
            comp = build_component("BS", idx,
                                   reflectivity=query_params.get("reflectivity", 0.5),
                                   transmissivity=query_params.get("transmissivity", 0.5))
        else:
            comp = build_component(ctype, idx)
        components.append(comp)

    # Build linear connections: each component feeds the next
    connections = [(components[i].id, components[i+1].id)
                   for i in range(len(components) - 1)]

    # Determine post-selection string
    measure_comps = [c for c in components
                     if c.type in ("PostSelection", "Heralding", "ThresholdDetector", "PNRDetector")]
    postselection = (
        measure_comps[0].params.get("rule", f"{num_qubits}-fold coincidence")
        if measure_comps else "None"
    )

    retrieved_sources = sorted({os.path.basename(c["source"]) for c in contexts}) if contexts else []

    return SetupDesign(
        target_name=target_name,
        num_qubits=num_qubits,
        components=components,
        connections=connections,
        postselection=postselection,
        notes=[f"GA-evolved design | chromosome: {chromosome}"],
        retrieved_sources=retrieved_sources,
    )


def _fitness(
    chromosome: List[str],
    target_name: str,
    query_params: Dict[str, Any],
    contexts: List[Dict[str, Any]],
    rho_target,   # QuTiP density matrix or None
) -> float:
    """
    Multi-objective fitness:
      primary  : fidelity F(rho_target, rho_out)  [0..1]
      secondary: penalise excess SPDCs and component count
    """
    # Hard constraint: must have at least 1 SPDC and 1 measurement
    n_spdc = chromosome.count("SPDC")
    has_measure = any(c in chromosome for c in
                      ("PostSelection","Heralding","ThresholdDetector","PNRDetector"))
    if n_spdc == 0 or not has_measure:
        return 0.0
    if n_spdc > GA_CONFIG["max_spdc"]:
        return 0.0

    design = _chromosome_to_design(chromosome, target_name, query_params, contexts)
    metrics = evaluate_setup(design)

    fidelity = metrics["fidelity_estimate"]

    # Soft penalties
    spdc_penalty = max(0, n_spdc - 1) * 0.04          # prefer fewer SPDCs
    comp_penalty = max(0, len(chromosome) - 6) * 0.01  # prefer compact designs

    return max(0.0, fidelity - spdc_penalty - comp_penalty)


def _random_chromosome(num_qubits: int, rng: random.Random) -> List[str]:
    """Generate a random valid chromosome."""
    n_spdc   = rng.randint(1, min(3, max(1, math.ceil(num_qubits / 2))))
    n_xform  = rng.randint(1, 4)
    n_meas   = rng.randint(1, 2)
    sources  = ["SPDC"] * n_spdc
    xforms   = rng.choices(COMP_POOL_TRANSFORMS, k=n_xform)
    measures = rng.choices(COMP_POOL_MEASURE, k=n_meas)
    chrom    = sources + xforms + measures
    rng.shuffle(chrom)
    # Ensure SPDC comes first (physical: source before optics)
    spdcs = [c for c in chrom if c == "SPDC"]
    rest  = [c for c in chrom if c != "SPDC"]
    return spdcs + rest


def _tournament_select(population, fitnesses, k: int, rng: random.Random) -> List[str]:
    """Tournament selection: pick k individuals, return the fittest."""
    contestants = rng.sample(range(len(population)), min(k, len(population)))
    best = max(contestants, key=lambda i: fitnesses[i])
    return population[best][:]


def _crossover(p1: List[str], p2: List[str], rng: random.Random) -> Tuple[List[str], List[str]]:
    """Single-point crossover."""
    if len(p1) < 2 or len(p2) < 2:
        return p1[:], p2[:]
    pt1 = rng.randint(1, len(p1) - 1)
    pt2 = rng.randint(1, len(p2) - 1)
    c1 = p1[:pt1] + p2[pt2:]
    c2 = p2[:pt2] + p1[pt1:]
    return c1, c2


def _mutate(chromosome: List[str], rng: random.Random) -> List[str]:
    """Random mutation: replace, insert, or delete a gene."""
    chrom = chromosome[:]
    op = rng.choice(["replace", "insert", "delete", "swap"])

    if op == "replace" and chrom:
        i = rng.randint(0, len(chrom) - 1)
        chrom[i] = rng.choice(COMP_POOL_ALL)

    elif op == "insert" and len(chrom) < GA_CONFIG["max_components"]:
        i = rng.randint(0, len(chrom))
        chrom.insert(i, rng.choice(COMP_POOL_TRANSFORMS + COMP_POOL_MEASURE))

    elif op == "delete" and len(chrom) > GA_CONFIG["min_len"]:
        i = rng.randint(0, len(chrom) - 1)
        chrom.pop(i)

    elif op == "swap" and len(chrom) >= 2:
        i, j = rng.sample(range(len(chrom)), 2)
        chrom[i], chrom[j] = chrom[j], chrom[i]

    # Always keep SPDCs at the front
    spdcs = [c for c in chrom if c == "SPDC"]
    rest  = [c for c in chrom if c != "SPDC"]
    return spdcs + rest


def genetic_algorithm_search(
    target_name: str,
    user_query:  str,
    contexts:    List[Dict[str, Any]],
    verbose:     bool = True,
) -> Dict[str, Any]:
    """
    Run the genetic algorithm to find the best photonic circuit for target_name.

    Returns the same dict structure as the old search_best_design().
    """
    import time
    t0 = time.time()

    rng = random.Random(42)
    query_params = extract_query_parameters(user_query)
    num_qubits   = TARGET_STATES[target_name]["num_qubits"]
    rho_target   = TARGET_DM.get(target_name) if QUTIP_AVAILABLE else None

    pop_size    = GA_CONFIG["pop_size"]
    generations = GA_CONFIG["generations"]

    # ── Initialise population ──────────────────────────────────────────────
    population = [_random_chromosome(num_qubits, rng) for _ in range(pop_size)]

    best_chromosome = None
    best_fitness    = -1.0
    fitness_history = []

    for gen in range(generations):
        # Evaluate fitness for all individuals
        fitnesses = [
            _fitness(chrom, target_name, query_params, contexts, rho_target)
            for chrom in population
        ]

        gen_best_f = max(fitnesses)
        fitness_history.append(round(gen_best_f, 4))

        gen_best_i = fitnesses.index(gen_best_f)
        if gen_best_f > best_fitness:
            best_fitness    = gen_best_f
            best_chromosome = population[gen_best_i][:]

        if verbose and (gen % 10 == 0 or gen == generations - 1):
            print(f"  Gen {gen+1:3d}/{generations} | best_fitness={gen_best_f:.4f} "
                  f"| chromosome={population[gen_best_i]}")

        # ── Build next generation ──────────────────────────────────────────
        # Elitism: carry top individuals unchanged
        elite_idx = sorted(range(pop_size), key=lambda i: fitnesses[i], reverse=True)
        new_pop = [population[i][:] for i in elite_idx[:GA_CONFIG["elitism"]]]

        while len(new_pop) < pop_size:
            p1 = _tournament_select(population, fitnesses, GA_CONFIG["tournament_k"], rng)
            p2 = _tournament_select(population, fitnesses, GA_CONFIG["tournament_k"], rng)

            if rng.random() < GA_CONFIG["crossover_rate"]:
                c1, c2 = _crossover(p1, p2, rng)
            else:
                c1, c2 = p1[:], p2[:]

            for child in (c1, c2):
                if rng.random() < GA_CONFIG["mutation_rate"]:
                    child = _mutate(child, rng)
                # Enforce SPDC constraint
                while child.count("SPDC") > GA_CONFIG["max_spdc"]:
                    i = len(child) - 1 - child[::-1].index("SPDC")
                    child.pop(i)
                if child:
                    new_pop.append(child)

        population = new_pop[:pop_size]

    # ── Build final best design ────────────────────────────────────────────
    if best_chromosome is None:
        best_chromosome = population[0]

    best_design  = _chromosome_to_design(best_chromosome, target_name, query_params, contexts)
    best_metrics = evaluate_setup(best_design)
    elapsed      = round(time.time() - t0, 2)

    best_metrics["ga_generations"]     = generations
    best_metrics["ga_population_size"] = pop_size
    best_metrics["ga_runtime_sec"]     = elapsed
    best_metrics["ga_fitness_history"] = fitness_history
    best_metrics["ga_best_chromosome"] = best_chromosome

    print(f"\n✅ GA complete | {generations} gen x {pop_size} pop | "
          f"best_fitness={best_fitness:.4f} | runtime={elapsed}s")

    return {
        "design":   best_design,
        "metrics":  best_metrics,
        "contexts": contexts,
        "hints":    extract_hints(contexts, query_text=user_query),
    }


def search_best_design(
    target_name: str,
    user_query:  str,
    n_candidates: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Main entry point for design search.
    Uses the Genetic Algorithm as primary searcher.
    Falls back to random candidate search if GA fails.
    """
    retrieval_query = build_retrieval_query(user_query, detected_target=target_name)
    contexts        = retrieve_context(retrieval_query, top_k=CONFIG["top_k_default"])

    try:
        return genetic_algorithm_search(target_name, user_query, contexts, verbose=True)
    except Exception as e:
        print(f"  ⚠️  GA failed ({e}), falling back to random search")
        # Fallback: random candidates
        hints = extract_hints(contexts, query_text=user_query)
        candidates = []
        n = n_candidates or CONFIG["candidate_count"]
        for v in range(n):
            design  = generate_candidate_design(target_name, hints, contexts, variant_seed=v)
            metrics = evaluate_setup(design)
            candidates.append({"design": design, "metrics": metrics,
                                "contexts": contexts, "hints": hints})
        return max(candidates, key=lambda x: x["metrics"]["overall_score"])


print("✅ Genetic Algorithm + design search loaded.")
print(f"   GA config: {GA_CONFIG}")


# ======================================================================
# CELL 14
# ======================================================================
# ── Domain Q&A + General fallback answerer ─────────────────────────────────
def answer_domain_question(query: str, contexts: List[Dict[str, Any]]) -> str:
    """Answer domain (quantum optics) questions using library knowledge + RAG context."""
    q = normalize_text(query)

    # Component explanation — driven by library, not hardcoded strings
    for comp_name, comp_meta in COMPONENT_LIBRARY.items():
        if comp_name.lower() in q:
            return f"{comp_name}: {comp_meta['purpose']}"

    # HWP vs QWP comparison
    if "difference" in q and "hwp" in q and "qwp" in q:
        hwp_purpose = COMPONENT_LIBRARY.get("HWP", {}).get("purpose", "polarization rotation")
        qwp_purpose = COMPONENT_LIBRARY.get("QWP", {}).get("purpose", "phase retardation")
        return (
            f"HWP ({hwp_purpose}) rotates the polarization state by twice the plate angle, "
            f"converting |H> to |V> at 45°. "
            f"QWP ({qwp_purpose}) introduces a 90° phase delay, converting linear to "
            "circular polarization and vice versa."
        )

    # Target-state descriptions — driven by TARGET_STATES config
    for state_key, meta in TARGET_STATES.items():
        for alias in meta.get("aliases", []):
            if alias.lower() in q:
                return (
                    f"{meta['description']}. "
                    f"Key components used: {', '.join(meta.get('keywords', []))[:200]}."
                )

    # RAG context
    if contexts and contexts[0]["score"] >= CONFIG["rag_confidence_threshold"]:
        preview = contexts[0]["text"][:600]
        source  = os.path.basename(contexts[0]["source"])
        return f"From the research papers ({source}):\n\n{preview}\n\n[...see full paper for more details]"

    if contexts:
        return (
            "I found loosely related material in the papers, but confidence is low.\n"
            f"Best match ({os.path.basename(contexts[0]['source'])}, "
            f"score={contexts[0]['score']:.3f}):\n{contexts[0]['text'][:400]}"
        )

    return (
        "The question is within quantum optics / photonic experiment design, "
        "but no strong supporting evidence was found in the uploaded papers. "
        "Try asking about a specific state (Bell, GHZ, W) or component (SPDC, BS, HWP, QWP, PBS)."
    )


def answer_general_question(query: str) -> str:
    """
    Handles questions outside the quantum optics domain.
    Provides a direct, factual answer from built-in knowledge.
    """
    q = normalize_text(query)

    # ── Physics / science ──
    if re.search(r"speed of light", q):
        return "The speed of light in vacuum is approximately 299,792,458 m/s (≈ 3×10⁸ m/s)."

    if re.search(r"planck.?s constant|planck constant", q):
        return "Planck's constant h ≈ 6.626×10⁻³⁴ J·s.  The reduced form ℏ = h/(2π) ≈ 1.055×10⁻³⁴ J·s."

    if re.search(r"schrodinger.?s? equation|schrodinger equation", q):
        return (
            "The time-dependent Schrödinger equation is: iℏ ∂ψ/∂t = Ĥψ, "
            "where Ĥ is the Hamiltonian operator and ψ is the quantum state (wave function)."
        )

    if re.search(r"\beinstein\b|e\s*=\s*mc2|mass.energy", q):
        return "Einstein's mass-energy equivalence: E = mc², where c is the speed of light in vacuum."

    if re.search(r"heisenberg uncertainty|uncertainty principle", q):
        return "Heisenberg's uncertainty principle: Δx·Δp ≥ ℏ/2. Position and momentum cannot both be known exactly."

    if re.search(r"what is (a )?qubit", q):
        return (
            "A qubit (quantum bit) is the basic unit of quantum information. "
            "Unlike a classical bit (0 or 1), a qubit can exist in a superposition: α|0⟩ + β|1⟩, "
            "where |α|² + |β|² = 1."
        )

    if re.search(r"what is (quantum )?entanglement", q):
        return (
            "Quantum entanglement is a phenomenon where two or more particles share a quantum state "
            "such that measuring one instantly determines the state of the other, regardless of distance. "
            "It is a key resource in quantum communication and quantum computing."
        )

    if re.search(r"what is superposition", q):
        return (
            "Quantum superposition means a quantum system can exist in multiple states simultaneously "
            "until measured. A qubit in superposition is written as α|0⟩ + β|1⟩."
        )

    if re.search(r"what is decoherence", q):
        return (
            "Decoherence is the process by which a quantum system loses its quantum properties "
            "(superposition, entanglement) due to interaction with the environment, "
            "effectively becoming classical."
        )

    if re.search(r"what is (a )?photon", q):
        return (
            "A photon is the elementary particle of light and all other electromagnetic radiation. "
            "It carries energy E = hf (h = Planck's constant, f = frequency) and has zero rest mass."
        )

    # ── Math ──
    if re.search(r"what is (the )?pythagorean theorem", q):
        return "Pythagorean theorem: a² + b² = c², where c is the hypotenuse of a right triangle."

    if re.search(r"what is (the )?euler.?s? (number|identity|formula)", q):
        return "Euler's identity: e^(iπ) + 1 = 0, connecting e, i, π, 1, and 0."

    # ── Computing ──
    if re.search(r"what is machine learning", q):
        return (
            "Machine learning (ML) is a subset of AI where systems learn patterns from data "
            "rather than being explicitly programmed. Key paradigms include supervised, "
            "unsupervised, and reinforcement learning."
        )

    if re.search(r"what is (a )?neural network", q):
        return (
            "A neural network is a computational model inspired by the brain, composed of "
            "layers of interconnected nodes (neurons). Deep learning uses many layers "
            "to learn hierarchical representations from data."
        )

    if re.search(r"what is (a )?large language model|what is (an )?llm", q):
        return (
            "A Large Language Model (LLM) is a neural network trained on massive text corpora "
            "to predict and generate human language. Examples include GPT-4, Claude, and Gemini."
        )

    # ── General fallback ──
    return (
        f"Your question ('{query[:120]}') is outside the quantum optics domain this system specialises in. "
        "I can still help with questions about quantum states (Bell, GHZ, W), photonic components "
        "(SPDC, BS, HWP, QWP, PBS), experiment design, or general physics and science. "
        "Feel free to rephrase or ask something else!"
    )

print("Q&A answerers loaded.")

# ======================================================================
# CELL 15
# ======================================================================
# ── Main pipeline ──────────────────────────────────────────────────────────
def process_query(user_query: str) -> Dict[str, Any]:
    try:
        user_query = clean_text(user_query)
        if not user_query:
            return {"status": "error", "error_type": "EMPTY_QUERY",
                    "message": "Empty query.", "query": ""}

        scope_info      = is_query_in_scope(user_query)
        detected_target = scope_info.get("detected_target")
        intent          = classify_query_intent(user_query)

        # ---- Design generation ----
        if intent == "design_target_state":
            if detected_target is None:
                return {
                    "status": "error", "error_type": "NO_TARGET_DETECTED",
                    "message": "Could not identify a target quantum state. Try: 'construct a Bell state' or 'design a GHZ-3 state'.",
                    "query": user_query,
                }
            best     = search_best_design(detected_target, user_query=user_query)
            design   = best["design"]
            metrics  = best["metrics"]
            contexts = best["contexts"]
            return {
                "status":           "success",
                "mode":             "design_generation",
                "query":            user_query,
                "detected_target":  detected_target,
                "design":           design.to_dict(),
                "metrics":          metrics,
                "rag_context_preview": [
                    {"source": os.path.basename(c["source"]),
                     "score":  round(c["score"], 4),
                     "text_preview": c["text"][:500]}
                    for c in contexts[:CONFIG["max_return_contexts"]]
                ],
            }

        # ---- Domain Q&A ----
        elif intent in ("explain_component", "retrieval_based_qa"):
            contexts = retrieve_context(user_query, top_k=CONFIG["top_k_default"])
            answer   = answer_domain_question(user_query, contexts)
            return {
                "status":  "success",
                "mode":    "qa",
                "query":   user_query,
                "answer":  answer,
                "rag_context_preview": [
                    {"source": os.path.basename(c["source"]),
                     "score":  round(c["score"], 4),
                     "text_preview": c["text"][:500]}
                    for c in contexts[:CONFIG["max_return_contexts"]]
                ],
            }

        # ---- General question (anything outside the domain) ----
        else:
            answer = answer_general_question(user_query)
            return {
                "status": "success",
                "mode":   "general_qa",
                "query":  user_query,
                "answer": answer,
            }

    except Exception as e:
        return {
            "status":      "error",
            "error_type":  "INTERNAL_ERROR",
            "message":     str(e),
            "traceback":   traceback.format_exc(),
        }

print("Main pipeline loaded.")



# ══════════════════════════════════════════════════════════════════════════
# Startup builder
# ══════════════════════════════════════════════════════════════════════════
def build_retriever():
    """Load PDFs, chunk text, return (pdf_texts, documents)."""
    global pdf_texts, documents
    pdf_files = find_all_pdfs(CONFIG["input_root"])
    print(f"Found {len(pdf_files)} PDF files in {CONFIG['input_root']}")
    pdf_texts = {p: t for p in pdf_files if (t := read_pdf_text(p)).strip()}
    print(f"Extracted text from {len(pdf_texts)} PDFs")
    documents = []
    for source_path, full_text in pdf_texts.items():
        for idx, chunk in enumerate(chunk_text(
            full_text, CONFIG["chunk_size"],
            CONFIG["chunk_overlap"], CONFIG["min_chunk_chars"]
        )):
            documents.append({
                "id":          f"{os.path.basename(source_path)}::chunk_{idx}",
                "source":      source_path,
                "chunk_index": idx,
                "text":        chunk,
            })
    print(f"Total chunks: {len(documents)}")
    return pdf_texts, documents

# ══════════════════════════════════════════════════════════════════════════
# Flask API
# ══════════════════════════════════════════════════════════════════════════
flask_app = Flask(__name__)
CORS(flask_app)

@flask_app.route("/", methods=["GET"])
def root():
    return jsonify({"status": "ok", "message": "Quantum Optics RAG + GA backend running."})

@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":           "ok",
        "retriever_ready":  retriever.is_ready(),
        "pdf_count":        len(pdf_texts),
        "chunk_count":      len(documents),
        "supported_targets":list(TARGET_STATES.keys()),
        "components":       list(COMPONENT_LIBRARY.keys()),
    })

@flask_app.route("/query", methods=["POST"])
def query_api():
    data = request.get_json(force=True, silent=True) or {}
    q    = data.get("query", "").strip()
    if not q:
        return jsonify({"status": "error", "message": "No query provided."}), 400
    return jsonify(process_query(q))

@flask_app.route("/targets", methods=["GET"])
def list_targets():
    return jsonify({
        k: {"description": v["description"],
            "num_qubits":  v["num_qubits"],
            "aliases":     v.get("aliases", [])}
        for k, v in TARGET_STATES.items()
    })

@flask_app.route("/components", methods=["GET"])
def list_components():
    return jsonify(COMPONENT_LIBRARY)


# ══════════════════════════════════════════════════════════════════════════
# Startup: download PDFs, build retriever + physics engine
# ══════════════════════════════════════════════════════════════════════════
print("Starting up...")
download_pdfs()
build_retriever()
retriever  = TfidfRetriever(documents, max_features=CONFIG["tfidf_max_features"])
TARGET_DM  = _build_target_density_matrices()
if QUTIP_AVAILABLE:
    print(f"Target density matrices built: {list(TARGET_DM.keys())}")
print(f"✅ Ready | {len(pdf_texts)} PDFs | {len(documents)} chunks | retriever={retriever.is_ready()}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port, debug=False)
