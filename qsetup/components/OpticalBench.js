import { useEffect, useRef, useState } from 'react';

// ── Physics-accurate component shapes ─────────────────────────────────────
// Each component is drawn at correct optical conventions:
// SPDC: nonlinear crystal (parallelogram) with pump in/signal+idler out
// BS: tilted 45° partially silvered plate
// PBS: cube with diagonal
// HWP/QWP: thin plate with orientation marks
// PhaseShifter: thin plate with phase lines
// PNRDetector/ThresholdDetector: D-shaped detector housing
// Heralding/PostSelection: coincidence logic box
// CrossKerr: crystal with two modes
// VacuumAncilla: vacuum port symbol

const COMP_COLORS = {
  SPDC:             { fill: '#ff9f0a22', stroke: '#ff9f0a', label: '#ff9f0a' },
  BS:               { fill: '#0a84ff22', stroke: '#0a84ff', label: '#0a84ff' },
  PBS:              { fill: '#30d15822', stroke: '#30d158', label: '#30d158' },
  HWP:              { fill: '#bf5af222', stroke: '#bf5af2', label: '#bf5af2' },
  QWP:              { fill: '#5e5ce622', stroke: '#5e5ce6', label: '#5e5ce6' },
  PhaseShifter:     { fill: '#ff375f22', stroke: '#ff375f', label: '#ff375f' },
  PNRDetector:      { fill: '#64d2ff22', stroke: '#64d2ff', label: '#64d2ff' },
  ThresholdDetector:{ fill: '#2ac9de22', stroke: '#2ac9de', label: '#2ac9de' },
  PostSelection:    { fill: '#ffd60a22', stroke: '#ffd60a', label: '#ffd60a' },
  Heralding:        { fill: '#ff6b0022', stroke: '#ff6b00', label: '#ff6b00' },
  CrossKerr:        { fill: '#ff375f22', stroke: '#ff375f', label: '#ff375f' },
  VacuumAncilla:    { fill: '#6e6e7322', stroke: '#6e6e73', label: '#6e6e73' },
};

