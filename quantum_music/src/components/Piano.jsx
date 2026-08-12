import { WHITE_KEYS, BLACK_KEYS } from '../constants/gates';
import PianoKey from './PianoKey';

const BLACK_KEY_WIDTH_PCT = 8.5;

export default function Piano({ keyBindings, activeKeyIds, onPress, onRelease, disabled = false }) {
  return (
    <div className="relative flex h-40 w-full select-none gap-[2px] sm:h-48 md:h-56">
      {WHITE_KEYS.map((gateDef) => (
        <PianoKey
          key={gateDef.id}
          gateDef={gateDef}
          keyBinding={keyBindings[gateDef.id]}
          isActive={activeKeyIds.has(gateDef.id)}
          onPress={onPress}
          onRelease={onRelease}
          disabled={disabled}
        />
      ))}

      {BLACK_KEYS.map((gateDef) => {
        const leftPct = ((gateDef.whiteIndex + 1) / WHITE_KEYS.length) * 100 - BLACK_KEY_WIDTH_PCT / 2;
        return (
          <PianoKey
            key={gateDef.id}
            gateDef={gateDef}
            keyBinding={keyBindings[gateDef.id]}
            isActive={activeKeyIds.has(gateDef.id)}
            onPress={onPress}
            onRelease={onRelease}
            disabled={disabled}
            style={{ left: `${leftPct}%`, width: `${BLACK_KEY_WIDTH_PCT}%` }}
          />
        );
      })}
    </div>
  );
}
