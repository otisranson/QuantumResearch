# Quantum one-time pad -- real hardware run report

Generated automatically by `quantum_encrypt.py --hardware`. Overwritten on every hardware run -- prior results live in git history, not accumulated here.

- **Timestamp:** 2026-08-14T09:25:47
- **Message:** 'hello hilbert'
- **Backend:** ibm_marrakesh (selected dynamically via `least_busy` unless `--backend` overrides it)
- **Key job(s):** d9vhehob1g9c73a8kn0g (104 qubits, 1 shot each, queue depth 1 at selection)
- **Wrong-key job(s):** d9vheln2sl0c73blsq90 (104 qubits, 1 shot each, queue depth 1 at selection)
- **Readout error mitigation:** No (single-shot run -- see `quantum_random_bits_hardware` docstring for why mitigation would work against the goal here)

## Result

```
Quantum-generated key: 01011010100110110110010001000100100011011000111010001100011110010010110011001101010101101100111000010000
Ciphertext (bits):     00110010111111100000100000101000111000101010111011100100000100000100000010101111001100111011110001100100
Ciphertext (hex):      32fe0828e2aee41040af33bc64

Decrypted with correct key: 'hello hilbert'
Decrypted with wrong key:   '©=\x8a_Añ\x9c)\x1aþÊúl'
```
