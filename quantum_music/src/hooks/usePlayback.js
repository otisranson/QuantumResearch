import { useCallback, useEffect, useRef, useState } from 'react';

// Steps through `song.notes` (a `{ keyId, duration }` sequence, keyId null
// for a rest) on a timer, calling onPress/onRelease exactly like a live key
// press would -- so playback reuses the same tone-playing, gate-recording,
// and highlighting logic as playing the piano by hand, instead of
// duplicating any of it here.
export function usePlayback(song, { onPress, onRelease, onStart, onEnd }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const timeoutRef = useRef(null);
  const cancelledRef = useRef(false);

  const stop = useCallback(() => {
    cancelledRef.current = true;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  const play = useCallback(() => {
    cancelledRef.current = false;
    setIsPlaying(true);
    onStart?.();

    const notes = song.notes;
    const step = (index) => {
      if (cancelledRef.current || index >= notes.length) {
        setIsPlaying(false);
        if (!cancelledRef.current) onEnd?.();
        return;
      }
      const { keyId, duration } = notes[index];
      if (keyId) onPress(keyId);
      timeoutRef.current = setTimeout(() => {
        if (keyId) onRelease(keyId);
        step(index + 1);
      }, duration * 1000);
    };
    step(0);
  }, [song, onPress, onRelease, onStart, onEnd]);

  // Stop any pending step if the component unmounts mid-playback.
  useEffect(() => () => stop(), [stop]);

  return { isPlaying, play, stop };
}
