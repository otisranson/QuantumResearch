# Quantum one-time pad -- real hardware run report

Generated automatically by `quantum_encrypt.py --hardware`. Overwritten on every hardware run -- prior results live in git history, not accumulated here.

- **Timestamp:** 2026-08-12T10:27:48
- **Message:** 'hello hilbert'
- **Backend:** ibm_marrakesh (selected dynamically via `least_busy` unless `--backend` overrides it)
- **Key job(s):** d9u85l0u5hac73agsme0 (104 qubits, 1 shot each, queue depth 1 at selection)
- **Wrong-key job(s):** d9u85nt35hes73fjjdng (104 qubits, 1 shot each, queue depth 1 at selection)
- **Readout error mitigation:** No (single-shot run -- see `quantum_random_bits_hardware` docstring for why mitigation would work against the goal here)

## Result

```
Quantum-generated key: 11110101001111101010111000100010110011000101010010110110000110001111000000010010000111010000101010011110
Ciphertext (bits):     10011101010110111100001001001110101000110111010011011110011100011001110001110000011110000111100011101010
Ciphertext (hex):      9d5bc24ea374de719c707878ea

Decrypted with correct key: 'hello hilbert'
Decrypted with wrong key:   '^õo~fç¼F¸Ôd9¸'
```
