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

"""Quantum Radio -- a sparse quantum listening experiment.

This circuit does not compute an answer. It listens.

Inspired by the question of whether altered perceptual states access signals
normally filtered by conscious processing -- specifically, a personal experience
of audio hallucinations under Prednisone and cephalexin, interpreted not as
malfunction but as potential signal. The quantum hardware is the analog instrument:
real quantum mechanical substrate, genuine stochasticity, decoherence included.
The simulator is the control -- a classical computer pretending. Where they diverge
is where the hardware is contributing something the classical model cannot account for.

phi (golden ratio) was chosen as the phase angle deliberately. It appears at the
boundary between order and emergence in natural systems. It is philosophically
consistent with an experiment designed to listen at the boundary between classical
and quantum behavior.

The CRT renderer was chosen as the output medium because untuned signal is what
the screen shows before the broadcast arrives.

Author: Otis Ranson
License: Apache 2.0
Repository: github.com/otisranson/QuantumResearch
"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, transpile

OUTPUT_DIR = Path(__file__).parent  # quantum_radio_crt.html fetches its JSON from this same directory

N_QUBITS = 10
SHOTS = 8192
PHI = (1 + np.sqrt(5)) / 2

# IBM Quantum backends cap a single job at 100,000 shots; we cap well under
# that ourselves so --hardware runs stay cheap and fast to queue regardless of
# how high --shots is pushed for local sweeps (the simulator has no such cap --
# see quantum_radio_results_18q.json's 2M+ shots).
HARDWARE_SHOTS_CAP = 10_000

# plot_comparison renders one point per basis state (2**N_QUBITS of them) so the
# viewer can see the full per-state distribution, same resolution the CRT renderer
# uses. Past this, Agg's rasterizer hits its own hard "cell block limit" and raises
# (empirically ~2**21-2**22 vertices); well before that it's already multi-GB and
# tens of seconds per plot. Not a Qiskit/hardware limit -- a matplotlib one.
MAX_PLOTTABLE_QUBITS = 20


def _tag() -> str:
    """Filename suffix identifying the current qubit count, so runs at different
    --qubits don't clobber each other's output (quantum_radio_crt.html's multi-row
    view reads several of these side by side)."""
    return f"{N_QUBITS}q"


def job_state_path() -> Path:
    """Tracks a submitted-but-not-yet-fetched hardware job, one file per qubit count."""
    return OUTPUT_DIR / f"quantum_radio_job_{_tag()}.json"


def build_circuit() -> QuantumCircuit:
    """The listening circuit: full superposition, a single chain of entanglement,
    and a golden-ratio phase kick -- then straight to measurement. No error
    correction, no repetition, no structure beyond what's needed to put all
    N_QUBITS qubits into one entangled state and let the hardware do what it does."""
    qc = QuantumCircuit(N_QUBITS, N_QUBITS)

    for q in range(N_QUBITS):
        qc.h(q)

    for q in range(N_QUBITS - 1):
        qc.cx(q, q + 1)

    for q in range(N_QUBITS):
        qc.rz(np.pi * PHI, q)

    qc.measure(range(N_QUBITS), range(N_QUBITS))
    return qc


def run_simulator(circuit: QuantumCircuit, shots: int = SHOTS) -> dict[str, int]:
    """Run the circuit on Aer's local simulator: the control condition -- a
    classical computer pretending to be quantum, with no decoherence."""
    from qiskit_aer import AerSimulator

    simulator = AerSimulator()
    transpiled = transpile(circuit, simulator)
    job = simulator.run(transpiled, shots=shots)
    counts = job.result().get_counts()
    return dict(counts)


@dataclass
class HardwareRunMetadata:
    backend_name: str
    job_id: str
    pending_jobs_at_selection: int


def submit_hardware(circuit: QuantumCircuit, shots: int, backend_name: str) -> HardwareRunMetadata:
    """Submit the circuit to a real IBM Quantum backend and return immediately --
    does not wait for the result. Queue times are outside our control and can run
    from minutes to many hours, so nothing here blocks on job.result(); the job
    is fetched later, non-blockingly, via --check-job."""
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    if shots > HARDWARE_SHOTS_CAP:
        print(f"Requested {shots} shots exceeds the hardware cap ({HARDWARE_SHOTS_CAP}) -- using {HARDWARE_SHOTS_CAP} instead.")
        shots = HARDWARE_SHOTS_CAP

    service = QiskitRuntimeService()
    backend = service.backend(backend_name)
    pending_jobs = backend.status().pending_jobs
    print(f"Selected backend: {backend.name} (queue depth: {pending_jobs} pending jobs)")

    transpiled = transpile(circuit, backend=backend, optimization_level=3)
    sampler = SamplerV2(mode=backend)
    job = sampler.run([transpiled], shots=shots)
    print(f"Submitted job {job.job_id()} ({shots} shots). Not waiting -- run with --check-job later to fetch results.")

    return HardwareRunMetadata(backend_name=backend.name, job_id=job.job_id(), pending_jobs_at_selection=pending_jobs)


def save_job_state(meta: HardwareRunMetadata) -> None:
    job_state_path().write_text(
        json.dumps(
            {
                "backend_name": meta.backend_name,
                "job_id": meta.job_id,
                "pending_jobs_at_selection": meta.pending_jobs_at_selection,
                "submitted_at": datetime.now().isoformat(timespec="seconds"),
            },
            indent=2,
        )
    )


def load_job_state() -> dict | None:
    path = job_state_path()
    if not path.exists():
        return None
    return json.loads(path.read_text())


def check_job(circuit: QuantumCircuit, shots: int) -> None:
    """Poll a previously submitted hardware job without blocking. If it has
    finished, fetch the results and write the full comparison output; otherwise
    report its status and return immediately."""
    from qiskit_ibm_runtime import QiskitRuntimeService

    state = load_job_state()
    if state is None:
        print(f"No pending hardware job found ({job_state_path().name} missing). Submit one with --hardware --qubits {N_QUBITS}.")
        return

    service = QiskitRuntimeService()
    job = service.job(state["job_id"])
    print(f"Job {state['job_id']} on {state['backend_name']}: {job.status()}")

    if not job.done():
        print("Still running -- check back later with --check-job.")
        return

    result = job.result()
    hardware_counts = dict(result[0].data.c.get_counts())
    metadata = HardwareRunMetadata(
        backend_name=state["backend_name"],
        job_id=state["job_id"],
        pending_jobs_at_selection=state["pending_jobs_at_selection"],
    )
    print(f"{len(hardware_counts)} distinct basis states observed on hardware.")

    print("\nRunning on AerSimulator (control)...")
    sim_counts = run_simulator(circuit, shots)
    print(f"{len(sim_counts)} distinct basis states observed in simulation.")

    tvd = total_variation_distance(hardware_counts, sim_counts, N_QUBITS)
    novel_states = novel_hardware_states(sim_counts, hardware_counts)
    print(f"\nTotal variation distance (hardware vs. simulator): {tvd:.4f}")

    plot_path = plot_comparison(sim_counts, hardware_counts, metadata.backend_name)
    json_path = save_results_json(sim_counts, hardware_counts, metadata, tvd, novel_states)
    report_path = write_report(sim_counts, hardware_counts, metadata, tvd, novel_states)

    print(f"\nPlot:   {plot_path}")
    print(f"JSON:   {json_path}")
    print(f"Report: {report_path}")

    job_state_path().unlink()


def counts_to_probabilities(counts: dict[str, int], n_qubits: int) -> np.ndarray:
    """Bitstring -> count map into a probability array indexed by basis-state
    integer. Qiskit writes measurement bitstrings with the highest classical bit
    leftmost (qubit 0 is the rightmost character), which is exactly `int(bitstring, 2)`
    -- both `run_simulator` and `run_hardware` produce counts in this same format,
    so no reordering is needed to compare them directly."""
    dim = 2**n_qubits
    total = sum(counts.values())
    probabilities = np.zeros(dim)
    for bitstring, count in counts.items():
        probabilities[int(bitstring, 2)] = count / total
    return probabilities


def total_variation_distance(counts_a: dict[str, int], counts_b: dict[str, int], n_qubits: int) -> float:
    """TVD = half the L1 distance between the two probability distributions --
    0 means identical distributions, 1 means no overlap at all."""
    p_a = counts_to_probabilities(counts_a, n_qubits)
    p_b = counts_to_probabilities(counts_b, n_qubits)
    return float(0.5 * np.sum(np.abs(p_a - p_b)))


def novel_hardware_states(sim_counts: dict[str, int], hardware_counts: dict[str, int]) -> list[str]:
    """Basis states the hardware measured at least once that the simulator never
    produced across its full shot budget -- states with genuinely zero probability
    under the ideal circuit. On decoherence-free hardware this list would be empty;
    anything here is noise (or, per the experiment's framing, signal)."""
    return sorted(state for state in hardware_counts if state not in sim_counts)


def plot_comparison(sim_counts: dict[str, int], hardware_counts: dict[str, int] | None, backend_name: str | None) -> Path:
    """Both output distributions as histograms, side by side, sharing a y-axis
    scale so the shape of the divergence is directly visible.

    Uses fill_between (one polygon per panel) rather than bar (one Rectangle
    patch per basis state). dim = 2**N_QUBITS, so bar's per-state object
    overhead was growing exponentially with qubit count -- at 20+ qubits that's
    millions of patch objects, enough to exhaust memory and lock up the
    machine. fill_between renders the same shape from a single vectorized
    path, independent of qubit count."""
    dim = 2**N_QUBITS
    x = np.arange(dim)
    sim_probabilities = counts_to_probabilities(sim_counts, N_QUBITS)

    fig, (ax_hw, ax_sim) = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)

    if hardware_counts is not None:
        hardware_probabilities = counts_to_probabilities(hardware_counts, N_QUBITS)
        shared_ylim = max(sim_probabilities.max(), hardware_probabilities.max()) * 1.1
        ax_hw.fill_between(x, hardware_probabilities, step="mid", color="tab:red", linewidth=0, rasterized=True)
        ax_hw.set_title(f"Hardware ({backend_name})")
    else:
        shared_ylim = sim_probabilities.max() * 1.1
        ax_hw.set_title("Hardware (not run -- pass --hardware)")

    ax_hw.set_xlabel(f"basis state (0-{dim - 1})")
    ax_hw.set_ylabel("probability")
    ax_hw.set_xlim(0, dim - 1)
    ax_hw.set_ylim(0, shared_ylim)

    ax_sim.fill_between(x, sim_probabilities, step="mid", color="tab:blue", linewidth=0, rasterized=True)
    ax_sim.set_title("Simulator (AerSimulator)")
    ax_sim.set_xlabel(f"basis state (0-{dim - 1})")
    ax_sim.set_xlim(0, dim - 1)
    ax_sim.set_ylim(0, shared_ylim)

    fig.suptitle(f"Quantum Radio ({N_QUBITS} qubits): hardware vs. simulator output distribution")
    fig.tight_layout()
    path = OUTPUT_DIR / f"quantum_radio_plot_{_tag()}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def save_results_json(
    sim_counts: dict[str, int],
    hardware_counts: dict[str, int] | None,
    hardware_meta: HardwareRunMetadata | None,
    tvd: float | None,
    novel_states: list[str],
) -> Path:
    payload = {
        "n_qubits": N_QUBITS,
        "shots": SHOTS,
        "phi": PHI,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "simulator_counts": sim_counts,
        "hardware_counts": hardware_counts,
        "hardware_backend": hardware_meta.backend_name if hardware_meta else None,
        "hardware_job_id": hardware_meta.job_id if hardware_meta else None,
        "total_variation_distance": tvd,
        "novel_hardware_states": novel_states,
    }
    path = OUTPUT_DIR / f"quantum_radio_results_{_tag()}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def write_report(
    sim_counts: dict[str, int],
    hardware_counts: dict[str, int] | None,
    hardware_meta: HardwareRunMetadata | None,
    tvd: float | None,
    novel_states: list[str],
    pending_meta: HardwareRunMetadata | None = None,
) -> Path:
    lines = [
        "# Quantum Radio -- divergence report",
        "",
        "Generated automatically by `quantum_radio.py`. Overwritten on every run --",
        "prior results live in git history, not accumulated here.",
        "",
        f"- **Timestamp:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Qubits:** {N_QUBITS}",
        f"- **Shots per run:** {SHOTS}",
        f"- **Phase angle:** pi * phi = {np.pi * PHI:.6f} rad (phi = {PHI:.6f})",
        "",
    ]

    if hardware_counts is None:
        if pending_meta is not None:
            lines += [
                f"Hardware job `{pending_meta.job_id}` submitted to {pending_meta.backend_name} and still",
                "pending -- run with `--check-job` to fetch results once it completes.",
            ]
        else:
            lines += [
                "No hardware run this time -- pass `--hardware` to submit to a real IBM",
                "Quantum backend (non-blocking; fetch results later with `--check-job`).",
            ]
        lines += [
            "",
            "## Simulator distribution only",
            "",
            f"{len(sim_counts)} of {2**N_QUBITS} basis states appeared across {SHOTS} shots.",
        ]
        path = OUTPUT_DIR / f"quantum_radio_report_{_tag()}.md"
        path.write_text("\n".join(lines) + "\n")
        return path

    sim_probabilities = counts_to_probabilities(sim_counts, N_QUBITS)
    hardware_probabilities = counts_to_probabilities(hardware_counts, N_QUBITS)
    divergence = np.abs(hardware_probabilities - sim_probabilities)
    top_divergent = np.argsort(divergence)[::-1][:10]

    lines += [
        f"- **Hardware backend:** {hardware_meta.backend_name}",
        f"- **Hardware job:** {hardware_meta.job_id}",
        "",
        "## Total variation distance",
        "",
        f"**TVD(hardware, simulator) = {tvd:.4f}**",
        "",
        "0 means the two distributions are identical; 1 means they share no support",
        "at all. Everything above zero is either hardware noise, decoherence, or --",
        "per this experiment's framing -- signal the classical model can't account for.",
        "",
        "## Basis states hardware measured that the simulator never produced",
        "",
    ]
    if novel_states:
        lines.append(f"{len(novel_states)} of {len(hardware_counts)} hardware-observed states have zero probability in the ideal circuit:")
        lines.append("")
        for state in novel_states:
            count = hardware_counts[state]
            lines.append(f"- `{state}` ({int(state, 2)}): {count} shots ({count / SHOTS:.4%})")
    else:
        lines.append("None -- every basis state the hardware measured also had nonzero probability in the ideal circuit.")
    lines.append("")

    lines += [
        "## Top 10 most divergent basis states",
        "",
        "| Basis state | Index | Simulator p | Hardware p | \\|delta\\| |",
        "|---|---:|---:|---:|---:|",
    ]
    for index in top_divergent:
        bitstring = format(index, f"0{N_QUBITS}b")
        lines.append(f"| `{bitstring}` | {index} | {sim_probabilities[index]:.4%} | {hardware_probabilities[index]:.4%} | {divergence[index]:.4%} |")
    lines.append("")

    path = OUTPUT_DIR / f"quantum_radio_report_{_tag()}.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def main() -> None:
    global N_QUBITS, SHOTS

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Submit the circuit to a real IBM Quantum backend via Qiskit and return immediately -- "
        "does not wait in the queue. Fetch the result later with --check-job. Needs an IBM Quantum "
        "API token: set it via the QISKIT_IBM_TOKEN environment variable, or save it once with "
        "QiskitRuntimeService.save_account(channel=..., token=...).",
    )
    parser.add_argument(
        "--check-job",
        action="store_true",
        help="Check the hardware job previously submitted with --hardware at the same --qubits. If it "
        "has finished, fetch the results and write the full comparison; otherwise report its status "
        "and exit. Never blocks.",
    )
    parser.add_argument(
        "--backend",
        default="ibm_kingston",
        help="IBM Quantum backend name to use with --hardware (default: ibm_kingston, chosen "
        "deliberately -- not the least-busy backend).",
    )
    parser.add_argument(
        "--qubits",
        type=int,
        default=N_QUBITS,
        help=f"Register size (default: {N_QUBITS}). Output filenames are tagged with this "
        "(quantum_radio_results_<N>q.json etc.) so runs at different sizes don't overwrite each "
        "other -- quantum_radio_crt.html's multi-row view reads several side by side.",
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=SHOTS,
        help=f"Shots per run (default: {SHOTS}). Applies to the local simulator uncapped -- at higher "
        "--qubits, shots/state falls fast (2**qubits states share the same shot budget), so raise this "
        f"to compensate or expect a sparser distribution. --hardware runs are separately capped at "
        f"{HARDWARE_SHOTS_CAP} regardless of this value (IBM Quantum's own per-job cap is 100,000).",
    )
    args = parser.parse_args()
    if args.hardware and args.check_job:
        parser.error("--hardware and --check-job are mutually exclusive")
    if args.qubits > MAX_PLOTTABLE_QUBITS:
        parser.error(
            f"--qubits {args.qubits} exceeds MAX_PLOTTABLE_QUBITS ({MAX_PLOTTABLE_QUBITS}). "
            f"plot_comparison plots 2**qubits points per panel; beyond this it's already "
            f"multi-GB and tens of seconds per plot, heading toward a hard failure in "
            f"matplotlib's rasterizer. Not a hardware or Qiskit limit -- lower --qubits."
        )

    N_QUBITS = args.qubits
    SHOTS = args.shots

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    circuit = build_circuit()

    if args.check_job:
        check_job(circuit, SHOTS)
        return

    print(f"Circuit: {N_QUBITS} qubits, H + CNOT chain + RZ(pi*phi={PHI:.6f}), {SHOTS} shots")
    print("\nRunning on AerSimulator (control)...")
    sim_counts = run_simulator(circuit, SHOTS)
    print(f"{len(sim_counts)} distinct basis states observed in simulation.")

    pending_meta = None
    if args.hardware:
        print(f"\nSubmitting to {args.backend} (instrument)...")
        pending_meta = submit_hardware(circuit, SHOTS, args.backend)
        save_job_state(pending_meta)
    else:
        print("\n--hardware not set: simulator-only run. Pass --hardware to submit a hardware comparison.")

    plot_path = plot_comparison(sim_counts, None, None)
    json_path = save_results_json(sim_counts, None, None, None, [])
    report_path = write_report(sim_counts, None, None, None, [], pending_meta=pending_meta)

    print(f"\nPlot:   {plot_path}")
    print(f"JSON:   {json_path}")
    print(f"Report: {report_path}")
    if pending_meta is not None:
        print(f"\nHardware job {pending_meta.job_id} submitted to {pending_meta.backend_name}.")
        print("Run `quantum_radio.py --check-job` later to fetch results -- this will not block.")


if __name__ == "__main__":
    main()
