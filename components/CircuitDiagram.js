export default function CircuitDiagram({ components, connections }) {
  if (!components || components.length === 0) return null;

  const nodeW = 110, nodeH = 38, gapX = 54, gapY = 52;
  const cols = Math.min(4, components.length);
  const rows = Math.ceil(components.length / cols);
  const svgW = cols * (nodeW + gapX) + 20;
  const svgH = rows * (nodeH + gapY) + 20;

  const posMap = {};
  components.forEach((c, i) => {
    const col = i % cols, row = Math.floor(i / cols);
    posMap[c.id] = {
      x: 10 + col * (nodeW + gapX) + nodeW / 2,
      y: 10 + row * (nodeH + gapY) + nodeH / 2,
    };
  });

  const COLOR = {
    SPDC: '#00ff9d', BS: '#00e5ff', PBS: '#00b8d4',
    HWP: '#ffb700', QWP: '#ff9500', PhaseShifter: '#bf7fff',
    PNRDetector: '#ff4060', PostSelection: '#ff6688', Heralding: '#ff8800',
  };

  return (
    <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} style={{ overflow: 'visible' }}>
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="rgba(0,229,255,0.5)" />
        </marker>
      </defs>
      {connections && connections.map(([src, dst], i) => {
        const s = posMap[src], d = posMap[dst];
        if (!s || !d) return null;
        const mx = (s.x + d.x) / 2;
        return (
          <path key={i}
            d={`M${s.x},${s.y} C${mx},${s.y} ${mx},${d.y} ${d.x},${d.y}`}
            fill="none" stroke="rgba(0,229,255,0.3)" strokeWidth="1.5"
            strokeDasharray="4 3" markerEnd="url(#arrow)" />
        );
      })}
      {components.map((c) => {
        const p = posMap[c.id];
        const color = COLOR[c.type] || '#6a90b8';
        return (
          <g key={c.id} transform={`translate(${p.x - nodeW/2},${p.y - nodeH/2})`}>
            <rect width={nodeW} height={nodeH} rx="4"
              fill={`${color}18`} stroke={color} strokeWidth="1" />
            <text x={nodeW/2} y={nodeH/2 - 4} textAnchor="middle"
              fill={color} fontSize="10" fontFamily="'Share Tech Mono',monospace" fontWeight="700">
              {c.type}
            </text>
            <text x={nodeW/2} y={nodeH/2 + 9} textAnchor="middle"
              fill="rgba(200,221,240,0.4)" fontSize="7.5" fontFamily="'Share Tech Mono',monospace">
              {c.id.split('_').pop()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
