import { useEffect, useMemo, useRef } from 'react';
import { MODES } from '../hooks/useQuantumCircuit';

const WIRE_LABEL_WIDTH = 56;
const COL_WIDTH = 88;
const START_PAD = 40;
const END_PAD = 40;
const MIN_WIDTH = 480;
const HEIGHT = 200;
const Q0_Y = 68;
const Q1_Y = 150;

function wireY(qubit) {
  return qubit === 0 ? Q0_Y : Q1_Y;
}

function GateBox({ x, gate }) {
  const y = wireY(gate.qubits[0]);
  return (
    <g>
      <rect
        x={x - 22}
        y={y - 22}
        width={44}
        height={44}
        rx={3}
        className="fill-paper stroke-ink"
        strokeWidth={2}
      />
      <text
        x={x}
        y={y + (gate.angleLabel ? 2 : 5)}
        textAnchor="middle"
        className="fill-ink font-mono font-semibold"
        fontSize={gate.symbol.length > 1 ? 15 : 18}
      >
        {gate.symbol}
      </text>
      {gate.angleLabel && (
        <text x={x} y={y + 16} textAnchor="middle" className="fill-ink-soft font-mono" fontSize={9}>
          {gate.angleLabel}
        </text>
      )}
    </g>
  );
}

function CnotGlyph({ x }) {
  return (
    <g>
      <line x1={x} y1={Q0_Y} x2={x} y2={Q1_Y} className="stroke-ink" strokeWidth={2} />
      <circle cx={x} cy={Q0_Y} r={6} className="fill-ink" />
      <circle cx={x} cy={Q1_Y} r={15} className="fill-paper stroke-ink" strokeWidth={2} />
      <line x1={x - 10} y1={Q1_Y} x2={x + 10} y2={Q1_Y} className="stroke-ink" strokeWidth={2} />
      <line x1={x} y1={Q1_Y - 10} x2={x} y2={Q1_Y + 10} className="stroke-ink" strokeWidth={2} />
    </g>
  );
}

function CzGlyph({ x }) {
  return (
    <g>
      <line x1={x} y1={Q0_Y} x2={x} y2={Q1_Y} className="stroke-ink" strokeWidth={2} />
      <circle cx={x} cy={Q0_Y} r={6} className="fill-ink" />
      <circle cx={x} cy={Q1_Y} r={6} className="fill-ink" />
    </g>
  );
}

function SwapGlyph({ x }) {
  const arm = 9;
  return (
    <g>
      <line x1={x} y1={Q0_Y} x2={x} y2={Q1_Y} className="stroke-ink" strokeWidth={2} />
      {[Q0_Y, Q1_Y].map((y) => (
        <g key={y}>
          <line x1={x - arm} y1={y - arm} x2={x + arm} y2={y + arm} className="stroke-ink" strokeWidth={2.5} />
          <line x1={x - arm} y1={y + arm} x2={x + arm} y2={y - arm} className="stroke-ink" strokeWidth={2.5} />
        </g>
      ))}
    </g>
  );
}

function GateGlyph({ x, gate }) {
  switch (gate.visual) {
    case 'cnot':
      return <CnotGlyph x={x} />;
    case 'cz':
      return <CzGlyph x={x} />;
    case 'swap':
      return <SwapGlyph x={x} />;
    default:
      return <GateBox x={x} gate={gate} />;
  }
}

export default function CircuitDiagram({ gates, mode }) {
  const width = useMemo(() => {
    const content = WIRE_LABEL_WIDTH + START_PAD + gates.length * COL_WIDTH + END_PAD;
    return Math.max(MIN_WIDTH, content);
  }, [gates.length]);

  const wireEndX = width - 24;
  const wireStartX = WIRE_LABEL_WIDTH;

  // Keep the newest gate in view as the circuit grows past the visible
  // width -- matters most for MusicBox playback, where gates land faster
  // than a reader could manually scroll to follow them.
  const scrollRef = useRef(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ left: el.scrollWidth, behavior: 'smooth' });
  }, [gates.length]);

  return (
    <div className="relative rounded-sm border border-ink/15 bg-paper/70 bg-grain bg-grain-fine shadow-inner">
      {mode === MODES.LOCKED && (
        <div className="pointer-events-none absolute right-4 top-3 z-10 -rotate-6 select-none rounded-sm border-2 border-rose/70 px-3 py-1 font-mono text-xs font-bold uppercase tracking-[0.2em] text-rose/80">
          Circuit locked
        </div>
      )}
      {mode === MODES.RECORDING && (
        <div className="pointer-events-none absolute right-4 top-3 z-10 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-[0.2em] text-rose">
          <span className="h-2 w-2 animate-pulse rounded-full bg-rose" />
          Recording
        </div>
      )}
      <div ref={scrollRef} className="overflow-x-auto">
        <svg width={width} height={HEIGHT} role="img" aria-label="Quantum circuit diagram" className="block">
          <text x={16} y={Q0_Y + 5} className="fill-ink-soft font-mono font-semibold" fontSize={13}>
            q0
          </text>
          <text x={16} y={Q1_Y + 5} className="fill-ink-soft font-mono font-semibold" fontSize={13}>
            q1
          </text>
          <line x1={wireStartX} y1={Q0_Y} x2={wireEndX} y2={Q0_Y} className="stroke-ink-soft" strokeWidth={1.5} />
          <line x1={wireStartX} y1={Q1_Y} x2={wireEndX} y2={Q1_Y} className="stroke-ink-soft" strokeWidth={1.5} />

          {gates.length === 0 && (
            <text
              x={wireStartX + START_PAD}
              y={(Q0_Y + Q1_Y) / 2 + 5}
              className="fill-ink-soft/50 font-display italic"
              fontSize={14}
            >
              {mode === MODES.RECORDING ? 'Play a key to add the first gate…' : ''}
            </text>
          )}

          {gates.map((gate, i) => {
            const x = wireStartX + START_PAD + i * COL_WIDTH + COL_WIDTH / 2;
            return <GateGlyph key={gate.instanceId} x={x} gate={gate} />;
          })}
        </svg>
      </div>
    </div>
  );
}
