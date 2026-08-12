export default function PianoKey({
  gateDef,
  keyBinding,
  isActive,
  onPress,
  onRelease,
  style,
  className = '',
  disabled = false,
}) {
  const isWhite = gateDef.type === 'white';
  const symbolSize = gateDef.symbol.length > 2 ? 'text-sm' : 'text-lg';

  function handleDown(e) {
    e.preventDefault();
    if (disabled) return;
    onPress(gateDef);
  }

  const baseWhite =
    'relative flex flex-1 select-none flex-col items-center justify-end rounded-b-md border border-ink/30 bg-paper pb-4 pt-2 shadow-key transition-transform duration-75 ease-out';
  const activeWhite = 'translate-y-1 border-brass bg-brass-light/25 shadow-none';

  const baseBlack =
    'absolute top-0 z-10 flex h-[60%] select-none flex-col items-center justify-end rounded-b-md border border-ink bg-ink pb-3 shadow-key-black transition-transform duration-75 ease-out';
  const activeBlack = 'translate-y-1 border-brass-light bg-ink/80 shadow-none';

  return (
    <button
      type="button"
      aria-label={`${gateDef.fullName} (${gateDef.symbol})`}
      disabled={disabled}
      onPointerDown={handleDown}
      onPointerUp={() => onRelease(gateDef)}
      onPointerLeave={() => onRelease(gateDef)}
      onPointerCancel={() => onRelease(gateDef)}
      onContextMenu={(e) => e.preventDefault()}
      style={style}
      className={`${isWhite ? baseWhite : baseBlack} ${isActive ? (isWhite ? activeWhite : activeBlack) : ''} ${className} disabled:cursor-not-allowed disabled:opacity-60`}
    >
      <span
        className={`absolute right-1.5 top-1.5 font-mono text-[10px] uppercase tracking-wide ${
          isWhite ? 'text-ink-soft/60' : 'text-paper/50'
        }`}
      >
        {keyBinding}
      </span>
      <span
        className={`font-mono font-semibold ${symbolSize} ${isWhite ? 'text-ink' : 'text-paper'}`}
      >
        {gateDef.symbol}
      </span>
    </button>
  );
}