function drawComponent(type, x, y, params = {}, isDark) {
  const c = COMP_COLORS[type] || { fill: '#88888822', stroke: '#888888', label: '#888888' };
  const s = c.stroke;
  const f = c.fill;
  const lw = 1.5;

  switch (type) {
    case 'SPDC': {
      // Nonlinear crystal: parallelogram tilted 10°
      const w = 44, h = 28;
      const skew = 8;
      return (
        <g transform={`translate(${x},${y})`}>
          {/* Crystal body */}
          <polygon
            points={`${-w/2+skew},${-h/2} ${w/2+skew},${-h/2} ${w/2-skew},${h/2} ${-w/2-skew},${h/2}`}
            fill={f} stroke={s} strokeWidth={lw}
          />
          {/* Internal lattice lines */}
          {[-10, 0, 10].map(dx => (
            <line key={dx} x1={dx-4} y1={-h/2+4} x2={dx+4} y2={h/2-4}
              stroke={s} strokeWidth={0.5} strokeOpacity={0.5} />
          ))}
          {/* Pump arrow in */}
          <line x1={-w/2-16} y1={0} x2={-w/2} y2={0} stroke={s} strokeWidth={1.5}
            markerEnd={`url(#arrow-${type})`} />
          {/* Signal out (top) */}
          <line x1={w/2} y1={0} x2={w/2+14} y2={-10} stroke={s} strokeWidth={1.2}
            strokeDasharray="3 2" />
          {/* Idler out (bottom) */}
          <line x1={w/2} y1={0} x2={w/2+14} y2={10} stroke={s} strokeWidth={1.2}
            strokeDasharray="3 2" />
          {/* Label */}
          <text x={0} y={h/2+14} textAnchor="middle" fill={c.label}
            fontSize={9} fontFamily="'DM Mono',monospace" fontWeight="500">SPDC</text>
          <text x={0} y={h/2+24} textAnchor="middle" fill={c.label}
            fontSize={7.5} fontFamily="'DM Mono',monospace" opacity={0.7}>
            {params.crystal || 'BBO'} {params.type || 'Type-II'}
          </text>
        </g>
      );
    }

    case 'BS': {
      // 50:50 beam splitter: thin plate at 45°
      const w = 6, h = 36;
      return (
        <g transform={`translate(${x},${y}) rotate(-45)`}>
          <rect x={-w/2} y={-h/2} width={w} height={h}
            fill={f} stroke={s} strokeWidth={lw} rx={1} />
          {/* Partial silvering marks */}
          {[-12,-6,0,6,12].map(dy => (
            <line key={dy} x1={-w/2} y1={dy} x2={w/2} y2={dy}
              stroke={s} strokeWidth={0.4} strokeOpacity={0.5} />
          ))}
          <text x={0} y={-h/2-6} textAnchor="middle" fill={c.label}
            fontSize={9} fontFamily="'DM Mono',monospace" fontWeight="500"
            transform="rotate(45)">BS</text>
        </g>
      );
    }

    case 'PBS': {
      // Polarizing beam splitter: cube with diagonal
      const sz = 30;
      return (
        <g transform={`translate(${x},${y})`}>
          <rect x={-sz/2} y={-sz/2} width={sz} height={sz}
            fill={f} stroke={s} strokeWidth={lw} />
          {/* PBS diagonal */}
          <line x1={-sz/2} y1={-sz/2} x2={sz/2} y2={sz/2}
            stroke={s} strokeWidth={1.8} />
          {/* H transmission arrow */}
          <line x1={sz/2} y1={0} x2={sz/2+14} y2={0}
            stroke={s} strokeWidth={1.2} />
          {/* V reflection arrow */}
          <line x1={0} y1={-sz/2} x2={0} y2={-sz/2-14}
            stroke={s} strokeWidth={1.2} strokeDasharray="3 2" />
          <text x={0} y={sz/2+14} textAnchor="middle" fill={c.label}
            fontSize={9} fontFamily="'DM Mono',monospace" fontWeight="500">PBS</text>
        </g>
      );
    }

    case 'HWP': {
      // Half-wave plate: thin plate with λ/2 symbol, tilted at angle
      const angle = params.angle_deg || 22.5;
      const w = 6, h = 34;
      return (
        <g transform={`translate(${x},${y}) rotate(${angle})`}>
          <rect x={-w/2} y={-h/2} width={w} height={h}
            fill={f} stroke={s} strokeWidth={lw} rx={1} />
          {/* Birefringence lines */}
          {[-10,-4,2,8].map(dy => (
            <line key={dy} x1={-w/2+1} y1={dy} x2={w/2-1} y2={dy+4}
              stroke={s} strokeWidth={0.5} strokeOpacity={0.6} />
          ))}
          <text x={0} y={-h/2-6} textAnchor="middle" fill={c.label}
            fontSize={9} fontFamily="'DM Mono',monospace" fontWeight="500"
            transform={`rotate(${-angle})`}>HWP</text>
          <text x={0} y={h/2+14} textAnchor="middle" fill={c.label}
            fontSize={7.5} fontFamily="'DM Mono',monospace" opacity={0.7}
            transform={`rotate(${-angle})`}>{angle}°</text>
        </g>
      );
    }

    case 'QWP': {
      const angle = params.angle_deg || 45;
      const w = 6, h = 34;
      return (
        <g transform={`translate(${x},${y}) rotate(${angle})`}>
          <rect x={-w/2} y={-h/2} width={w} height={h}
            fill={f} stroke={s} strokeWidth={lw} rx={1} />
          {[-10,-3,4,11].map(dy => (
            <line key={dy} x1={-w/2+1} y1={dy} x2={w/2-1} y2={dy+2}
              stroke={s} strokeWidth={0.5} strokeOpacity={0.6} />
          ))}
          <text x={0} y={-h/2-6} textAnchor="middle" fill={c.label}
            fontSize={9} fontFamily="'DM Mono',monospace" fontWeight="500"
            transform={`rotate(${-angle})`}>QWP</text>
          <text x={0} y={h/2+14} textAnchor="middle" fill={c.label}
            fontSize={7.5} fontFamily="'DM Mono',monospace" opacity={0.7}
            transform={`rotate(${-angle})`}>{angle}°</text>
        </g>
      );
    }

    case 'PhaseShifter': {
      const phase = params.phase_deg || 180;
      const w = 8, h = 32;
      return (
        <g transform={`translate(${x},${y})`}>
          <rect x={-w/2} y={-h/2} width={w} height={h}
            fill={f} stroke={s} strokeWidth={lw} rx={2} />
          {/* Phase wave indicator */}
          <path d={`M${-w/2+1},-8 Q0,-4 ${w/2-1},-8 Q0,-12 ${-w/2+1},-8`}
            fill="none" stroke={s} strokeWidth={0.8} />
          <path d={`M${-w/2+1},4 Q0,8 ${w/2-1},4 Q0,0 ${-w/2+1},4`}
            fill="none" stroke={s} strokeWidth={0.8} />
          <text x={0} y={-h/2-6} textAnchor="middle" fill={c.label}
            fontSize={9} fontFamily="'DM Mono',monospace" fontWeight="500">φ</text>
          <text x={0} y={h/2+14} textAnchor="middle" fill={c.label}
            fontSize={7.5} fontFamily="'DM Mono',monospace" opacity={0.7}>{phase}°</text>
        </g>
      );
    }

    case 'PNRDetector':
    case 'ThresholdDetector': {
      const label = type === 'PNRDetector' ? 'PNR' : 'TD';
      return (
        <g transform={`translate(${x},${y})`}>
          {/* D-shaped detector housing */}
          <path d={`M-10,-16 L10,-16 A16,16 0 0,1 10,16 L-10,16 Z`}
            fill={f} stroke={s} strokeWidth={lw} />
          {/* Active area */}
          <ellipse cx={4} cy={0} rx={6} ry={8} fill={s} opacity={0.3} />
          <ellipse cx={4} cy={0} rx={3} ry={4} fill={s} opacity={0.6} />
          {/* Click lines */}
          <line x1={-10} y1={-6} x2={-18} y2={-10} stroke={s} strokeWidth={0.8} />
          <line x1={-10} y1={0}  x2={-18} y2={0}   stroke={s} strokeWidth={0.8} />
          <line x1={-10} y1={6}  x2={-18} y2={10}  stroke={s} strokeWidth={0.8} />
          <text x={0} y={24} textAnchor="middle" fill={c.label}
            fontSize={9} fontFamily="'DM Mono',monospace" fontWeight="500">{label}</text>
        </g>
      );
    }

    case 'PostSelection':
    case 'Heralding': {
      const label = type === 'PostSelection' ? '&' : 'H';
      const rule = params.rule || (type === 'PostSelection' ? 'coincidence' : 'herald');
      return (
        <g transform={`translate(${x},${y})`}>
          <rect x={-22} y={-16} width={44} height={32}
            fill={f} stroke={s} strokeWidth={lw} rx={6} />
          {/* AND gate symbol */}
          <text x={0} y={5} textAnchor="middle" fill={s}
            fontSize={14} fontFamily="'DM Mono',monospace" fontWeight="700">{label}</text>
          <text x={0} y={24} textAnchor="middle" fill={c.label}
            fontSize={7.5} fontFamily="'DM Mono',monospace" opacity={0.8}>
            {type === 'PostSelection' ? 'POST-SEL' : 'HERALD'}
          </text>
        </g>
      );
    }

    case 'CrossKerr': {
      const w = 40, h = 26;
      return (
        <g transform={`translate(${x},${y})`}>
          <rect x={-w/2} y={-h/2} width={w} height={h}
            fill={f} stroke={s} strokeWidth={lw} rx={3} />
          {/* χ(3) symbol */}
          <text x={0} y={5} textAnchor="middle" fill={s}
            fontSize={11} fontFamily="'DM Mono',monospace">χ⁽³⁾</text>
          {/* Two mode lines */}
          <line x1={-w/2-12} y1={-6} x2={-w/2} y2={-6} stroke={s} strokeWidth={1} />
          <line x1={-w/2-12} y1={6}  x2={-w/2} y2={6}  stroke={s} strokeWidth={1} strokeDasharray="2 1" />
          <text x={0} y={h/2+14} textAnchor="middle" fill={c.label}
            fontSize={8} fontFamily="'DM Mono',monospace">Cross-Kerr</text>
        </g>
      );
    }

    case 'VacuumAncilla': {
      return (
        <g transform={`translate(${x},${y})`}>
          <circle cx={0} cy={0} r={14} fill={f} stroke={s} strokeWidth={lw} />
          <text x={0} y={4} textAnchor="middle" fill={s}
            fontSize={10} fontFamily="'DM Mono',monospace">|0⟩</text>
          <text x={0} y={24} textAnchor="middle" fill={c.label}
            fontSize={8} fontFamily="'DM Mono',monospace">vacuum</text>
        </g>
      );
    }

    default:
      return (
        <g transform={`translate(${x},${y})`}>
          <rect x={-20} y={-14} width={40} height={28}
            fill={f} stroke={s} strokeWidth={lw} rx={4} />
          <text x={0} y={4} textAnchor="middle" fill={c.label}
            fontSize={8} fontFamily="'DM Mono',monospace">{type}</text>
        </g>
      );
  }
}

