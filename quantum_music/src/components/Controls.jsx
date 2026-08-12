import { MODES } from '../hooks/useQuantumCircuit';

function GearIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3.2" />
      <path
        d="M12 2.5v2.4M12 19.1v2.4M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.9 19.1l1.7-1.7M17.4 6.6l1.7-1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

const baseBtn =
  'font-mono text-xs uppercase tracking-[0.15em] px-4 py-2.5 rounded-sm border transition-colors duration-100 disabled:cursor-not-allowed disabled:opacity-35';

export default function Controls({
  mode,
  isPlaying,
  onRecord,
  onEnd,
  onClear,
  onReset,
  onPlay,
  onStop,
  onOpenSettings,
}) {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <button
        type="button"
        onClick={onRecord}
        disabled={mode === MODES.RECORDING || isPlaying}
        className={`${baseBtn} border-rose text-rose hover:bg-rose/10`}
      >
        ● Record
      </button>
      <button
        type="button"
        onClick={onEnd}
        disabled={mode !== MODES.RECORDING || isPlaying}
        className={`${baseBtn} border-ink text-ink hover:bg-ink/5`}
      >
        ■ End
      </button>
      <button
        type="button"
        onClick={onClear}
        disabled={isPlaying}
        className={`${baseBtn} border-ink-soft/50 text-ink-soft hover:bg-ink/5`}
      >
        Clear
      </button>
      <button
        type="button"
        onClick={onReset}
        disabled={isPlaying}
        className={`${baseBtn} border-ink-soft/50 text-ink-soft hover:bg-ink/5`}
      >
        Reset
      </button>
      <button
        type="button"
        onClick={onPlay}
        disabled={isPlaying || mode === MODES.RECORDING}
        className={`${baseBtn} border-brass text-brass hover:bg-brass/10`}
      >
        ♪ Play Für Elise
      </button>
      <button
        type="button"
        onClick={onStop}
        disabled={!isPlaying}
        className={`${baseBtn} border-ink text-ink hover:bg-ink/5`}
      >
        ■ Stop
      </button>
      <button
        type="button"
        onClick={onOpenSettings}
        aria-label="Open settings"
        className="ml-1 flex items-center justify-center rounded-full border border-ink-soft/40 p-2.5 text-ink-soft transition-colors duration-100 hover:border-brass hover:text-brass"
      >
        <GearIcon />
      </button>
    </div>
  );
}
