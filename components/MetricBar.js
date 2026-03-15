export default function MetricBar({ label, value, color = 'var(--cyan)' }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'4px' }}>
        <span style={{ fontFamily:'var(--mono)', fontSize:'11px', color:'var(--text2)' }}>{label}</span>
        <span style={{ fontFamily:'var(--mono)', fontSize:'11px', color }}>{pct}%</span>
      </div>
      <div style={{ height:'4px', background:'var(--border2)', borderRadius:'2px', overflow:'hidden' }}>
        <div style={{
          height:'100%', width:`${pct}%`, background: color,
          borderRadius:'2px', boxShadow:`0 0 8px ${color}`,
          transition:'width 0.8s cubic-bezier(0.4,0,0.2,1)'
        }} />
      </div>
    </div>
  );
}
