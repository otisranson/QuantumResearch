import { useEffect, useState } from 'react';
import { PIANO_KEYS } from '../constants/gates';

export default function SettingsPanel({ open, bindings, onChangeBinding, onRestoreDefaults, onClose }) {
  const [listeningFor, setListeningFor] = useState(null);

  function handleClose() {
    setListeningFor(null);
    onClose();
  }

  useEffect(() => {
    if (!listeningFor) return undefined;

    function handleKeyDown(e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.key === 'Escape') {
        setListeningFor(null);
        return;
      }
      onChangeBinding(listeningFor, e.key.toLowerCase());
      setListeningFor(null);
    }

    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [listeningFor, onChangeBinding]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 px-4 backdrop-blur-[2px]"
      onClick={handleClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-sm border-2 border-ink bg-paper p-6 shadow-2xl sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl font-semibold text-ink">Key Bindings</h2>
            <p className="mt-1 font-display text-sm italic text-ink-soft">
              Click a binding, then press any key to remap it.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close settings"
            className="rounded-full border border-ink-soft/40 px-2.5 py-1 font-mono text-sm text-ink-soft hover:border-rose hover:text-rose"
          >
            ×
          </button>
        </div>

        <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          {PIANO_KEYS.map((gateDef) => {
            const isListening = listeningFor === gateDef.id;
            return (
              <div
                key={gateDef.id}
                className="flex items-center justify-between gap-3 rounded-sm border border-ink/15 bg-paper-dark/40 px-3 py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <span
                    className={`inline-block h-3.5 w-3.5 shrink-0 rounded-sm border border-ink ${
                      gateDef.type === 'white' ? 'bg-paper' : 'bg-ink'
                    }`}
                  />
                  <div>
                    <p className="font-mono text-sm font-semibold text-ink">{gateDef.symbol}</p>
                    <p className="font-display text-xs text-ink-soft">{gateDef.fullName}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setListeningFor(gateDef.id)}
                  className={`min-w-[6.5rem] rounded-sm border px-3 py-1.5 font-mono text-xs uppercase tracking-wide transition-colors ${
                    isListening
                      ? 'animate-pulse border-brass bg-brass-light/20 text-brass'
                      : 'border-ink-soft/40 text-ink hover:border-brass hover:text-brass'
                  }`}
                >
                  {isListening ? 'Press a key…' : bindings[gateDef.id]}
                </button>
              </div>
            );
          })}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onRestoreDefaults}
            className="rounded-sm border border-ink-soft/50 px-4 py-2 font-mono text-xs uppercase tracking-[0.15em] text-ink-soft hover:bg-ink/5"
          >
            Restore Defaults
          </button>
        </div>
      </div>
    </div>
  );
}
