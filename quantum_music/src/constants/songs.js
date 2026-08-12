// A short, hand-transcribed excerpt from the opening theme of Beethoven's
// "Für Elise" (WoO 59, public domain), simplified to fit this app's twelve
// pitch-class gates: octave is dropped entirely: since the piano here is a
// single fixed octave (see gates.js), every note collapses to whichever of
// the 12 keys shares its pitch class. This reproduces the well-known
// melodic contour and rhythm of the opening theme, not a note-for-note
// facsimile of the manuscript. The eight-bar theme genuinely is stated
// twice near the very start of the real piece, which is what THEME_A being
// repeated below reflects.

import { PIANO_KEYS } from './gates';

const SIXTEENTH = 0.2;
const EIGHTH = 0.4;
const QUARTER = 0.8;

// [pianoKeyId | null for a rest, duration in seconds]
const THEME_A = [
  ['E', SIXTEENTH], ['Dsharp', SIXTEENTH], ['E', SIXTEENTH], ['Dsharp', SIXTEENTH], ['E', SIXTEENTH],
  ['B', EIGHTH], ['D', EIGHTH], ['C', EIGHTH], ['A', EIGHTH],
  [null, EIGHTH],
  ['C', EIGHTH], ['E', EIGHTH], ['A', EIGHTH], ['B', EIGHTH],
  [null, EIGHTH],
  ['E', EIGHTH], ['Gsharp', EIGHTH], ['B', EIGHTH], ['C', EIGHTH],
  [null, EIGHTH],
  ['E', SIXTEENTH], ['Dsharp', SIXTEENTH], ['E', SIXTEENTH], ['Dsharp', SIXTEENTH], ['E', SIXTEENTH],
  ['B', EIGHTH], ['D', EIGHTH], ['C', EIGHTH], ['A', EIGHTH],
  [null, QUARTER],
];

// Catches a typo'd key id immediately at module load, rather than a silent
// no-op key press at playback time.
const VALID_KEY_IDS = new Set(PIANO_KEYS.map((k) => k.id));
THEME_A.forEach(([keyId]) => {
  if (keyId !== null && !VALID_KEY_IDS.has(keyId)) {
    throw new Error(`songs.js: unknown piano key id ${keyId}`);
  }
});

export const FUR_ELISE = {
  title: "Für Elise (opening theme, Beethoven, public domain)",
  notes: [...THEME_A, ...THEME_A].map(([keyId, duration]) => ({ keyId, duration })),
};
