# Quantum Morse transmission -- real hardware run report

Generated automatically by `quantum_morse.py --hardware`. Overwritten on every hardware run -- prior results live in git history, not accumulated here.

- **Timestamp:** 2026-08-12T10:52:00
- **Readout error mitigation:** No (single-shot run per qubit -- see `transmit_via_qubits_hardware` docstring for why extra shots wouldn't add information here)

## 'SOS HELP'

- **Backend:** ibm_marrakesh (selected dynamically via `least_busy` unless `--backend` overrides it)
- **Job(s):** d9u8eml35hes73fjjmqg (71 qubits, 1 shot each, queue depth 10 at selection)
- **Matches sent pulses:** False

```
Morse:       ... --- ... / .... . .-.. .--.
Pulse train: 10101000111011101110001010100000001010101000100010111010100010111011101

Read back from qubits: 10101000111011101110001010100000001010101000100010111010100010011011101
Matches sent pulses:   False

Decoded Morse: ... --- ... / .... . .-.. .--.
Decoded text:  'SOS HELP'
```

## 'HELLO'

- **Backend:** ibm_marrakesh (selected dynamically via `least_busy` unless `--backend` overrides it)
- **Job(s):** d9u8gjgu5hac73agt1h0 (49 qubits, 1 shot each, queue depth 5 at selection)
- **Matches sent pulses:** False

```
Morse:       .... . .-.. .-.. ---
Pulse train: 1010101000100010111010100010111010100011101110111

Read back from qubits: 1010101000100010111010100010111110100011101110111
Matches sent pulses:   False

Decoded Morse: .... . .-.. .-. ---
Decoded text:  'HELRO'
```

## 'CQ DE W1AW 73'

- **Backend:** ibm_marrakesh (selected dynamically via `least_busy` unless `--backend` overrides it)
- **Job(s):** d9u8h0l35hes73fjjp70 (137 qubits, 1 shot each, queue depth 2 at selection)
- **Matches sent pulses:** False

```
Morse:       -.-. --.- / -.. . / .-- .---- .- .-- / --... ...--
Pulse train: 11101011101000111011101011100000001110101000100000001011101110001011101110111011100010111000101110111000000011101110101010001010101110111

Read back from qubits: 10101011101000111011101011100000001110101000100000001011101100001011101110110011100010111000101110111000000011101110101010001010101110111
Matches sent pulses:   False

Decoded Morse: ...-. --.- / -.. . / .-- .---- .- .-- / --... ...--
Decoded text:  'Q DE W1AW 73'
```

## 'A'

- **Backend:** ibm_marrakesh (selected dynamically via `least_busy` unless `--backend` overrides it)
- **Job(s):** d9u8h2s98n5s7392herg (5 qubits, 1 shot each, queue depth 1 at selection)
- **Matches sent pulses:** False

```
Morse:       .-
Pulse train: 10111

Read back from qubits: 11111
Matches sent pulses:   False

Decoded Morse: -
Decoded text:  'T'
```