// ── Photon beam path between components ───────────────────────────────────
function PhotonBeam({ x1, y1, x2, y2, animated, color = '#0a84ff', idx = 0 }) {
  const mid = { x: (x1 + x2) / 2, y: (y1 + y2) / 2 };
  const len = Math.sqrt((x2-x1)**2 + (y2-y1)**2);
  const id = `beam-${idx}`;
  return (
    <g>
      <defs>
        <marker id={`arrowhead-${idx}`} markerWidth="6" markerHeight="6"
          refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill={color} opacity={0.7} />
        </marker>
      </defs>
      {/* Base beam */}
      <line x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={color} strokeWidth={1.2} opacity={0.25}
        strokeDasharray="4 3" />
      {/* Animated photon */}
      {animated && (
        <circle r={3} fill={color} opacity={0.9}>
          <animateMotion dur={`${1.2 + idx * 0.3}s`} repeatCount="indefinite"
            path={`M${x1},${y1} L${x2},${y2}`} />
          <animate attributeName="opacity" values="0;1;0"
            dur={`${1.2 + idx * 0.3}s`} repeatCount="indefinite" />
          <animate attributeName="r" values="2;4;2"
            dur={`${1.2 + idx * 0.3}s`} repeatCount="indefinite" />
        </circle>
      )}
      {/* Arrow */}
      <line x1={mid.x - (x2-x1)*0.05} y1={mid.y - (y2-y1)*0.05}
            x2={mid.x + (x2-x1)*0.05} y2={mid.y + (y2-y1)*0.05}
        stroke={color} strokeWidth={1.5} opacity={0.6}
        markerEnd={`url(#arrowhead-${idx})`} />
    </g>
  );
}

