import { useState, useRef, useEffect, useCallback } from 'react';
import Head from 'next/head';
import OpticalBench from '../components/OpticalBench';
import MathPanel from '../components/MathPanel';

const API = process.env.NEXT_PUBLIC_API_URL || '';

const SUGGESTED = [
  'Design a Bell state |Φ⁺⟩ experiment using Type-II SPDC',
  'What optical setup generates a 3-qubit GHZ state?',
  'How do I create a W state with photons?',
  'Build a linear cluster state for measurement-based QC',
  'Design a Dicke state D(4,2) experiment',
  'What is the difference between HWP and QWP?',
  'Explain how SPDC produces entangled photons',
  'Create a ring-4 graph state setup',
];

const ThemeIcon = ({ isDark }) => isDark ? (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1" x2="12" y2="3"/>
    <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/>
    <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
  </svg>
) : (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
);

const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);

const AtomIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="12" cy="12" r="1"/>
    <ellipse cx="12" cy="12" rx="10" ry="4"/>
    <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/>
    <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/>
  </svg>
);

export default function QSetup() {
  const [isDark, setIsDark]         = useState(true);
  const [query, setQuery]           = useState('');
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);
  const [animatePhotons, setAnimatePhotons] = useState(true);
  const [activeTab, setActiveTab]   = useState('bench');  // 'bench' | 'math'
  const [history, setHistory]       = useState([]);
  const [dots, setDots]             = useState('');
  const textareaRef = useRef(null);
  const resultsRef  = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  useEffect(() => {
    if (!loading) return;
    const t = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 400);
    return () => clearInterval(t);
  }, [loading]);

  const submit = useCallback(async (q) => {
    const text = (q || query).trim();
    if (!text || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setActiveTab('bench');

    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data);
      setHistory(h => [{ query: text, mode: data.mode, target: data.detected_target }, ...h.slice(0, 7)]);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    } catch (e) {
      setError(e.message.includes('fetch') ? 'Backend unreachable. Check that the server is running.' : e.message);
    } finally {
      setLoading(false);
    }
  }, [query, loading]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  // ── Styles ────────────────────────────────────────────────────────────────
  const bg     = 'var(--bg)';
  const bg2    = 'var(--bg2)';
  const panel  = 'var(--panel)';
  const text   = 'var(--text)';
  const text2  = 'var(--text2)';
  const text3  = 'var(--text3)';
  const border = 'var(--border)';
  const hl     = 'var(--highlight)';

  const isDesign = result?.mode === 'design_generation';
  const isQA     = result?.mode === 'qa' || result?.mode === 'general_qa';
  const design   = result?.design;
  const metrics  = result?.metrics;

  return (
    <>
      <Head>
        <title>QSetup — Quantum Setup Generator</title>
        <meta name="description" content="AI-powered quantum optical experiment designer" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet" />
      </Head>

      <div style={{ minHeight: '100vh', background: bg, color: text, display: 'flex', flexDirection: 'column' }}>

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <header style={{
          position: 'sticky', top: 0, zIndex: 100,
          backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
          background: isDark ? 'rgba(0,0,0,0.8)' : 'rgba(255,255,255,0.8)',
          borderBottom: `1px solid ${border}`,
          padding: '0 28px', height: 54,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ color: hl }}><AtomIcon /></div>
            <div>
              <span style={{
                fontFamily: 'var(--serif)', fontSize: 18, letterSpacing: '-0.02em', color: text,
              }}>QSetup</span>
              <span style={{
                fontFamily: 'var(--mono)', fontSize: 9, color: text3,
                letterSpacing: '0.15em', display: 'block', marginTop: -2,
              }}>QUANTUM SETUP GENERATOR</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {isDesign && metrics && (
              <div style={{
                fontFamily: 'var(--mono)', fontSize: 11, color: text2,
                display: 'flex', gap: 12,
              }}>
                <span style={{ color: 'var(--success)' }}>F={((metrics.fidelity_estimate||0)*100).toFixed(0)}%</span>
                <span>P={((metrics.success_probability_estimate||0)*100).toFixed(0)}%</span>
              </div>
            )}
            <button
              onClick={() => setIsDark(d => !d)}
              style={{
                background: 'none', border: `1px solid ${border}`,
                borderRadius: 8, padding: '5px 8px', color: text2,
                cursor: 'pointer', display: 'flex', alignItems: 'center',
              }}
            >
              <ThemeIcon isDark={isDark} />
            </button>
          </div>
        </header>

        {/* ── Hero ────────────────────────────────────────────────────────── */}
        {!result && !loading && (
          <div style={{
            textAlign: 'center', padding: '80px 24px 40px',
            animation: 'fadeUp 0.6s ease both',
          }}>
            <div style={{
              fontFamily: 'var(--serif)', fontSize: 'clamp(36px, 5vw, 60px)',
              lineHeight: 1.1, letterSpacing: '-0.03em', color: text,
              marginBottom: 16,
            }}>
              Quantum Setup
              <br />
              <em style={{ color: text2 }}>Generator</em>
            </div>
            <p style={{
              fontFamily: 'var(--sans)', fontSize: 16, color: text2,
              maxWidth: 480, margin: '0 auto 12px',
            }}>
              Describe a quantum state in natural language. The AI autonomously
              designs the photonic experiment — with real physics, real math.
            </p>
            <p style={{
              fontFamily: 'var(--mono)', fontSize: 11, color: text3,
              letterSpacing: '0.1em',
            }}>
              GENETIC ALGORITHM · QUTIP SIMULATION · F(ρ_target, ρ_out) = (Tr√(√ρ_t·ρ_out·√ρ_t))²
            </p>
          </div>
        )}

        {/* ── Input ───────────────────────────────────────────────────────── */}
        <div style={{
          padding: '0 24px 24px',
          maxWidth: 780, width: '100%', margin: '0 auto',
          animation: 'fadeUp 0.6s ease 0.1s both',
        }}>
          <div style={{
            background: panel,
            border: `1px solid ${border}`,
            borderRadius: 16,
            boxShadow: 'var(--shadow)',
            overflow: 'hidden',
          }}>
            <textarea
              ref={textareaRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
              placeholder="Ask anything — e.g. 'Design a Bell state |Φ⁺⟩ using Type-II SPDC and a BBO crystal pumped at 405nm'"
              rows={3}
              style={{
                width: '100%', resize: 'none',
                background: 'transparent',
                border: 'none', outline: 'none',
                color: text, fontFamily: 'var(--sans)',
                fontSize: 15, lineHeight: 1.6,
                padding: '18px 20px 10px',
              }}
            />
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 14px 12px',
              borderTop: `1px solid ${border}`,
            }}>
              <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: text3 }}>
                {loading ? `Genetic algorithm running${dots}` : 'Enter ↵ to submit'}
              </div>
              <button
                onClick={() => submit()}
                disabled={loading || !query.trim()}
                style={{
                  background: loading ? 'transparent' : hl,
                  border: `1px solid ${loading ? border : hl}`,
                  borderRadius: 10, padding: '7px 16px',
                  color: loading ? text3 : '#fff',
                  cursor: loading ? 'default' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: 7,
                  fontFamily: 'var(--sans)', fontSize: 13, fontWeight: 500,
                  transition: 'all 0.2s',
                }}
              >
                <SendIcon />
                {loading ? 'Running' : 'Generate'}
              </button>
            </div>
          </div>

          {/* Suggestions */}
          {!result && !loading && (
            <div style={{ marginTop: 16 }}>
              <div style={{
                fontSize: 10, fontFamily: 'var(--mono)', color: text3,
                letterSpacing: '0.12em', marginBottom: 10,
              }}>TRY ASKING</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {SUGGESTED.slice(0, 6).map(s => (
                  <button key={s}
                    onClick={() => { setQuery(s); submit(s); }}
                    style={{
                      background: panel, border: `1px solid ${border}`,
                      borderRadius: 20, padding: '6px 14px',
                      fontFamily: 'var(--sans)', fontSize: 12, color: text2,
                      cursor: 'pointer', transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { e.target.style.borderColor = hl; e.target.style.color = text; }}
                    onMouseLeave={e => { e.target.style.borderColor = border; e.target.style.color = text2; }}
                  >{s}</button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Results ─────────────────────────────────────────────────────── */}
        <div ref={resultsRef} style={{ maxWidth: 1200, width: '100%', margin: '0 auto', padding: '0 24px 80px' }}>

          {/* Error */}
          {error && (
            <div style={{
              background: 'rgba(255,59,48,0.08)', border: '1px solid rgba(255,59,48,0.3)',
              borderRadius: 12, padding: '14px 18px', color: '#ff3b30',
              fontFamily: 'var(--mono)', fontSize: 13, marginBottom: 20,
              animation: 'fadeUp 0.4s ease',
            }}>⚠ {error}</div>
          )}

          {/* Loading skeleton */}
          {loading && (
            <div style={{ animation: 'fadeUp 0.4s ease' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: text3,
                marginBottom: 16, letterSpacing: '0.08em' }}>
                ◎ RUNNING GENETIC ALGORITHM{dots}
              </div>
              {[100, 75, 90, 60].map((w, i) => (
                <div key={i} style={{
                  height: 10, background: bg2, borderRadius: 5,
                  width: `${w}%`, marginBottom: 10,
                  animation: `pulse 1.5s ease ${i * 0.15}s infinite`,
                }} />
              ))}
            </div>
          )}

          {/* API error */}
          {result?.status === 'error' && (
            <div style={{
              background: 'rgba(255,59,48,0.08)', border: '1px solid rgba(255,59,48,0.3)',
              borderRadius: 12, padding: '14px 18px', animation: 'fadeUp 0.4s ease',
            }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: '#ff3b30',
                letterSpacing: '0.1em', marginBottom: 4 }}>{result.error_type}</div>
              <div style={{ fontSize: 13, color: text2 }}>{result.message}</div>
            </div>
          )}

          {/* QA answer */}
          {isQA && (
            <div style={{ animation: 'fadeUp 0.5s ease' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: text3,
                letterSpacing: '0.12em', marginBottom: 12 }}>ANSWER</div>
              <div style={{
                background: panel, border: `1px solid ${border}`,
                borderRadius: 16, padding: 24,
              }}>
                <p style={{ fontSize: 15, lineHeight: 1.8, color: text, whiteSpace: 'pre-wrap' }}>
                  {result.answer}
                </p>
                {result.rag_context_preview?.length > 0 && (
                  <div style={{ marginTop: 20, paddingTop: 16, borderTop: `1px solid ${border}` }}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: text3,
                      letterSpacing: '0.1em', marginBottom: 10 }}>SOURCES</div>
                    {result.rag_context_preview.slice(0,2).map((c, i) => (
                      <div key={i} style={{ fontFamily: 'var(--mono)', fontSize: 11, color: text3,
                        marginBottom: 4 }}>
                        {c.source} · {c.score}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Design result */}
          {isDesign && design && (
            <div style={{ animation: 'fadeUp 0.5s ease' }}>

              {/* Result header */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginBottom: 20, flexWrap: 'wrap', gap: 12,
              }}>
                <div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: text3,
                    letterSpacing: '0.12em', marginBottom: 4 }}>EXPERIMENT DESIGN</div>
                  <div style={{ fontFamily: 'var(--serif)', fontSize: 26,
                    letterSpacing: '-0.02em', color: text }}>
                    {design.target_name?.replace(/_/g, ' ').toUpperCase()}
                  </div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: text2, marginTop: 2 }}>
                    {design.num_qubits}-qubit photonic state · {design.components?.length} components
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {/* Animate toggle */}
                  <button onClick={() => setAnimatePhotons(a => !a)} style={{
                    background: animatePhotons ? `${hl}22` : panel,
                    border: `1px solid ${animatePhotons ? hl : border}`,
                    borderRadius: 8, padding: '6px 12px',
                    fontFamily: 'var(--mono)', fontSize: 11,
                    color: animatePhotons ? hl : text2, cursor: 'pointer',
                  }}>
                    {animatePhotons ? '◎ photons on' : '○ photons off'}
                  </button>

                  {/* Tab switcher */}
                  <div style={{
                    display: 'flex', background: bg2, borderRadius: 10,
                    padding: 3, border: `1px solid ${border}`,
                  }}>
                    {[['bench','Bench'],['math','Math']].map(([key, label]) => (
                      <button key={key} onClick={() => setActiveTab(key)} style={{
                        background: activeTab === key ? panel : 'transparent',
                        border: activeTab === key ? `1px solid ${border}` : '1px solid transparent',
                        borderRadius: 8, padding: '5px 14px',
                        fontFamily: 'var(--mono)', fontSize: 11,
                        color: activeTab === key ? text : text3, cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}>{label}</button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Bench tab */}
              {activeTab === 'bench' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 16 }}>

                  {/* Optical bench */}
                  <div style={{
                    background: panel, border: `1px solid ${border}`,
                    borderRadius: 16, padding: 20, overflow: 'hidden',
                  }}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: text3,
                      letterSpacing: '0.12em', marginBottom: 14 }}>OPTICAL BENCH</div>
                    <OpticalBench
                      components={design.components}
                      connections={design.connections}
                      animatePhotons={animatePhotons}
                      isDark={isDark}
                    />
                    {design.postselection && design.postselection !== 'None' && (
                      <div style={{
                        marginTop: 14, padding: '8px 12px',
                        background: `rgba(255,214,10,0.08)`,
                        border: '1px solid rgba(255,214,10,0.25)',
                        borderRadius: 8, fontFamily: 'var(--mono)', fontSize: 11,
                      }}>
                        <span style={{ color: '#ffd60a', letterSpacing: '0.08em' }}>POST-SELECTION</span>
                        <span style={{ color: text2, marginLeft: 8 }}>{design.postselection}</span>
                      </div>
                    )}
                  </div>

                  {/* Component list */}
                  <div style={{
                    background: panel, border: `1px solid ${border}`,
                    borderRadius: 16, padding: 20,
                    display: 'flex', flexDirection: 'column', gap: 0,
                    maxHeight: 520, overflowY: 'auto',
                  }}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: text3,
                      letterSpacing: '0.12em', marginBottom: 14 }}>COMPONENTS</div>
                    {design.components?.map((c, i) => {
                      const colors = {
                        SPDC: '#ff9f0a', BS: '#0a84ff', PBS: '#30d158',
                        HWP: '#bf5af2', QWP: '#5e5ce6', PhaseShifter: '#ff375f',
                        PNRDetector: '#64d2ff', ThresholdDetector: '#2ac9de',
                        PostSelection: '#ffd60a', Heralding: '#ff6b00',
                        CrossKerr: '#ff375f', VacuumAncilla: '#6e6e73',
                      };
                      const color = colors[c.type] || text2;
                      const keyParams = Object.entries(c.params || {})
                        .filter(([k]) => !['purpose','output_pair','modes','entangled_state',
                          'pump','degenerate','interference_mode','efficiency_assumed',
                          'accept_condition'].includes(k))
                        .slice(0, 3);
                      return (
                        <div key={c.id} style={{
                          padding: '10px 0',
                          borderBottom: i < design.components.length - 1 ? `1px solid ${border}` : 'none',
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                            <div style={{
                              width: 6, height: 6, borderRadius: '50%',
                              background: color, flexShrink: 0,
                              boxShadow: `0 0 6px ${color}`,
                            }} />
                            <span style={{ fontFamily: 'var(--mono)', fontSize: 12,
                              color, fontWeight: 500 }}>{c.type}</span>
                          </div>
                          {keyParams.map(([k, v]) => (
                            <div key={k} style={{
                              fontFamily: 'var(--mono)', fontSize: 10, color: text3,
                              paddingLeft: 14, lineHeight: 1.6,
                            }}>
                              {k}: <span style={{ color: text2 }}>
                                {typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(4)) : String(v)}
                              </span>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Math tab */}
              {activeTab === 'math' && (
                <div style={{
                  background: panel, border: `1px solid ${border}`,
                  borderRadius: 16, padding: 28,
                  animation: 'fadeIn 0.3s ease',
                }}>
                  <MathPanel result={result} isDark={isDark} />
                </div>
              )}

              {/* Notes */}
              {design.notes?.length > 0 && (
                <div style={{
                  marginTop: 16, padding: '14px 18px',
                  background: bg2, border: `1px solid ${border}`,
                  borderRadius: 12,
                }}>
                  {design.notes.map((n, i) => (
                    <div key={i} style={{
                      fontFamily: 'var(--sans)', fontSize: 13, color: text2,
                      display: 'flex', gap: 8, marginBottom: i < design.notes.length-1 ? 6 : 0,
                    }}>
                      <span style={{ color: text3, flexShrink: 0 }}>—</span>
                      {n}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── History sidebar (only when results exist) ────────────────────── */}
        {history.length > 0 && (
          <div style={{
            position: 'fixed', bottom: 24, right: 24,
            background: panel, border: `1px solid ${border}`,
            borderRadius: 16, padding: '14px 16px', maxWidth: 260,
            boxShadow: 'var(--shadow)',
            animation: 'fadeUp 0.4s ease',
          }}>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: text3,
              letterSpacing: '0.12em', marginBottom: 10 }}>RECENT</div>
            {history.slice(0, 4).map((h, i) => (
              <button key={i} onClick={() => { setQuery(h.query); submit(h.query); }}
                style={{
                  display: 'block', width: '100%', background: 'none',
                  border: 'none', borderBottom: i < Math.min(history.length, 4) - 1 ? `1px solid ${border}` : 'none',
                  padding: '7px 0', textAlign: 'left', cursor: 'pointer', color: text2,
                  fontFamily: 'var(--sans)', fontSize: 11, lineHeight: 1.4,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}
                onMouseEnter={e => e.target.style.color = text}
                onMouseLeave={e => e.target.style.color = text2}
                title={h.query}
              >{h.query}</button>
            ))}
          </div>
        )}

        {/* ── Footer ──────────────────────────────────────────────────────── */}
        <footer style={{
          borderTop: `1px solid ${border}`, padding: '16px 28px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginTop: 'auto',
        }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: text3,
            letterSpacing: '0.1em' }}>
            QSETUP · QUANTUM SETUP GENERATOR
          </span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: text3 }}>
            GA · QuTiP · TF-IDF RAG
          </span>
        </footer>
      </div>

      <style jsx global>{`
        @keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
        @keyframes fadeIn { from{opacity:0} to{opacity:1} }
        @keyframes pulse  { 0%,100%{opacity:0.4} 50%{opacity:0.8} }
        textarea::placeholder { color: var(--text3); }
        button { transition: all 0.15s ease; }
      `}</style>
    </>
  );
}
