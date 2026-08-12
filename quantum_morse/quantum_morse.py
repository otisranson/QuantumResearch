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

"""A Morse code device simulated on qubits.

A message is translated into Morse code, then into an ITU-timed pulse train
(dot = 1 unit on, dash = 3 units on, intra-character gap = 1 unit off,
inter-character gap = 3 units off, inter-word gap = 7 units off). That pulse
train is "transmitted" by writing each bit onto a qubit with an X gate and
reading it back with a measurement, then decoded back into text.

By default this runs on Cirq's local statevector simulator, so the qubits round-trip
the bits with no noise. `--hardware` instead transmits through a real IBM Quantum
backend via Qiskit -- since every qubit here is deterministically prepared in |0> or
|1> (never a superposition), a noiseless read-back must exactly match what was sent,
so any mismatch on real hardware is genuine gate/readout noise corrupting a bit that
was never random to begin with -- a literal transmission-fidelity test.
"""

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from itertools import groupby
from pathlib import Path

import cirq

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "morse"

MORSE_CODE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}
REVERSE_MORSE_CODE = {code: letter for letter, code in MORSE_CODE.items()}


def text_to_morse(text: str) -> str:
    """Convert `text` to Morse, letters space-separated, words separated by ' / '."""
    words = text.upper().split(" ")
    morse_words = []
    for word in words:
        letters = [MORSE_CODE[ch] for ch in word if ch in MORSE_CODE]
        morse_words.append(" ".join(letters))
    return " / ".join(morse_words)


def morse_to_text(morse: str) -> str:
    words = morse.split(" / ")
    decoded_words = []
    for word in words:
        letters = word.split(" ")
        decoded_words.append("".join(REVERSE_MORSE_CODE.get(letter, "") for letter in letters))
    return " ".join(decoded_words)


def morse_to_pulse_train(morse: str) -> str:
    """Encode Morse text as an ITU-timed bit string of dots, dashes, and gaps."""
    word_pulses = []
    for word in morse.split(" / "):
        letter_pulses = []
        for letter in word.split(" "):
            symbol_pulses = ["1" if symbol == "." else "111" for symbol in letter]
            letter_pulses.append("0".join(symbol_pulses))
        word_pulses.append("000".join(letter_pulses))
    return "0000000".join(word_pulses)


def pulse_train_to_morse(pulse_train: str) -> str:
    """Inverse of morse_to_pulse_train: read run lengths back into Morse text."""
    morse = []
    for bit, group in groupby(pulse_train):
        length = sum(1 for _ in group)
        if bit == "1":
            morse.append("." if length == 1 else "-")
        elif length >= 7:
            morse.append(" / ")
        elif length >= 3:
            morse.append(" ")
        # length 1 zero-run is the intra-character gap: no separator needed.
    return "".join(morse)


def transmit_via_qubits(pulse_train: str, batch_size: int = 16) -> str:
    """Write `pulse_train` onto qubits with X gates and read it back via measurement.

    Batched to keep each simulated state vector to at most 2**batch_size, since
    simulating the whole pulse train's worth of qubits at once would need
    2**len(pulse_train) amplitudes.
    """
    simulator = cirq.Simulator()
    received = []

    for start in range(0, len(pulse_train), batch_size):
        chunk = pulse_train[start : start + batch_size]
        qubits = cirq.LineQubit.range(len(chunk))
        circuit = cirq.Circuit(cirq.X(q) for q, bit in zip(qubits, chunk) if bit == "1")
        circuit.append(cirq.measure(*qubits, key="pulses"))

        result = simulator.run(circuit, repetitions=1)
        received.append("".join(str(b) for b in result.measurements["pulses"][0]))

    return "".join(received)


@dataclass
class HardwareTransmitRun:
    """Metadata about a `transmit_via_qubits_hardware` call, kept separate from the
    received bits so `write_hardware_report` can document what actually ran without
    the transmit function needing to know about report-writing."""

    backend_name: str
    pending_jobs_at_selection: int
    job_ids: list[str] = field(default_factory=list)
    qubits_per_job: list[int] = field(default_factory=list)


def transmit_via_qubits_hardware(pulse_train: str, backend_name: str | None = None) -> tuple[str, HardwareTransmitRun]:
    """Write `pulse_train` onto qubits with X gates and read it back via measurement on
    a real IBM Quantum backend, in batches sized to the backend's qubit count.

    Unlike quantum_encrypt.py's hardware QRNG, these qubits aren't in superposition --
    each one is deterministically prepared in |0> or |1>, so a noiseless read-back must
    exactly match the sent chunk. One shot per qubit is still correct here, for a
    different reason than the QRNG case: this reads a definite state, not a
    distribution, so extra shots would only add repeated measurements of the same
    single quantum event, not new information.

    Qiskit writes measurement bitstrings with the highest classical bit leftmost (qubit
    0 is the rightmost character) -- `bitstring[::-1]` undoes that so index i lines up
    with the qubit that chunk[i] was written to, matching the local Cirq path's plain
    left-to-right string order. Confirmed against `qiskit.primitives.StatevectorSampler`
    on a known bit pattern before this ever touched real hardware.
    """
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    backend = service.backend(backend_name) if backend_name else service.least_busy(min_num_qubits=1)
    pending_jobs = backend.status().pending_jobs
    print(f"Selected backend: {backend.name} (queue depth: {pending_jobs} pending jobs)")
    run_info = HardwareTransmitRun(backend_name=backend.name, pending_jobs_at_selection=pending_jobs)

    received = []
    for start in range(0, len(pulse_train), backend.num_qubits):
        chunk = pulse_train[start : start + backend.num_qubits]
        qc = QuantumCircuit(len(chunk))
        for i, bit in enumerate(chunk):
            if bit == "1":
                qc.x(i)
        qc.measure_all()
        transpiled = transpile(qc, backend=backend, optimization_level=3)

        sampler = SamplerV2(mode=backend)
        job = sampler.run([transpiled], shots=1)
        print(f"Submitted job {job.job_id()} ({len(chunk)} qubits, 1 shot), waiting for results...")
        result = job.result()
        counts = result[0].data.meas.get_counts()
        received.append(next(iter(counts))[::-1])
        run_info.job_ids.append(job.job_id())
        run_info.qubits_per_job.append(len(chunk))

    return "".join(received), run_info


