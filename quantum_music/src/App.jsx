import { useCallback, useMemo, useState } from 'react';
import Piano from './components/Piano';
import CircuitDiagram from './components/CircuitDiagram';
import GateCard from './components/GateCard';
import Controls from './components/Controls';
import SettingsPanel from './components/SettingsPanel';
import { useAudio } from './hooks/useAudio';
import { useKeyboardBindings } from './hooks/useKeyboardBindings';
import { useQuantumCircuit, MODES } from './hooks/useQuantumCircuit';
import { usePlayback } from './hooks/usePlayback';
import { GATES_BY_ID, DEFAULT_KEY_MAP } from './constants/gates';
import { FUR_ELISE } from './constants/songs';

export default function App() {
  const [bindings, setBindings] = useState(DEFAULT_KEY_MAP);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activeKeyIds, setActiveKeyIds] = useState(() => new Set());

  const { playTone } = useAudio();
  const { mode, circuit, activeGate, displayedGates, playGate, startRecording, endRecording, clearCircuit, resetAll } =
    useQuantumCircuit();

  const reverseKeyMap = useMemo(() => {
    const map = {};
    Object.entries(bindings).forEach(([pianoKeyId, char]) => {
      map[char] = pianoKeyId;
    });
    return map;
  }, [bindings]);

  const handlePress = useCallback(
    (pianoKeyId) => {
      const gateDef = GATES_BY_ID[pianoKeyId];
      if (!gateDef) return;
      playTone(gateDef.frequency);
      playGate(gateDef);
      setActiveKeyIds((prev) => {
        if (prev.has(pianoKeyId)) return prev;
        const next = new Set(prev);
        next.add(pianoKeyId);
        return next;
      });
    },
    [playTone, playGate],
  );

  const handleRelease = useCallback((pianoKeyId) => {
    setActiveKeyIds((prev) => {
      if (!prev.has(pianoKeyId)) return prev;
      const next = new Set(prev);
      next.delete(pianoKeyId);
      return next;
    });
  }, []);

  const { isPlaying, play: playSong, stop: stopSong } = usePlayback(FUR_ELISE, {
    onPress: handlePress,
    onRelease: handleRelease,
    onStart: () => {
      clearCircuit();
      startRecording();
    },
    onEnd: endRecording,
  });

  useKeyboardBindings(reverseKeyMap, {
    onPress: handlePress,
    onRelease: handleRelease,
    enabled: !settingsOpen && !isPlaying,
  });

  const handlePianoPress = useCallback((gateDef) => handlePress(gateDef.id), [handlePress]);
  const handlePianoRelease = useCallback((gateDef) => handleRelease(gateDef.id), [handleRelease]);

  const handleChangeBinding = useCallback((pianoKeyId, newChar) => {
    setBindings((prev) => {
      const next = { ...prev };
      const existingOwnerEntry = Object.entries(prev).find(
        ([id, char]) => char === newChar && id !== pianoKeyId,
      );
      if (existingOwnerEntry) {
        next[existingOwnerEntry[0]] = prev[pianoKeyId];
      }
      next[pianoKeyId] = newChar;
      return next;
    });
  }, []);

  const handleRestoreDefaults = useCallback(() => setBindings(DEFAULT_KEY_MAP), []);

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <header className="border-b-2 border-ink px-6 py-5 sm:px-10">
        <div className="mx-auto flex w-full max-w-6xl items-baseline justify-between">
          <div>
            <h1 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              Quantum Music
            </h1>
            <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.25em] text-ink-soft">
              Play the wavefunction
            </p>
          </div>
          <p className="hidden font-mono text-xs uppercase tracking-[0.2em] text-ink-soft/70 sm:block">
            q0 · q1 two-qubit register
          </p>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-6 sm:px-10 sm:py-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-stretch">
          <div className="sm:flex-1">
            {mode === MODES.FREEPLAY ? (
              <GateCard gate={activeGate} />
            ) : (
              <div className="flex h-full min-h-[9rem] flex-col justify-between rounded-sm border border-ink/15 bg-paper-dark/50 px-6 py-5">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.2em] text-rose">
                    {mode === MODES.RECORDING ? 'Recording' : 'Circuit locked'}
                  </p>
                  <h3 className="mt-1 font-display text-2xl font-semibold text-ink">
                    {circuit.length} gate{circuit.length === 1 ? '' : 's'} in circuit
                  </h3>
                </div>
                <p className="mt-3 font-display text-sm italic text-ink-soft">
                  {mode === MODES.RECORDING
                    ? 'Every key you play is appended to the circuit below.'
                    : 'Press Record to start building a new one.'}
                </p>
              </div>
            )}
          </div>
          <div className="flex items-start sm:items-center">
            <Controls
              mode={mode}
              isPlaying={isPlaying}
              onRecord={startRecording}
              onEnd={endRecording}
              onClear={clearCircuit}
              onReset={resetAll}
              onPlay={playSong}
              onStop={stopSong}
              onOpenSettings={() => setSettingsOpen(true)}
            />
          </div>
        </div>

        <CircuitDiagram gates={displayedGates} mode={mode} />

        <div className="mt-auto pt-4">
          <Piano
            keyBindings={bindings}
            activeKeyIds={activeKeyIds}
            onPress={handlePianoPress}
            onRelease={handlePianoRelease}
            disabled={isPlaying}
          />
        </div>
      </main>

      <SettingsPanel
        open={settingsOpen}
        bindings={bindings}
        onChangeBinding={handleChangeBinding}
        onRestoreDefaults={handleRestoreDefaults}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  );
}
