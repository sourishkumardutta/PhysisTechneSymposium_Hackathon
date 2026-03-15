import { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import CircuitDiagram from '../components/CircuitDiagram';
import MetricBar from '../components/MetricBar';

const API = process.env.NEXT_PUBLIC_API_URL || '';

const QUICK = [
  { label: 'Bell State',  query: 'construct a bell state' },
  { label: 'GHZ-3',       query: 'construct a GHZ 3 state' },
  { label: 'GHZ-4',       query: 'construct a GHZ 4 state' },
  { label: 'W State',     query: 'construct a W state' },
  { label: 'What is SPDC?',query: 'what is SPDC?' },
  { label: 'HWP vs QWP', query: 'difference between HWP and QWP' },
];

function Tag({ children, color = 'var(--cyan)' }) {
  return (
    <span style={{
      fontFamily: 'var(--mono)', fontSize: '10px', padding: '2px 8px',
      border: `1px solid ${color}44`, color, background: `${color}10`,
      borderRadius: '3px', display: 'inline-block', marginRight: '6px', marginBottom: '4px',
    }}>{children}</span>
  );
}

function Panel({ title, accent = 'var(--cyan)', children, style = {} }) {
  return (
    <div style={{
      background: 'var(--panel)', border: `1px solid var(--border)`,
      borderTop: `2px solid ${accent}`, borderRadius: '6px',
      padding: '16px', position: 'relative', ...style,
    }}>
      {title && (
        <div style={{
          fontFamily: 'var(--mono)', fontSize: '10px', color: accent,
          letterSpacing: '0.12em', textTransform: 'uppercase',
          marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px',
        }}>
          <span style={{ display:'inline-block', width:'6px', height:'6px',
            background: accent, borderRadius:'50%', boxShadow:`0 0 6px ${accent}` }} />
          {title}
        </div>
      )}
      {children}
    </div>
  );
}

export default function Home() {
  const [query, setQuery]     = useState('');
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [health, setHealth]   = useState(null);
  const [history, setHistory] = useState([]);
  const [dots, setDots]       = useState('');
  const inputRef = useRef(null);

  // Animate loading dots
  useEffect(() => {
    if (!loading) return;
    const t = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 400);
    return () => clearInterval(t);
  }, [loading]);

  // Health check on mount
  useEffect(() => {
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(d => setHealth(d))
      .catch(() => setHealth(null));
  }, []);

  async function submit(q) {
    const text = (q || query).trim();
    if (!text) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
      });
      const data = await res.json();
      setResult(data);
      setHistory(h => [{ query: text, mode: data.mode || data.status }, ...h.slice(0, 9)]);
    } catch (e) {
      setError('Backend unreachable. Check that your Kaggle notebook is still running.');
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  }

  const design   = result?.design;
  const metrics  = result?.metrics;
  const isDesign = result?.mode === 'design_generation';
  const isQA     = result?.mode === 'qa' || result?.mode === 'general_qa';

  return (
    <>
      <Head>
        <title>QuantumOptix — Photonic Experiment Designer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:ital,wght@0,300;0,400;0,600;0,700;1,300&display=swap" rel="stylesheet" />
      </Head>

      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>

        {/* ── Header ── */}
        <header style={{
          borderBottom: '1px solid var(--border)',
          background: 'linear-gradient(180deg, #0a1628 0%, var(--bg) 100%)',
          padding: '0 24px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          height: '56px', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            {/* Logo mark */}
            <svg width="28" height="28" viewBox="0 0 28 28">
              <circle cx="14" cy="14" r="12" fill="none" stroke="var(--cyan)" strokeWidth="1.2" />
              <circle cx="14" cy="14" r="5" fill="none" stroke="var(--cyan)" strokeWidth="1" strokeDasharray="3 2" />
              <line x1="2" y1="14" x2="26" y2="14" stroke="var(--cyan)" strokeWidth="0.8" opacity="0.5" />
              <line x1="14" y1="2" x2="14" y2="26" stroke="var(--cyan)" strokeWidth="0.8" opacity="0.5" />
              <circle cx="14" cy="14" r="2.5" fill="var(--cyan)" />
            </svg>
            <div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '15px', color: 'var(--cyan)', letterSpacing: '0.08em' }}>
                QUANTUM<span style={{ color: 'var(--text2)' }}>OPTIX</span>
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--text3)', letterSpacing: '0.15em' }}>
                PHOTONIC EXPERIMENT DESIGNER
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            {health && (
              <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)',
                display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width:'6px', height:'6px', borderRadius:'50%',
                  background: 'var(--green)', display:'inline-block',
                  boxShadow: '0 0 6px var(--green)', animation: 'pulse 2s infinite' }} />
                BACKEND LIVE · {health.pdf_count} PDFs · {health.chunk_count} chunks
              </div>
            )}
          </div>
        </header>

        {/* ── Main ── */}
        <main style={{ flex: 1, display: 'grid', gridTemplateColumns: '220px 1fr', gap: '0' }}>

          {/* ── Sidebar ── */}
          <aside style={{
            borderRight: '1px solid var(--border)', padding: '16px',
            background: 'var(--bg2)', display: 'flex', flexDirection: 'column', gap: '16px',
          }}>
            <div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--text3)',
                letterSpacing: '0.15em', marginBottom: '10px' }}>QUICK QUERIES</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {QUICK.map(q => (
                  <button key={q.query} onClick={() => { setQuery(q.query); submit(q.query); }}
                    style={{
                      background: 'transparent', border: '1px solid var(--border2)',
                      color: 'var(--text2)', fontFamily: 'var(--mono)', fontSize: '10px',
                      padding: '7px 10px', borderRadius: '4px', cursor: 'pointer',
                      textAlign: 'left', transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { e.target.style.borderColor='var(--cyan)'; e.target.style.color='var(--cyan)'; e.target.style.background='var(--cyan-dim)'; }}
                    onMouseLeave={e => { e.target.style.borderColor='var(--border2)'; e.target.style.color='var(--text2)'; e.target.style.background='transparent'; }}
                  >
                    ▸ {q.label}
                  </button>
                ))}
              </div>
            </div>

            {history.length > 0 && (
              <div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--text3)',
                  letterSpacing: '0.15em', marginBottom: '10px' }}>RECENT</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {history.map((h, i) => (
                    <button key={i} onClick={() => { setQuery(h.query); submit(h.query); }}
                      style={{
                        background: 'transparent', border: '1px solid var(--border2)',
                        color: 'var(--text3)', fontFamily: 'var(--mono)', fontSize: '9px',
                        padding: '6px 8px', borderRadius: '4px', cursor: 'pointer',
                        textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap', maxWidth: '100%', transition: 'all 0.15s',
                      }}
                      onMouseEnter={e => { e.target.style.color='var(--text)'; e.target.style.borderColor='var(--border)'; }}
                      onMouseLeave={e => { e.target.style.color='var(--text3)'; e.target.style.borderColor='var(--border2)'; }}
                      title={h.query}
                    >
                      {h.query}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {health?.supported_targets && (
              <div style={{ marginTop: 'auto' }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--text3)',
                  letterSpacing: '0.15em', marginBottom: '8px' }}>SUPPORTED STATES</div>
                {health.supported_targets.map(t => (
                  <Tag key={t} color="var(--green)">{t}</Tag>
                ))}
              </div>
            )}
          </aside>

          {/* ── Content ── */}
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>

            {/* Input */}
            <Panel title="Query Interface" accent="var(--cyan)">
              <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, position: 'relative' }}>
                  <textarea
                    ref={inputRef}
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={handleKey}
                    placeholder="e.g.  construct a Bell state  |  what is SPDC?  |  build a GHZ-3 using a 390nm laser"
                    rows={2}
                    style={{
                      width: '100%', resize: 'none',
                      background: 'var(--bg3)', border: '1px solid var(--border)',
                      borderRadius: '5px', color: 'var(--text)',
                      fontFamily: 'var(--mono)', fontSize: '13px',
                      padding: '10px 14px', outline: 'none',
                      transition: 'border-color 0.2s',
                    }}
                    onFocus={e => e.target.style.borderColor = 'var(--cyan)'}
                    onBlur={e => e.target.style.borderColor = 'var(--border)'}
                  />
                </div>
                <button
                  onClick={() => submit()}
                  disabled={loading || !query.trim()}
                  style={{
                    height: '60px', padding: '0 22px',
                    background: loading ? 'transparent' : 'var(--cyan-dim)',
                    border: `1px solid ${loading ? 'var(--border)' : 'var(--cyan)'}`,
                    color: loading ? 'var(--text3)' : 'var(--cyan)',
                    fontFamily: 'var(--mono)', fontSize: '12px', letterSpacing: '0.1em',
                    borderRadius: '5px', cursor: loading ? 'default' : 'pointer',
                    transition: 'all 0.2s', whiteSpace: 'nowrap',
                  }}
                  onMouseEnter={e => { if (!loading) e.currentTarget.style.background = 'rgba(0,229,255,0.2)'; }}
                  onMouseLeave={e => { if (!loading) e.currentTarget.style.background = 'var(--cyan-dim)'; }}
                >
                  {loading ? `PROCESSING${dots}` : 'RUN QUERY →'}
                </button>
              </div>
              <div style={{ marginTop: '8px', fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--text3)' }}>
                ENTER to submit · Shift+Enter for newline · Ask anything — design queries, QA, general science
              </div>
            </Panel>

            {/* Error */}
            {error && (
              <Panel accent="var(--red)">
                <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--red)' }}>
                  ⚠ {error}
                </div>
              </Panel>
            )}

            {/* Loading skeleton */}
            {loading && (
              <Panel title="Processing" accent="var(--cyan)">
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--text2)' }}>
                    Running RAG retrieval + candidate search{dots}
                  </div>
                </div>
                {[80, 60, 90].map((w, i) => (
                  <div key={i} style={{ height: '8px', background: 'var(--border2)',
                    borderRadius: '4px', marginTop: '10px', width: `${w}%`,
                    animation: 'shimmer 1.5s infinite', animationDelay: `${i*0.2}s` }} />
                ))}
              </Panel>
            )}

            {/* ── Design Result ── */}
            {result && isDesign && design && (
              <>
                {/* Header row */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                  <Panel title="Target State" accent="var(--green)">
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '20px', color: 'var(--green)',
                      textShadow: '0 0 20px var(--green)' }}>
                      {design.target_name?.replace(/_/g, ' ').toUpperCase()}
                    </div>
                    <div style={{ color: 'var(--text2)', fontSize: '11px', marginTop: '4px' }}>
                      {design.num_qubits}-qubit photonic state
                    </div>
                    <div style={{ marginTop: '8px' }}>
                      <Tag color="var(--green)">{design.num_qubits} qubits</Tag>
                      <Tag color="var(--cyan)">{design.components?.length} components</Tag>
                    </div>
                  </Panel>

                  <Panel title="Fidelity & Success" accent="var(--cyan)">
                    <MetricBar label="Fidelity Estimate"       value={metrics?.fidelity_estimate}            color="var(--cyan)" />
                    <MetricBar label="Success Probability"     value={metrics?.success_probability_estimate} color="var(--green)" />
                    <MetricBar label="Simplicity"              value={metrics?.simplicity_score}             color="var(--amber)" />
                    <MetricBar label="Practicality"            value={metrics?.practicality_score}           color="var(--text2)" />
                  </Panel>

                  <Panel title="Resource Budget" accent="var(--amber)">
                    {[
                      ['SPDC Sources',   metrics?.num_spdc,       'var(--green)'],
                      ['Total Components',metrics?.num_components, 'var(--cyan)'],
                      ['Spatial Modes',  metrics?.spatial_modes,  'var(--amber)'],
                      ['Total Cost',     metrics?.total_cost,     'var(--text2)'],
                      ['Overall Score',  metrics?.overall_score,  'var(--cyan)'],
                    ].map(([label, val, color]) => (
                      <div key={label} style={{ display: 'flex', justifyContent: 'space-between',
                        fontFamily: 'var(--mono)', fontSize: '11px', marginBottom: '6px' }}>
                        <span style={{ color: 'var(--text2)' }}>{label}</span>
                        <span style={{ color }}>{val}</span>
                      </div>
                    ))}
                  </Panel>
                </div>

                {/* Circuit diagram */}
                <Panel title="Optical Circuit Diagram" accent="var(--cyan)">
                  <div style={{ padding: '10px 0', minHeight: '80px' }}>
                    <CircuitDiagram components={design.components} connections={design.connections} />
                  </div>
                  <div style={{ marginTop: '10px', fontFamily: 'var(--mono)', fontSize: '10px',
                    color: 'var(--text3)', borderTop: '1px solid var(--border2)', paddingTop: '8px' }}>
                    POST-SELECTION: <span style={{ color: 'var(--amber)' }}>{design.postselection}</span>
                  </div>
                </Panel>

                {/* Component table */}
                <Panel title="Component Manifest" accent="var(--cyan)">
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--mono)', fontSize: '11px' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                          {['#', 'Type', 'ID', 'Key Parameters'].map(h => (
                            <th key={h} style={{ textAlign: 'left', padding: '6px 12px',
                              color: 'var(--text3)', fontWeight: 400, letterSpacing: '0.1em', fontSize: '10px' }}>
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {design.components?.map((c, i) => {
                          const COMP_COLOR = {
                            SPDC: 'var(--green)', BS: 'var(--cyan)', PBS: 'var(--cyan2)',
                            HWP: 'var(--amber)', QWP: 'var(--amber)', PhaseShifter: '#bf7fff',
                            PNRDetector: 'var(--red)', PostSelection: 'var(--red)',
                            Heralding: '#ff8800',
                          };
                          const color = COMP_COLOR[c.type] || 'var(--text2)';
                          const keyParams = Object.entries(c.params || {})
                            .filter(([k]) => !['purpose','accept_condition','entangled_state','pump','degenerate','interference_mode','efficiency_assumed','output_pair','modes'].includes(k))
                            .slice(0, 3)
                            .map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed ? v.toFixed(3) : v : v}`)
                            .join('  ·  ');
                          return (
                            <tr key={c.id} style={{ borderBottom: '1px solid var(--border2)' }}
                              onMouseEnter={e => e.currentTarget.style.background = 'var(--cyan-dim)'}
                              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                              <td style={{ padding: '7px 12px', color: 'var(--text3)' }}>{i + 1}</td>
                              <td style={{ padding: '7px 12px', color }}>{c.type}</td>
                              <td style={{ padding: '7px 12px', color: 'var(--text3)', fontSize: '10px' }}>{c.id}</td>
                              <td style={{ padding: '7px 12px', color: 'var(--text2)', fontSize: '10px' }}>{keyParams || '—'}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </Panel>

                {/* Notes + Sources */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <Panel title="Design Notes" accent="var(--amber)">
                    {design.notes?.map((n, i) => (
                      <div key={i} style={{ display: 'flex', gap: '8px', marginBottom: '6px',
                        fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text2)' }}>
                        <span style={{ color: 'var(--amber)', flexShrink: 0 }}>▸</span>
                        {n}
                      </div>
                    ))}
                  </Panel>
                  <Panel title="RAG Sources" accent="var(--text2)">
                    {result.rag_context_preview?.length > 0 ? result.rag_context_preview.map((c, i) => (
                      <div key={i} style={{ marginBottom: '10px', paddingBottom: '10px',
                        borderBottom: i < result.rag_context_preview.length - 1 ? '1px solid var(--border2)' : 'none' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--cyan2)' }}>
                            {c.source}
                          </span>
                          <span style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)' }}>
                            score: {c.score}
                          </span>
                        </div>
                        <div style={{ fontSize: '10px', color: 'var(--text3)', lineHeight: 1.5,
                          maxHeight: '48px', overflow: 'hidden' }}>
                          {c.text_preview}
                        </div>
                      </div>
                    )) : (
                      <div style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text3)' }}>
                        No RAG context retrieved.
                      </div>
                    )}
                  </Panel>
                </div>
              </>
            )}

            {/* ── QA Result ── */}
            {result && isQA && (
              <Panel title={result.mode === 'general_qa' ? 'General Answer' : 'Domain Answer'}
                accent={result.mode === 'general_qa' ? 'var(--amber)' : 'var(--cyan)'}>
                <div style={{ fontFamily: 'var(--sans)', fontSize: '13px', color: 'var(--text)',
                  lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                  {result.answer}
                </div>
                {result.rag_context_preview?.length > 0 && (
                  <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--border2)' }}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--text3)',
                      letterSpacing: '0.15em', marginBottom: '8px' }}>RAG SOURCES</div>
                    {result.rag_context_preview.slice(0, 2).map((c, i) => (
                      <div key={i} style={{ marginBottom: '6px', fontFamily: 'var(--mono)', fontSize: '10px' }}>
                        <span style={{ color: 'var(--cyan2)' }}>{c.source}</span>
                        <span style={{ color: 'var(--text3)', marginLeft: '8px' }}>score: {c.score}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Panel>
            )}

            {/* ── Error from API ── */}
            {result && result.status === 'error' && (
              <Panel title="Error" accent="var(--red)">
                <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--red)',
                  marginBottom: '6px' }}>
                  {result.error_type}
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text2)' }}>
                  {result.message}
                </div>
              </Panel>
            )}

            {/* ── Empty state ── */}
            {!result && !loading && !error && (
              <Panel accent="var(--border)">
                <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                  <svg width="60" height="60" viewBox="0 0 60 60" style={{ margin: '0 auto 16px', display: 'block', opacity: 0.3 }}>
                    <circle cx="30" cy="30" r="26" fill="none" stroke="var(--cyan)" strokeWidth="1.5" strokeDasharray="6 3" />
                    <circle cx="30" cy="30" r="12" fill="none" stroke="var(--cyan)" strokeWidth="1" />
                    <circle cx="30" cy="30" r="4" fill="var(--cyan)" />
                    <line x1="4" y1="30" x2="56" y2="30" stroke="var(--cyan)" strokeWidth="0.8" />
                    <line x1="30" y1="4" x2="30" y2="56" stroke="var(--cyan)" strokeWidth="0.8" />
                  </svg>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--text3)',
                    letterSpacing: '0.1em' }}>
                    AWAITING QUERY
                  </div>
                  <div style={{ fontFamily: 'var(--sans)', fontSize: '12px', color: 'var(--text3)',
                    marginTop: '8px' }}>
                    Ask to design a quantum state or use the quick queries on the left
                  </div>
                </div>
              </Panel>
            )}
          </div>
        </main>
      </div>

      <style jsx global>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes shimmer {
          0% { opacity: 0.3; }
          50% { opacity: 0.7; }
          100% { opacity: 0.3; }
        }
      `}</style>
    </>
  );
}