EXAMPLE_MESSAGES = ["SOS HELP", "HELLO", "CQ DE W1AW 73", "A"]


@dataclass
class MessageResult:
    message: str
    morse: str
    pulse_train: str
    received: str
    matches: bool
    decoded_morse: str
    decoded_text: str
    transmit_run: HardwareTransmitRun | None = None


def run_message(message: str, hardware: bool = False, backend_name: str | None = None) -> MessageResult:
    """Encode `message`, send it through the qubits (simulated, or real IBM Quantum
    hardware if `hardware=True`), decode it, and print each stage.

    Returns a `MessageResult` so callers (or a script) can check the decoded text
    against the input, and so a hardware run's report can be written afterward.
    """
    print(f"Message: {message!r}")

    # Text -> Morse: standard dot/dash notation, letters space-separated, words separated by '/'.
    morse = text_to_morse(message)
    print(f"\nMorse:       {morse}")

    # Morse -> pulse train: ITU timing as a bit string (dot=1 unit on, dash=3, gaps of 1/3/7).
    pulse_train = morse_to_pulse_train(morse)
    print(f"Pulse train: {pulse_train}")

    # The "device": each pulse bit is written onto a qubit with X and read back by measuring it.
    transmit_run = None
    if hardware:
        received, transmit_run = transmit_via_qubits_hardware(pulse_train, backend_name)
    else:
        received = transmit_via_qubits(pulse_train)
    print(f"\nRead back from qubits: {received}")
    # On the simulator this is always True (no noise simulated); on real hardware a
    # False here is genuine gate/readout noise, not a bug -- see the module docstring.
    matches = received == pulse_train
    print(f"Matches sent pulses:   {matches}")

    # Pulse train -> Morse -> text: the inverse of the two encoding steps above.
    decoded_morse = pulse_train_to_morse(received)
    decoded_text = morse_to_text(decoded_morse)
    print(f"\nDecoded Morse: {decoded_morse}")
    print(f"Decoded text:  {decoded_text!r}")

    return MessageResult(message, morse, pulse_train, received, matches, decoded_morse, decoded_text, transmit_run)


def write_hardware_report(results: list[MessageResult]) -> Path:
    """Write a report of a `--hardware` run to output/morse/HARDWARE_RUN.md, mirroring
    the hardware-report convention used elsewhere in this repo (quantum_prime_gaps/,
    quantum_encrypt.py): overwritten on every hardware run, with prior results living
    in git history rather than accumulating in the file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Quantum Morse transmission -- real hardware run report",
        "",
        "Generated automatically by `quantum_morse.py --hardware`. Overwritten on "
        "every hardware run -- prior results live in git history, not accumulated here.",
        "",
        f"- **Timestamp:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Readout error mitigation:** No (single-shot run per qubit -- see "
        "`transmit_via_qubits_hardware` docstring for why extra shots wouldn't add information here)",
        "",
    ]
    for result in results:
        run = result.transmit_run
        lines += [
            f"## {result.message!r}",
            "",
            f"- **Backend:** {run.backend_name} (selected dynamically via `least_busy` "
            "unless `--backend` overrides it)",
            f"- **Job(s):** {', '.join(run.job_ids)} "
            f"({', '.join(str(q) for q in run.qubits_per_job)} qubits, 1 shot each, "
            f"queue depth {run.pending_jobs_at_selection} at selection)",
            f"- **Matches sent pulses:** {result.matches}",
            "",
            "```",
            f"Morse:       {result.morse}",
            f"Pulse train: {result.pulse_train}",
            "",
            f"Read back from qubits: {result.received}",
            f"Matches sent pulses:   {result.matches}",
            "",
            f"Decoded Morse: {result.decoded_morse}",
            f"Decoded text:  {result.decoded_text!r}",
            "```",
            "",
        ]
    path = OUTPUT_DIR / "HARDWARE_RUN.md"
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Encode a message as Morse, transmit it through simulated qubits, decode it back."
    )
    parser.add_argument(
        "message",
        nargs="?",
        default=None,
        help="Text to send (letters, digits, spaces). Omit to run the built-in example messages instead.",
    )
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Transmit through a real IBM Quantum backend via Qiskit, instead of Cirq's local "
        "simulator. Needs an IBM Quantum API token: set it via the QISKIT_IBM_TOKEN environment "
        "variable, or save it once with QiskitRuntimeService.save_account(channel=..., token=...).",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="IBM Quantum backend name to use with --hardware (default: least busy).",
    )
    args = parser.parse_args()

    messages = [args.message] if args.message is not None else EXAMPLE_MESSAGES
    if args.message is None:
        print("No message given, running the built-in examples instead.\n")

    results = []
    for index, message in enumerate(messages):
        if index > 0:
            print()
        results.append(run_message(message, hardware=args.hardware, backend_name=args.backend))

    if args.hardware:
        report_path = write_hardware_report(results)
        print(f"\nHardware run report written to {report_path}")


if __name__ == "__main__":
    main()