// ── Main optical bench layout ──────────────────────────────────────────────
export default function OpticalBench({ components, connections, animatePhotons, isDark }) {
  if (!components || components.length === 0) return null;

  const PADDING   = 80;
  const COMP_W    = 100;  // horizontal spacing
  const COMP_H    = 90;   // vertical spacing
  const MAX_COLS  = 5;

  // Layout: group by type role
  const sources   = components.filter(c => c.type === 'SPDC' || c.type === 'VacuumAncilla');
  const optics    = components.filter(c => ['BS','PBS','HWP','QWP','PhaseShifter','CrossKerr'].includes(c.type));
  const detectors = components.filter(c => ['PNRDetector','ThresholdDetector','PostSelection','Heralding'].includes(c.type));

  // Build position map
  const posMap = {};
  let col = 0;

  // Sources column
  sources.forEach((c, i) => {
    posMap[c.id] = { x: PADDING + col * COMP_W, y: PADDING + i * COMP_H };
  });
  if (sources.length) col++;

  // Optics columns
  const oCols = Math.ceil(optics.length / 2);
  for (let ci = 0; ci < oCols; ci++) {
    const batch = optics.slice(ci * 2, ci * 2 + 2);
    batch.forEach((c, ri) => {
      posMap[c.id] = { x: PADDING + col * COMP_W, y: PADDING + ri * COMP_H };
    });
    col++;
  }

  // Detectors column
  detectors.forEach((c, i) => {
    posMap[c.id] = { x: PADDING + col * COMP_W, y: PADDING + i * COMP_H };
  });

  // Fallback: place any unmapped components
  components.forEach((c, i) => {
    if (!posMap[c.id]) {
      posMap[c.id] = {
        x: PADDING + (i % MAX_COLS) * COMP_W,
        y: PADDING + Math.floor(i / MAX_COLS) * COMP_H,
      };
    }
  });

  // SVG dimensions
  const xs = Object.values(posMap).map(p => p.x);
  const ys = Object.values(posMap).map(p => p.y);
  const svgW = Math.max(...xs) + PADDING + 60;
  const svgH = Math.max(...ys) + PADDING + 60;

  // Beam colors by type
  const getBeamColor = (srcType) => {
    if (srcType === 'SPDC') return '#ff9f0a';
    if (['BS','PBS'].includes(srcType)) return '#0a84ff';
    if (['HWP','QWP'].includes(srcType)) return '#bf5af2';
    return '#6e6e73';
  };

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg
        width="100%"
        viewBox={`0 0 ${svgW} ${svgH}`}
        style={{ minWidth: `${svgW}px`, display: 'block' }}
      >
        <defs>
          {/* Glow filters */}
          {Object.entries(COMP_COLORS).map(([type, c]) => (
            <filter key={type} id={`glow-${type}`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          ))}
          {/* Optical table background grid */}
          <pattern id="grid" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="10" cy="10" r="0.8"
              fill={isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)'} />
          </pattern>
        </defs>

        {/* Optical table surface */}
        <rect x={0} y={0} width={svgW} height={svgH}
          fill={isDark ? '#0a0a0a' : '#f9f9fb'} rx={12} />
        <rect x={0} y={0} width={svgW} height={svgH}
          fill="url(#grid)" rx={12} />

        {/* Table border */}
        <rect x={1} y={1} width={svgW-2} height={svgH-2}
          fill="none"
          stroke={isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'}
          strokeWidth={1} rx={12} />

        {/* Optical rail line */}
        <line x1={PADDING - 30} y1={PADDING + (sources.length - 1) * COMP_H / 2}
              x2={Math.max(...xs) + 40}
              y2={PADDING + (sources.length - 1) * COMP_H / 2}
          stroke={isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'}
          strokeWidth={20} />

        {/* Photon beams */}
        {(connections || []).map(([srcId, dstId], i) => {
          const sp = posMap[srcId], dp = posMap[dstId];
          if (!sp || !dp) return null;
          const srcComp = components.find(c => c.id === srcId);
          const color = getBeamColor(srcComp?.type || '');
          return (
            <PhotonBeam key={i} x1={sp.x} y1={sp.y} x2={dp.x} y2={dp.y}
              animated={animatePhotons} color={color} idx={i} />
          );
        })}

        {/* Components */}
        {components.map((comp) => {
          const p = posMap[comp.id];
          if (!p) return null;
          return (
            <g key={comp.id} filter={`url(#glow-${comp.type})`}>
              {drawComponent(comp.type, p.x, p.y, comp.params || {}, isDark)}
            </g>
          );
        })}

        {/* "OPTICAL BENCH" label */}
        <text x={12} y={svgH - 10}
          fill={isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)'}
          fontSize={8} fontFamily="'DM Mono',monospace" letterSpacing={2}>
          OPTICAL BENCH
        </text>
      </svg>
    </div>
  );
}
