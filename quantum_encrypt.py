# Copyright 2026 Otis Ranson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Encrypt a string with a one-time pad keyed by a quantum random number generator.

A Hadamard on |0> puts a qubit into an equal superposition; measuring it in the
computational basis then collapses it to a genuinely random 0 or 1 (not a
pseudo-random one). Using that as a one-time-pad key is real, information-
theoretically secure encryption -- provided the key is truly random, as long
as the message, used only once, and never shared with anyone but the parties
who need it.

By default the qubits live on Cirq's local statevector simulator (pseudo-random
under the hood, standing in for "genuinely random" for demo purposes). `--hardware`
instead sources the key from a real IBM Quantum backend via Qiskit -- an actual
physical Hadamard-and-measure on real qubits, so the randomness is the real thing,
not a stand-in for it.
"""

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import cirq

OUTPUT_DIR = Path(__file__).parent / "output" / "encryption"


def string_to_binary(text: str) -> str:
    """Convert each character of `text` into an 8-bit binary string."""
    return "".join(format(ord(char), "08b") for char in text)


def binary_to_string(binary: str) -> str:
    """Inverse of string_to_binary: decode 8-bit chunks back into characters."""
    chars = (binary[i : i + 8] for i in range(0, len(binary), 8))
    return "".join(chr(int(byte, 2)) for byte in chars)


def xor_bits(a: str, b: str) -> str:
    return "".join("0" if x == y else "1" for x, y in zip(a, b))


def quantum_random_bits(n: int, batch_size: int = 16) -> str:
    """Generate n random bits by measuring Hadamard-superposed qubits, in small batches.

    Batching keeps each simulated state vector to at most 2**batch_size, since
    simulating all n qubits at once would need 2**n amplitudes.
    """
    simulator = cirq.Simulator()
    bits = []
    remaining = n

    while remaining > 0:
        chunk = min(batch_size, remaining)
        qubits = cirq.LineQubit.range(chunk)
        circuit = cirq.Circuit(cirq.H(q) for q in qubits)
        circuit.append(cirq.measure(*qubits, key="key"))

        result = simulator.run(circuit, repetitions=1)
        bits.append("".join(str(b) for b in result.measurements["key"][0]))
        remaining -= chunk

    return "".join(bits)


@dataclass
class HardwareKeyRun:
    """Metadata about a `quantum_random_bits_hardware` call, kept separate from the
    bits themselves so `write_hardware_report` can document what actually ran without
    the key-generation function needing to know about report-writing."""

    backend_name: str
    pending_jobs_at_selection: int
    job_ids: list[str] = field(default_factory=list)
    qubits_per_job: list[int] = field(default_factory=list)


def quantum_random_bits_hardware(n: int, backend_name: str | None = None) -> tuple[str, HardwareKeyRun]:
    """Generate n random bits by measuring Hadamard-superposed qubits on a real IBM
    Quantum backend, in batches sized to the backend's qubit count.

    Unlike the statistical Sampler runs elsewhere in this repo -- many shots
    distilled into a probability distribution -- this needs exactly ONE shot per
    qubit: each shot IS the random bit, not a sample used to estimate something.
    No readout-error mitigation is applied, for the same reason: correcting toward
    an "expected" distribution would work against getting the device's raw physical
    randomness, not for it.
    """
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    backend = service.backend(backend_name) if backend_name else service.least_busy(min_num_qubits=1)
    pending_jobs = backend.status().pending_jobs
    print(f"Selected backend: {backend.name} (queue depth: {pending_jobs} pending jobs)")
    run_info = HardwareKeyRun(backend_name=backend.name, pending_jobs_at_selection=pending_jobs)

    bits = []
    remaining = n
    while remaining > 0:
        chunk = min(remaining, backend.num_qubits)
        qc = QuantumCircuit(chunk)
        qc.h(range(chunk))
        qc.measure_all()
        transpiled = transpile(qc, backend=backend, optimization_level=3)

        sampler = SamplerV2(mode=backend)
        job = sampler.run([transpiled], shots=1)
        print(f"Submitted job {job.job_id()} ({chunk} qubits, 1 shot), waiting for results...")
        result = job.result()
        counts = result[0].data.meas.get_counts()
        bits.append(next(iter(counts)))
        run_info.job_ids.append(job.job_id())
        run_info.qubits_per_job.append(chunk)
        remaining -= chunk

    return "".join(bits), run_info


def encrypt(message: str, key: str) -> tuple[str, str]:
    """Return (ciphertext_bits, key) for `message`, XORed with the given one-time-pad key."""
    plaintext_bits = string_to_binary(message)
    ciphertext_bits = xor_bits(plaintext_bits, key)
    return ciphertext_bits, key


def decrypt(ciphertext_bits: str, key: str) -> str:
    plaintext_bits = xor_bits(ciphertext_bits, key)
    return binary_to_string(plaintext_bits)


def write_hardware_report(
    message: str,
    key: str,
    ciphertext_bits: str,
    ciphertext_hex: str,
    recovered: str,
    garbled: str,
    key_run: HardwareKeyRun,
    wrong_key_run: HardwareKeyRun,
) -> Path:
    """Write a report of a `--hardware` run to output/HARDWARE_RUN.md, mirroring the
    hardware-report convention `quantum_prime_gaps/quantum_prime_gaps.py` uses:
    overwritten on every hardware run, with prior results living in git history
    rather than accumulating in the file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    lines = [
        "# Quantum one-time pad -- real hardware run report",
        "",
        "Generated automatically by `quantum_encrypt.py --hardware`. Overwritten on "
        "every hardware run -- prior results live in git history, not accumulated here.",
        "",
        f"- **Timestamp:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Message:** {message!r}",
        f"- **Backend:** {key_run.backend_name} (selected dynamically via `least_busy` "
        "unless `--backend` overrides it)",
        f"- **Key job(s):** {', '.join(key_run.job_ids)} "
        f"({', '.join(str(q) for q in key_run.qubits_per_job)} qubits, 1 shot each, "
        f"queue depth {key_run.pending_jobs_at_selection} at selection)",
        f"- **Wrong-key job(s):** {', '.join(wrong_key_run.job_ids)} "
        f"({', '.join(str(q) for q in wrong_key_run.qubits_per_job)} qubits, 1 shot each, "
        f"queue depth {wrong_key_run.pending_jobs_at_selection} at selection)",
        f"- **Readout error mitigation:** No (single-shot run -- see `quantum_random_bits_hardware` "
        "docstring for why mitigation would work against the goal here)",
        "",
        "## Result",
        "",
        "```",
        f"Quantum-generated key: {key}",
        f"Ciphertext (bits):     {ciphertext_bits}",
        f"Ciphertext (hex):      {ciphertext_hex}",
        "",
        f"Decrypted with correct key: {recovered!r}",
        f"Decrypted with wrong key:   {garbled!r}",
        "```",
        "",
    ]
    path = OUTPUT_DIR / "HARDWARE_RUN.md"
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Source the one-time-pad key from a real IBM Quantum backend via Qiskit, "
        "instead of Cirq's local simulator. Needs an IBM Quantum API token: set it via the "
        "QISKIT_IBM_TOKEN environment variable, or save it once with "
        "QiskitRuntimeService.save_account(channel=..., token=...).",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="IBM Quantum backend name to use with --hardware (default: least busy).",
    )
    args = parser.parse_args()

    message = "hello hilbert"
    print(f"Message: {message!r}")

    n_bits = len(string_to_binary(message))
    key_run = wrong_key_run = None
    if args.hardware:
        print("\nSourcing key from real IBM Quantum hardware...")
        key, key_run = quantum_random_bits_hardware(n_bits, args.backend)
    else:
        key = quantum_random_bits(n_bits)

    ciphertext_bits, key = encrypt(message, key)
    ciphertext_bytes = int(ciphertext_bits, 2).to_bytes(len(ciphertext_bits) // 8, "big")
    ciphertext_hex = ciphertext_bytes.hex()

    print(f"\nQuantum-generated key: {key}")
    print(f"Ciphertext (bits):     {ciphertext_bits}")
    print(f"Ciphertext (hex):      {ciphertext_hex}")
    if args.hardware:
        print(f"Hardware job ID(s):    {', '.join(key_run.job_ids)}")

    recovered = decrypt(ciphertext_bits, key)
    print(f"\nDecrypted with correct key: {recovered!r}")

    if args.hardware:
        wrong_key, wrong_key_run = quantum_random_bits_hardware(len(key), args.backend)
    else:
        wrong_key = quantum_random_bits(len(key))
    garbled = decrypt(ciphertext_bits, wrong_key)
    print(f"Decrypted with wrong key:   {garbled!r}")

    if args.hardware:
        report_path = write_hardware_report(
            message, key, ciphertext_bits, ciphertext_hex, recovered, garbled, key_run, wrong_key_run
        )
        print(f"\nHardware run report written to {report_path}")


if __name__ == "__main__":
    main()
