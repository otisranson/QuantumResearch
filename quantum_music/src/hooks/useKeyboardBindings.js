import { useEffect, useRef } from 'react';

// Attaches global keydown/keyup listeners that translate a physical key
// into a piano-key id via `keyMap` (keyboard char -> piano key id).
// Cleans up listeners on unmount or whenever inputs change.
export function useKeyboardBindings(keyMap, { onPress, onRelease, enabled = true } = {}) {
  const heldKeys = useRef(new Set());

  useEffect(() => {
    if (!enabled) return undefined;

    function handleKeyDown(e) {
      if (e.repeat) return;
      const key = e.key.toLowerCase();
      const pianoKeyId = keyMap[key];
      if (!pianoKeyId || heldKeys.current.has(key)) return;
      heldKeys.current.add(key);
      onPress?.(pianoKeyId);
    }

    function handleKeyUp(e) {
      const key = e.key.toLowerCase();
      heldKeys.current.delete(key);
      const pianoKeyId = keyMap[key];
      if (pianoKeyId) onRelease?.(pianoKeyId);
    }

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    const keys = heldKeys.current;
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      keys.clear();
    };
  }, [keyMap, onPress, onRelease, enabled]);
}
