// ── Mathematical state representations ────────────────────────────────────
const STATE_MATH = {
  bell_phi_plus: {
    ket:    '|Φ⁺⟩ = (|HH⟩ + |VV⟩) / √2',
    matrix: '½ · [[1,0,0,1],[0,0,0,0],[0,0,0,0],[1,0,0,1]]',
    unitary: 'U_SPDC → |Φ⁺⟩\nU_PS(π) = diag(1, e^{iπ}) = diag(1,-1)',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'E(|Φ⁺⟩) = 1 ebit (maximally entangled)',
    concurrence: 'C = 1.0',
    notes: 'Generated via Type-II SPDC. Signal and idler photons are orthogonally polarized and entangled.',
  },
  bell_phi_minus: {
    ket:    '|Φ⁻⟩ = (|HH⟩ − |VV⟩) / √2',
    matrix: '½ · [[1,0,0,-1],[0,0,0,0],[0,0,0,0],[-1,0,0,1]]',
    unitary: 'U = U_PS(π) · U_SPDC\nPhase shift: e^{iπ} = −1 on one arm',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'E = 1 ebit',
    concurrence: 'C = 1.0',
    notes: 'Relative π phase between |HH⟩ and |VV⟩ amplitudes distinguishes Φ⁻ from Φ⁺.',
  },
  bell_psi_plus: {
    ket:    '|Ψ⁺⟩ = (|HV⟩ + |VH⟩) / √2',
    matrix: '½ · [[0,0,0,0],[0,1,1,0],[0,1,1,0],[0,0,0,0]]',
    unitary: 'U_HWP(45°) = [[0,1],[1,0]] on signal mode\nFlips H↔V: |HH⟩ → |HV⟩, |VV⟩ → |VH⟩',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'E = 1 ebit',
    concurrence: 'C = 1.0',
    notes: 'Anti-correlated polarization state. HWP at 45° maps Φ⁺ → Ψ⁺.',
  },
  bell_psi_minus: {
    ket:    '|Ψ⁻⟩ = (|HV⟩ − |VH⟩) / √2',
    matrix: '½ · [[0,0,0,0],[0,1,-1,0],[0,-1,1,0],[0,0,0,0]]',
    unitary: 'Singlet state: only antisymmetric Bell state\nU = U_PS(π) · U_HWP(45°)',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'E = 1 ebit',
    concurrence: 'C = 1.0',
    notes: 'The only antisymmetric Bell state. Invariant under identical local unitaries.',
  },
  ghz_3: {
    ket:    '|GHZ₃⟩ = (|HHH⟩ + |VVV⟩) / √2',
    matrix: '8×8 density matrix:\nρ = ½(|HHH⟩⟨HHH| + |HHH⟩⟨VVV| + |VVV⟩⟨HHH| + |VVV⟩⟨VVV|)',
    unitary: 'U_BS = (1/√2)[[1, i],[i, 1]] (fusion)\nFusion gate: U_BS · (SPDC₁ ⊗ SPDC₂)',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'Genuine tripartite entanglement\nE_geometric = 1/2',
    concurrence: 'Tangle τ = 1/4',
    notes: 'Type-II fusion of two Bell pairs at a 50:50 BS. Post-select on 3-fold coincidence.',
  },
  ghz_4: {
    ket:    '|GHZ₄⟩ = (|HHHH⟩ + |VVVV⟩) / √2',
    matrix: '16×16 density matrix (GHZ form)',
    unitary: 'Two SPDC sources + BS fusion + heralding\nU = Herald · U_HWP · U_BS · (SPDC₁ ⊗ SPDC₂)',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'Genuine 4-partite entanglement',
    concurrence: 'Tangle τ = 1/8',
    notes: 'Requires heralded fusion. Success probability ~1/8 without photon-number resolution.',
  },
  w_3: {
    ket:    '|W₃⟩ = (|HVV⟩ + |VHV⟩ + |VVH⟩) / √3',
    matrix: '⅓ · (sum of all single-excitation outer products)',
    unitary: 'Symmetric superposition via cascaded BS:\nU_BS(θ₁) · U_BS(θ₂) with θ = arctan(1/√2)',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'Robust to particle loss (unlike GHZ)',
    concurrence: 'C₁₂ = 2/3',
    notes: 'Single excitation delocalized across 3 modes. More robust to loss than GHZ states.',
  },
  w_4: {
    ket:    '|W₄⟩ = (|HVVV⟩+|VHVV⟩+|VVHV⟩+|VVVH⟩) / 2',
    matrix: '¼ · (sum of all single-excitation outer products, 4-mode)',
    unitary: 'Two SPDC sources + cascaded symmetric BS network',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'Single excitation across 4 modes',
    concurrence: 'C₁₂ = 1/2',
    notes: '4-qubit W state. Maximally robust multipartite entanglement against photon loss.',
  },
  cluster_linear_3: {
    ket:    '|C₃⟩ = CZ₁₂ · CZ₂₃ · |+⟩⊗³',
    matrix: 'Graph state: ρ = |C₃⟩⟨C₃|\nAdjacency: 1—2—3',
    unitary: '|+⟩ = (|H⟩+|V⟩)/√2 via HWP(22.5°)\nCZ = diag(1,1,1,-1) via PBS fusion',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'Resource for 1D measurement-based QC',
    concurrence: 'Stabilizer state: +XXX, +ZZI, +IZZ',
    notes: 'Linear cluster state enables universal MBQC. Stabilizers: ⟨X₁Z₂, Z₁X₂Z₃, Z₂X₃⟩.',
  },
  cluster_linear_4: {
    ket:    '|C₄⟩ = CZ₁₂·CZ₂₃·CZ₃₄·|+⟩⊗⁴',
    matrix: 'Graph state: 1—2—3—4',
    unitary: 'Two SPDC + double BS fusion with heralding',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: '4-qubit linear cluster, universal MBQC resource',
    concurrence: 'Stabilizer: ⟨X₁Z₂, Z₁X₂Z₃, Z₂X₃Z₄, Z₃X₄⟩',
    notes: 'Heralded preparation improves success probability over post-selection alone.',
  },
  cluster_square_4: {
    ket:    '|□₄⟩ = CZ₁₂·CZ₂₃·CZ₃₄·CZ₄₁·|+⟩⊗⁴',
    matrix: 'Square graph: 1—2\n              |  |\n              4—3',
    unitary: 'PBS fusion creates CZ bonds in 2D topology',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: '2D cluster: universal MBQC on square lattice',
    concurrence: 'Perimeter stabilizers + plaquette operators',
    notes: 'Square (2D) cluster state. 4 CZ bonds form a cycle. Universal for MBQC.',
  },
  dicke_4_1: {
    ket:    '|D₄¹⟩ = (|HVVV⟩+|VHVV⟩+|VVHV⟩+|VVVH⟩) / 2',
    matrix: '¼ · Π₁ (projector onto 1-excitation subspace)',
    unitary: 'Cascaded symmetric BS network\nU = BS₃₄ · BS₂₃ · BS₁₂ (Clements network)',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'Permutationally invariant, 1-excitation sector',
    concurrence: 'Same as W₄ state (identical)',
    notes: 'Dicke state D(4,1) ≡ W₄. Post-select on total photon number = 1.',
  },
  dicke_4_2: {
    ket:    '|D₄²⟩ = (1/√6) Σ_{|S|=2} |S⟩',
    matrix: '(1/6) · Π₂ (projector onto 2-excitation subspace)',
    unitary: 'Two SPDC + balanced BS network\nC(6,2) = 6 terms: |HHVV⟩,|HVHV⟩,...',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'Permutationally invariant, 2-excitation sector',
    concurrence: '√(8/3)/3 ≈ 0.544',
    notes: 'Dicke D(4,2): equal superposition of all 4-qubit states with exactly 2 excitations.',
  },
  star_3: {
    ket:    '|Star₃⟩ = CZ₀₁·CZ₀₂·|+⟩⊗³',
    matrix: 'Star graph: 0 connected to 1,2',
    unitary: 'Central qubit 0 via PBS fusions\nStabilizers: X₀Z₁Z₂, Z₀X₁, Z₀X₂',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'Star graph state: hub-and-spoke topology',
    concurrence: 'Equivalent to GHZ₃ up to local unitaries',
    notes: 'Star-3 is LC-equivalent to GHZ₃. Central qubit acts as hub for entanglement distribution.',
  },
  star_4: {
    ket:    '|Star₄⟩ = CZ₀₁·CZ₀₂·CZ₀₃·|+⟩⊗⁴',
    matrix: 'Star graph: 0 connected to 1,2,3',
    unitary: 'Two sequential PBS fusions on central qubit',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: 'LC-equivalent to GHZ₄',
    concurrence: 'Stabilizers: X₀Z₁Z₂Z₃, Z₀X₁, Z₀X₂, Z₀X₃',
    notes: '4-qubit star graph. Central qubit maximally connected. Heralded preparation used.',
  },
  ring_4: {
    ket:    '|Ring₄⟩ = CZ₁₂·CZ₂₃·CZ₃₄·CZ₄₁·|+⟩⊗⁴',
    matrix: 'Cycle graph C₄: 1—2—3—4—1',
    unitary: 'BS fusions create adjacent CZ bonds\nPBS closes the ring: bond 4→1',
    fidelity_formula: 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²',
    entanglement: '4-qubit ring = square cluster state (equivalent)',
    concurrence: 'All nearest-neighbor bonds equal',
    notes: 'Ring-4 is equivalent to square cluster-4. Periodic boundary conditions.',
  },
};

