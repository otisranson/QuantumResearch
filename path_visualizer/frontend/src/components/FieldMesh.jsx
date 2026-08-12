import { useEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { GRID_SIZE } from "../constants.js";

// Passthrough vertex shader: no camera needed at all. Writing clip-space
// position directly (bypassing projectionMatrix/modelViewMatrix) turns the
// 2x2 plane into a fixed fullscreen quad regardless of any camera the
// <Canvas> happens to be using.
const VERTEX_SHADER = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

// Deep navy/purple at low amplitude -> cyan -> white at high amplitude,
// per the design spec. Piecewise-linear across 4 stops (not a chained
// smoothstep mix, which double-blends at the seams).
const FRAGMENT_SHADER = `
uniform sampler2D uField;
varying vec2 vUv;

vec3 colorRamp(float t) {
  vec3 c0 = vec3(0.02, 0.02, 0.06);
  vec3 c1 = vec3(0.16, 0.09, 0.42);
  vec3 c2 = vec3(0.13, 0.83, 0.93);
  vec3 c3 = vec3(1.0, 1.0, 1.0);
  if (t < 0.35) {
    return mix(c0, c1, t / 0.35);
  } else if (t < 0.7) {
    return mix(c1, c2, (t - 0.35) / 0.35);
  }
  return mix(c2, c3, (t - 0.7) / 0.3);
}

void main() {
  float v = texture2D(uField, vUv).r;
  gl_FragColor = vec4(colorRamp(v), 1.0);
}
`;

export default function FieldMesh({ field }) {
  const invalidate = useThree((state) => state.invalidate);

  // Created once and mutated in place on every field update, rather than
  // reconstructed, to avoid reallocating a GPU texture on every debounced
  // fetch. Uint8Array + UnsignedByteType (not a float texture) is
  // universally filterable in WebGL2 with no extension gotchas -- the
  // GPU's bilinear filtering is what smooths our sparse per-path-point
  // rasterization into a continuous-looking field.
  const texture = useMemo(() => {
    const data = new Uint8Array(GRID_SIZE * GRID_SIZE);
    const tex = new THREE.DataTexture(data, GRID_SIZE, GRID_SIZE, THREE.RedFormat, THREE.UnsignedByteType);
    // Explicit, not left to the three.js default (which has differed
    // across versions) -- see utils/domain.js for the full convention
    // this ties into (backend row 0 <-> y=-1 <-> screen bottom).
    tex.flipY = false;
    tex.minFilter = THREE.LinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.needsUpdate = true;
    return tex;
  }, []);

  useEffect(() => () => texture.dispose(), [texture]);

  useEffect(() => {
    if (!field) return;
    const data = texture.image.data;
    let i = 0;
    for (let row = 0; row < GRID_SIZE; row++) {
      const srcRow = field[row];
      for (let col = 0; col < GRID_SIZE; col++) {
        // Intentional in-place mutation of the GPU-backed buffer, not React state; see the useMemo comment above.
        // eslint-disable-next-line react-hooks/immutability
        data[i++] = Math.round(srcRow[col] * 255);
      }
    }
    // The three.js signal to re-upload the just-mutated buffer to the GPU, not a React-state write.
    // eslint-disable-next-line react-hooks/immutability
    texture.needsUpdate = true;
    invalidate();
  }, [field, texture, invalidate]);

  const uniforms = useMemo(() => ({ uField: { value: texture } }), [texture]);

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        vertexShader={VERTEX_SHADER}
        fragmentShader={FRAGMENT_SHADER}
        uniforms={uniforms}
        depthTest={false}
        depthWrite={false}
      />
    </mesh>
  );
}