export function getMathForState(targetName) {
  return STATE_MATH[targetName] || null;
}

export default function MathPanel({ result, isDark }) {
  if (!result || result.mode !== 'design_generation') return null;

  const { design, metrics, detected_target } = result;
  const math = STATE_MATH[detected_target] || {};
  const m = metrics || {};

  const textColor = isDark ? '#f5f5f7' : '#1d1d1f';
  const mutedColor = isDark ? '#ababab' : '#6e6e73';
  const borderColor = isDark ? '#2c2c2e' : '#d2d2d7';
  const panelBg = isDark ? '#1c1c1e' : '#f5f5f7';
  const codeBg = isDark ? '#0a0a0a' : '#f0f0f5';

  const Block = ({ label, children, accent = '#0a84ff' }) => (
    <div style={{
      borderLeft: `3px solid ${accent}`,
      paddingLeft: 16, marginBottom: 20,
    }}>
      <div style={{ fontSize: 10, fontFamily: 'var(--mono)', letterSpacing: '0.12em',
        color: accent, marginBottom: 6, textTransform: 'uppercase' }}>{label}</div>
      {children}
    </div>
  );

  const Code = ({ children }) => (
    <pre style={{
      background: codeBg, borderRadius: 8, padding: '10px 14px',
      fontFamily: 'var(--mono)', fontSize: 12, color: textColor,
      lineHeight: 1.7, overflowX: 'auto', whiteSpace: 'pre-wrap',
      border: `1px solid ${borderColor}`,
    }}>{children}</pre>
  );

  return (
    <div style={{ color: textColor }}>

      {/* State vector */}
      {math.ket && (
        <Block label="Quantum State |ψ⟩" accent="#bf5af2">
          <div style={{
            fontSize: 18, fontFamily: 'var(--mono)', letterSpacing: '0.02em',
            padding: '12px 0', color: isDark ? '#bf5af2' : '#7f3fbf',
          }}>{math.ket}</div>
        </Block>
      )}

      {/* Fidelity formula */}
      <Block label="Fidelity (PS Definition)" accent="#0a84ff">
        <Code>{math.fidelity_formula || 'F(ρ_t, ρ_out) = (Tr√(√ρ_t · ρ_out · √ρ_t))²'}</Code>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginTop: 10 }}>
          {[
            ['Fidelity', `${(m.fidelity_estimate * 100).toFixed(1)}%`, m.fidelity_source === 'qutip_simulation' ? '#30d158' : '#ff9f0a'],
            ['Success P', `${(m.success_probability_estimate * 100).toFixed(1)}%`, '#0a84ff'],
            ['Score', `${(m.overall_score * 100).toFixed(0)}/100`, '#bf5af2'],
          ].map(([label, val, color]) => (
            <div key={label} style={{
              background: codeBg, borderRadius: 8, padding: '10px 12px',
              border: `1px solid ${borderColor}`,
            }}>
              <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: mutedColor,
                letterSpacing: '0.1em', marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 20, fontFamily: 'var(--mono)', color, fontWeight: 500 }}>{val}</div>
            </div>
          ))}
        </div>
        {m.fidelity_source && (
          <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: mutedColor, marginTop: 6 }}>
            source: {m.fidelity_source}
            {m.ga_runtime_sec && ` · GA runtime: ${m.ga_runtime_sec}s · ${m.ga_generations} gen × ${m.ga_population_size} pop`}
          </div>
        )}
      </Block>

      {/* Unitary operators */}
      {math.unitary && (
        <Block label="Unitary Operations" accent="#ff9f0a">
          <Code>{math.unitary}</Code>
        </Block>
      )}

      {/* Density matrix */}
      {math.matrix && (
        <Block label="Density Matrix ρ" accent="#30d158">
          <Code>{math.matrix}</Code>
        </Block>
      )}

      {/* Entanglement */}
      {math.entanglement && (
        <Block label="Entanglement Properties" accent="#ff375f">
          <Code>{`${math.entanglement}\n${math.concurrence ? `Concurrence/Tangle: ${math.concurrence}` : ''}`}</Code>
        </Block>
      )}

      {/* Component operations */}
      <Block label="Component Unitaries" accent="#6e6e73">
        <Code>{[
          'U_BS(r)  = [[√(1-r),   i√r  ],   Beam Splitter',
          '           [i√r,      √(1-r)]]',
          '',
          'U_HWP(θ) = [[cos2θ,  sin2θ],   Half-Wave Plate',
          '            [sin2θ, -cos2θ]]',
          '',
          'U_QWP(θ) = (1/√2)[[1-i·cos2θ, -i·sin2θ],   Quarter-Wave Plate',
          '                   [-i·sin2θ, 1+i·cos2θ]]',
          '',
          'U_PS(φ)  = [[1,    0    ],   Phase Shifter',
          '            [0, e^{iφ}  ]]',
          '',
          'SPDC → |Φ⁺⟩ = (|HH⟩+|VV⟩)/√2   (ideal Type-II)',
        ].join('\n')}</Code>
      </Block>

      {/* Resource budget */}
      <Block label="Resource Budget" accent="#ffd60a">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
          {[
            ['SPDC', m.num_spdc, m.num_spdc > 3 ? '#ff375f' : '#30d158'],
            ['Components', m.num_components, '#0a84ff'],
            ['Spatial modes', m.spatial_modes, '#bf5af2'],
            ['Cost', m.total_cost, '#ff9f0a'],
          ].map(([label, val, color]) => (
            <div key={label} style={{
              background: codeBg, borderRadius: 8, padding: '8px 10px',
              border: `1px solid ${borderColor}`, textAlign: 'center',
            }}>
              <div style={{ fontSize: 18, fontFamily: 'var(--mono)', color }}>{val}</div>
              <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: mutedColor,
                marginTop: 2, letterSpacing: '0.08em' }}>{label}</div>
            </div>
          ))}
        </div>
      </Block>

      {/* Notes */}
      {math.notes && (
        <Block label="Physical Interpretation" accent="#ababab">
          <div style={{ fontSize: 13, lineHeight: 1.7, color: mutedColor }}>{math.notes}</div>
        </Block>
      )}

      {/* GA chromosome */}
      {m.ga_best_chromosome && (
        <Block label="GA Best Chromosome" accent="#636366">
          <Code>{m.ga_best_chromosome.join(' → ')}</Code>
          {m.ga_fitness_history && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: mutedColor,
                marginBottom: 4 }}>FITNESS HISTORY (generations)</div>
              <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end', height: 40 }}>
                {m.ga_fitness_history.map((f, i) => (
                  <div key={i} style={{
                    flex: 1, background: `rgba(10,132,255,${0.2 + f * 0.8})`,
                    height: `${Math.max(4, f * 40)}px`, borderRadius: 2,
                    minWidth: 2,
                  }} title={`Gen ${i+1}: ${f}`} />
                ))}
              </div>
            </div>
          )}
        </Block>
      )}

      {/* Retrieved sources */}
      {result.rag_context_preview?.length > 0 && (
        <Block label="Research Papers (RAG)" accent="#636366">
          {result.rag_context_preview.slice(0, 3).map((c, i) => (
            <div key={i} style={{
              marginBottom: 8, padding: '8px 10px',
              background: codeBg, borderRadius: 6,
              border: `1px solid ${borderColor}`,
            }}>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: mutedColor }}>
                {c.source} · score: {c.score}
              </div>
              <div style={{ fontSize: 11, color: mutedColor, marginTop: 4,
                overflow: 'hidden', display: '-webkit-box',
                WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                {c.text_preview}
              </div>
            </div>
          ))}
        </Block>
      )}
    </div>
  );
}
