"""Hierarchical qubit-correlation analysis of quantum_radio's 12-qubit hardware/
simulator run.

This is a repurposing, not a native feature of the golden-ratio phase-kick
circuit quantum_radio.py runs: that circuit has no encoding/ancilla structure,
so the "qubits 0-5 vs 6-11" split drawn throughout the plots below is an
arbitrary bipartition used to demonstrate a hierarchical-analysis methodology,
not a genuine encoding subspace. Treat the highlighting as "here's where we cut
the register in half," not "here's where the meaningful physics lives."

Reads quantum_radio_results_12q.json (bitstring -> shot count, for both the
ibm_marrakesh hardware run and the AerSimulator control) and produces:

1. Per-qubit marginals P(qubit_i = |1>), hardware vs simulator.
2. A 12x12 pairwise correlation matrix (Pearson, over the binary per-qubit
   outcome), hardware vs simulator vs their difference.
3. A hierarchical partition tree: qubits recursively bisected in index order
   (0-5 | 6-11, then 0-2 | 3-5, etc.), with mutual information between each
   node's two halves as the edge weight -- drawn as a dendrogram.
4. A 2-sigma flag on any qubit pair where the hardware correlation diverges
   from the simulator correlation beyond sampling noise -- crosstalk or
   entanglement, this analysis alone can't tell which.

Run: .venv/bin/python quantum_radio/qubit_hierarchy_analysis.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

HERE = Path(__file__).parent
RESULTS_PATH = HERE / "quantum_radio_results_12q.json"
SCREENSHOTS_DIR = HERE / "screenshots"
REPORT_PATH = HERE / "qubit_hierarchy_report.md"

N_QUBITS = 12
SPLIT_AT = 6  # the arbitrary "left half / right half" bipartition, qubits 0-5 vs 6-11

# Palette (see the project's dataviz skill): fixed categorical slots for
# identity (simulator = blue, hardware = red, matching every other hw/sim
# panel in this repo), a blue<->red diverging pair with a neutral gray
# midpoint for polarity (correlation sign), and a single blue sequential
# ramp for magnitude (mutual information).
SIM_COLOR = "#2a78d6"
HW_COLOR = "#e34948"
NEUTRAL_GRAY = "#f0efec"
DIVERGING_CMAP = LinearSegmentedColormap.from_list("blue_red_diverging", ["#184f95", NEUTRAL_GRAY, "#d03b3b"])
SEQUENTIAL_BLUE = LinearSegmentedColormap.from_list("sequential_blue", ["#cde2fb", "#0d366b"])
HIGHLIGHT_FILL = "#eda10022"  # translucent yellow wash marking the qubits 0-5 half


def load_counts() -> tuple[dict[str, int], dict[str, int]]:
    data = json.loads(RESULTS_PATH.read_text())
    assert data["n_qubits"] == N_QUBITS, f"expected a {N_QUBITS}-qubit run, got {data['n_qubits']}"
    return data["simulator_counts"], data["hardware_counts"]


def counts_to_bits_and_probs(counts: dict[str, int]) -> tuple[np.ndarray, np.ndarray]:
    """Qiskit writes the highest classical bit leftmost (qubit 0 is the rightmost
    character) -- same convention quantum_radio.py itself relies on. Returns
    (bits, probs): bits[state, qubit] in {0,1}, probs[state] summing to 1. One row
    per *distinct* measured bitstring, not one per shot -- every statistic below is
    computed as a probability-weighted sum over these, which is exact and avoids
    materializing 8192 rows of duplicates."""
    keys = list(counts.keys())
    weights = np.array([counts[k] for k in keys], dtype=np.float64)
    probs = weights / weights.sum()
    bits = np.zeros((len(keys), N_QUBITS), dtype=np.float64)
    for row, bitstring in enumerate(keys):
        for q in range(N_QUBITS):
            bits[row, q] = int(bitstring[N_QUBITS - 1 - q])
    return bits, probs


def marginals(bits: np.ndarray, probs: np.ndarray) -> np.ndarray:
    return bits.T @ probs


def correlation_matrix(bits: np.ndarray, probs: np.ndarray) -> np.ndarray:
    mean = bits.T @ probs
    cov = (bits * probs[:, None]).T @ bits - np.outer(mean, mean)
    var = np.diag(cov)
    denom = np.sqrt(np.outer(var, var))
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.where(denom > 0, cov / denom, 0.0)
    np.fill_diagonal(corr, 1.0)
    return corr


def marginal_joint(bits: np.ndarray, probs: np.ndarray, qubit_indices: list[int]) -> dict[tuple, float]:
    """Joint distribution over a subset of qubits, marginalizing out the rest --
    just aggregating probability mass by the reduced tuple of bit values."""
    dist: dict[tuple, float] = defaultdict(float)
    sub = bits[:, qubit_indices]
    for row, p in zip(sub, probs):
        dist[tuple(row)] += p
    return dist


def entropy_bits(dist: dict[tuple, float], n_shots: int) -> float:
    """Miller-Madow bias-corrected plug-in entropy. The uncorrected estimator is
    downward-biased by roughly (K_observed - 1) / (2 N ln 2) bits, where K is the
    number of distinct outcomes -- negligible when the outcome space is small
    relative to N, but severe for e.g. the full 12-qubit joint (4096 possible
    states, only 8192 shots): that alone produces ~0.3 bits of spurious entropy
    deficit, which flows straight into mutual information as a false positive.
    Uncorrected, the root-level MI in this analysis comes out ~0.4 bits purely
    from that undersampling artifact -- two orders of magnitude above every other
    node in the tree, and with no support in the (near-zero) pairwise correlation
    matrix. Correcting for it is what makes "is this real" answerable at all."""
    p = np.array(list(dist.values()))
    p = p[p > 0]
    plugin = float(-np.sum(p * np.log2(p)))
    bias = (len(p) - 1) / (2 * n_shots * np.log(2))
    return plugin + bias


def mutual_information(bits: np.ndarray, probs: np.ndarray, left: list[int], right: list[int], n_shots: int) -> float:
    joint = marginal_joint(bits, probs, left + right)
    left_h = entropy_bits(marginal_joint(bits, probs, left), n_shots)
    right_h = entropy_bits(marginal_joint(bits, probs, right), n_shots)
    joint_h = entropy_bits(joint, n_shots)
    # The bias-corrected estimator is unbiased in expectation, not non-negative --
    # it can dip slightly below 0 when the true MI is at/near 0. Clip for display;
    # a real negative MI isn't a meaningful quantity anyway.
    return max(0.0, left_h + right_h - joint_h)


def _entropy_from_uniform_samples(cols: np.ndarray, n_shots: int) -> float:
    """Same Miller-Madow-corrected entropy as entropy_bits, specialized for
    synthetic per-shot samples (one row per shot, equal weight) -- vectorized via
    integer-packing + np.unique instead of a Python dict, since the null
    calibration below needs many of these per node."""
    k = cols.shape[1]
    keys = (cols.astype(np.int64) * (1 << np.arange(k))[None, :]).sum(axis=1)
    _, counts = np.unique(keys, return_counts=True)
    p = counts / n_shots
    plugin = float(-np.sum(p * np.log2(p)))
    bias = (len(p) - 1) / (2 * n_shots * np.log(2))
    return plugin + bias


def null_mi_stats(marg_probs: np.ndarray, n_left: int, n_shots: int, rng: np.random.Generator, n_trials: int = 200) -> tuple[float, float]:
    """What would this node's (bias-corrected) MI look like if its qubits were
    genuinely independent, with the same marginals and the same shot count? Answers
    it by simulation rather than trusting the analytic correction alone -- Miller-
    Madow is only a first-order fix, and stays imperfect when N/K is small (the
    root node here has N=8192 shots against up to K=4096 possible states, i.e.
    N/K ~= 2). Returns (null_mean, null_std) so the observed MI can be turned into
    a z-score against this simulated noise floor."""
    n = len(marg_probs)
    trials = np.empty(n_trials)
    for t in range(n_trials):
        synth = rng.random((n_shots, n)) < marg_probs[None, :]
        trials[t] = (
            _entropy_from_uniform_samples(synth[:, :n_left], n_shots)
            + _entropy_from_uniform_samples(synth[:, n_left:], n_shots)
            - _entropy_from_uniform_samples(synth, n_shots)
        )
    return float(trials.mean()), float(trials.std())


def build_partition_tree(
    bits: np.ndarray, probs: np.ndarray, qubit_indices: list[int], n_shots: int, full_marginals: np.ndarray, rng: np.random.Generator
) -> dict:
    """Recursively bisect `qubit_indices` (root call: all 12, in index order, so
    the very first split is exactly the 0-5 | 6-11 halves) and compute the
    mutual information between the two halves at every level, calibrated against
    an independent-qubits null (see null_mi_stats) so a node's MI is judged
    against sampling noise at its own outcome-space size, not a flat threshold."""
    if len(qubit_indices) == 1:
        return {"qubits": qubit_indices, "leaf": True}
    mid = (len(qubit_indices) + 1) // 2
    left_idx, right_idx = qubit_indices[:mid], qubit_indices[mid:]
    mi = mutual_information(bits, probs, left_idx, right_idx, n_shots)
    null_mean, null_std = null_mi_stats(full_marginals[qubit_indices], len(left_idx), n_shots, rng)
    z = (mi - null_mean) / null_std if null_std > 0 else 0.0
    return {
        "qubits": qubit_indices,
        "leaf": False,
        "mi": mi,
        "null_mean": null_mean,
        "null_std": null_std,
        "z": z,
        "left": build_partition_tree(bits, probs, left_idx, n_shots, full_marginals, rng),
        "right": build_partition_tree(bits, probs, right_idx, n_shots, full_marginals, rng),
    }


def tree_depth(node: dict) -> int:
    if node["leaf"]:
        return 0
    return 1 + max(tree_depth(node["left"]), tree_depth(node["right"]))


def plot_marginals(sim_p1: np.ndarray, hw_p1: np.ndarray) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.axvspan(-0.5, SPLIT_AT - 0.5, color=HIGHLIGHT_FILL, zorder=0)
    ax.axvspan(SPLIT_AT - 0.5, N_QUBITS - 0.5, color="#00000000", zorder=0)

    x = np.arange(N_QUBITS)
    width = 0.38
    ax.bar(x - width / 2, sim_p1, width, label="simulator", color=SIM_COLOR)
    ax.bar(x + width / 2, hw_p1, width, label="hardware (ibm_marrakesh)", color=HW_COLOR)
    ax.axhline(0.5, color="#898781", linewidth=1, linestyle="--", zorder=1)

    ax.set_xticks(x)
    ax.set_xticklabels([f"q{i}" for i in range(N_QUBITS)])
    ax.set_ylabel("P(qubit = |1>)")
    ax.set_title("Per-qubit marginals -- hardware vs. simulator\n(shaded: qubits 0-5, the arbitrary left/right split used below)")
    ax.legend(frameon=False)
    ax.set_ylim(0, 1)
    fig.tight_layout()

    path = SCREENSHOTS_DIR / "qubit_hierarchy_marginals.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_correlations(sim_corr: np.ndarray, hw_corr: np.ndarray, flagged: list[tuple[int, int]]) -> Path:
    diff = hw_corr - sim_corr
    panels = [("Simulator", sim_corr), ("Hardware (ibm_marrakesh)", hw_corr), ("Hardware - Simulator (Δ)", diff)]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    for ax, (title, mat) in zip(axes, panels):
        im = ax.imshow(mat, cmap=DIVERGING_CMAP, vmin=-1, vmax=1)
        ax.set_title(title)
        ax.set_xticks(range(N_QUBITS))
        ax.set_yticks(range(N_QUBITS))
        ax.set_xticklabels([f"q{i}" for i in range(N_QUBITS)], fontsize=8)
        ax.set_yticklabels([f"q{i}" for i in range(N_QUBITS)], fontsize=8)
        ax.axvline(SPLIT_AT - 0.5, color="#eda100", linewidth=2)
        ax.axhline(SPLIT_AT - 0.5, color="#eda100", linewidth=2)
        if title.startswith("Hardware -"):
            for i, j in flagged:
                for a, b in ((i, j), (j, i)):
                    ax.add_patch(Rectangle((b - 0.5, a - 0.5), 1, 1, fill=False, edgecolor="black", linewidth=1.6))

    cbar = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02)
    cbar.set_label("correlation coefficient")
    fig.suptitle(
        "Pairwise qubit correlation -- orange lines mark the arbitrary 0-5 | 6-11 split; "
        "black boxes on the Δ panel are pairs flagged beyond 2σ sampling noise"
    )
    path = SCREENSHOTS_DIR / "qubit_hierarchy_correlations.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _assign_positions(node: dict, leaf_order: list[int], depth: int, positions: dict[int, tuple[float, float]]) -> float:
    """Recursively assign an x position to every node (mean of its leaves' x) and
    stash (x, depth) per node id; returns this node's x."""
    if node["leaf"]:
        x = float(leaf_order.index(node["qubits"][0]))
        positions[id(node)] = (x, depth)
        return x
    lx = _assign_positions(node["left"], leaf_order, depth + 1, positions)
    rx = _assign_positions(node["right"], leaf_order, depth + 1, positions)
    x = (lx + rx) / 2
    positions[id(node)] = (x, depth)
    return x


Z_CAP = 4.0  # z-scores are clipped to this for color/linewidth scaling, not for the printed label
Z_SIGNIFICANT = 2.0


def _draw_tree(ax, node: dict, leaf_order: list[int], depth: int, positions: dict, max_depth: int):
    x, _ = positions[id(node)]
    y = max_depth - depth
    if node["leaf"]:
        ax.text(x, y - 0.35, f"q{node['qubits'][0]}", ha="center", va="top", fontsize=9)
        return
    for child in (node["left"], node["right"]):
        cx, _ = positions[id(child)]
        cy = max_depth - (depth + 1)
        z_frac = max(0.0, min(node["z"], Z_CAP)) / Z_CAP
        color = SEQUENTIAL_BLUE(z_frac)
        lw = 1 + 5 * z_frac
        ax.plot([x, x, cx], [y, cy, cy], color=color, linewidth=lw, solid_capstyle="round")
        _draw_tree(ax, child, leaf_order, depth + 1, positions, max_depth)
    star = "*" if node["z"] > Z_SIGNIFICANT else ""
    ax.text(x, y + 0.12, f"{node['mi']:.3f} bits{star}\n(z={node['z']:.1f})", ha="center", va="bottom", fontsize=7, color="#52514e")


def plot_dendrograms(sim_tree: dict, hw_tree: dict) -> Path:
    leaf_order = list(range(N_QUBITS))
    max_depth = max(tree_depth(sim_tree), tree_depth(hw_tree))

    fig, axes = plt.subplots(1, 2, figsize=(15, 7.2), sharey=True)
    for ax, tree, title in zip(axes, (sim_tree, hw_tree), ("Simulator", "Hardware (ibm_marrakesh)")):
        positions: dict = {}
        _assign_positions(tree, leaf_order, 0, positions)
        ax.axvspan(-0.5, SPLIT_AT - 0.5, color=HIGHLIGHT_FILL, zorder=0)
        _draw_tree(ax, tree, leaf_order, 0, positions, max_depth)
        ax.set_title(title)
        ax.set_xlim(-0.5, N_QUBITS - 0.5)
        ax.set_ylim(-0.6, max_depth + 0.9)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    fig.suptitle(
        "Hierarchical partition tree -- recursive 0-5|6-11-style bisection\n"
        "MI: Miller-Madow corrected, calibrated vs. an independence null (* = z > 2). Shaded: qubits 0-5.",
        fontsize=12,
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 0.9, 0.88))

    sm = plt.cm.ScalarMappable(cmap=SEQUENTIAL_BLUE, norm=plt.Normalize(0, Z_CAP))
    cbar = fig.colorbar(sm, ax=axes, fraction=0.025, pad=0.03, extend="max")
    cbar.set_label("z-score vs. independent-qubits null (same marginals, same shot count)")
    path = SCREENSHOTS_DIR / "qubit_hierarchy_dendrogram.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def flag_divergent_pairs(sim_corr: np.ndarray, hw_corr: np.ndarray, n_shots: int) -> list[tuple[int, int, float, float, float]]:
    """Fisher-style approximation: under the null of no true correlation, a
    Pearson correlation estimated from N binary trials has stderr ~ 1/sqrt(N-3).
    Flag pairs where |hw - sim| exceeds 2x the combined stderr of both estimates.
    This is a heuristic threshold (the per-qubit variables aren't bivariate
    normal), good enough to separate "probably real" from "probably shot noise,"
    not a rigorous significance test."""
    se = np.sqrt(2.0 / (n_shots - 3))
    threshold = 2 * se
    flagged = []
    for i in range(N_QUBITS):
        for j in range(i + 1, N_QUBITS):
            delta = hw_corr[i, j] - sim_corr[i, j]
            if abs(delta) > threshold:
                flagged.append((i, j, sim_corr[i, j], hw_corr[i, j], delta))
    flagged.sort(key=lambda row: -abs(row[4]))
    return flagged


def write_report(
    sim_p1: np.ndarray,
    hw_p1: np.ndarray,
    flagged: list[tuple[int, int, float, float, float]],
    threshold: float,
    marginals_path: Path,
    correlations_path: Path,
    dendrogram_path: Path,
    sim_tree: dict,
    hw_tree: dict,
    significant: list[str],
) -> None:
    lines = [
        "# Hierarchical qubit analysis -- quantum_radio 12-qubit run",
        "",
        "Repurposes quantum_radio's 12-qubit hardware (ibm_marrakesh) vs. AerSimulator",
        "counts to demonstrate a hierarchical qubit-correlation methodology. **The",
        "qubits 0-5 | 6-11 split is an arbitrary bipartition, not a genuine encoding/",
        "ancilla subspace** -- the golden-ratio phase-kick circuit this data comes from",
        "has no such structure. Whether any flagged pair below is crosstalk noise or",
        "something more structured isn't answerable from this data alone.",
        "",
        f"Generated by `qubit_hierarchy_analysis.py`. Source: `{RESULTS_PATH.name}`.",
        "",
        "## Marginals",
        "",
        f"![marginals]({marginals_path.relative_to(HERE)})",
        "",
        "| Qubit | P(=1) sim | P(=1) hw | Δ |",
        "|---|---:|---:|---:|",
    ]
    for i in range(N_QUBITS):
        lines.append(f"| q{i} | {sim_p1[i]:.4f} | {hw_p1[i]:.4f} | {hw_p1[i] - sim_p1[i]:+.4f} |")

    lines += [
        "",
        "## Pairwise correlations",
        "",
        f"![correlations]({correlations_path.relative_to(HERE)})",
        "",
        "## Hierarchical partition tree",
        "",
        "Edge weights are Miller-Madow bias-corrected mutual information (bits) between",
        "each node's two halves, then calibrated against a *simulated independence null*:",
        "200 synthetic datasets per node, drawn from independent Bernoulli qubits with that",
        "node's own observed marginals and shot count, giving a z-score for \"is this MI",
        "bigger than independent qubits would produce by chance.\" That second step matters",
        "-- the uncorrected plug-in estimator alone is a trap at the root: the full 12-qubit",
        "joint has 4096 possible outcomes from only 8192 shots (N/K ~ 2), which produces ~0.3",
        "bits of spurious \"structure\" on its own (naive root MI came out ~0.4 bits). Miller-",
        "Madow correction brings that down to ~0.11 bits -- still, on its own, looking like",
        "the biggest number in the tree by 20x. Only the null comparison resolves it: simulated",
        "independent qubits with the *same* marginals and shot count produce MI in the same",
        "~0.10 bit range purely from sampling noise, so the corrected root MI",
        f"(simulator={sim_tree['mi']:.4f} bits, z={sim_tree['z']:.2f}; hardware={hw_tree['mi']:.4f} bits,",
        f"z={hw_tree['z']:.2f}) is not distinguishable from noise. A node is only flagged",
        "significant (marked `*` in the figure) at z > 2.",
        "",
        f"![dendrogram]({dendrogram_path.relative_to(HERE)})",
        "",
        "**Partition-tree nodes exceeding z > 2 (simulator or hardware):**",
        "",
    ]
    if not significant:
        lines.append(
            "None. No qubit grouping at any level of the hierarchy -- including the top-level "
            "0-5 | 6-11 split -- shows more mutual information than independent qubits with the "
            "same marginals would produce by chance. Combined with the near-zero pairwise "
            "correlation matrix, there's no evidence of structure here at any granularity: "
            "\"noisy neighbors,\" not entanglement -- at least not at the level this circuit's "
            "measurement statistics can resolve it."
        )
    else:
        lines.extend(f"- {line}" for line in significant)
    lines += [
        "",
        "## Qubit pairs flagged beyond 2σ",
        "",
        f"2σ threshold on |hw correlation - sim correlation|, from the {8192}-shot sampling",
        f"noise on each Pearson estimate (see docstring for the approximation): **{threshold:.4f}**.",
        "",
    ]
    if not flagged:
        lines.append("None -- every pairwise correlation's hardware/simulator difference is within sampling noise.")
    else:
        lines.append("| Pair | Crosses 0-5|6-11? | sim corr | hw corr | Δ |")
        lines.append("|---|---|---:|---:|---:|")
        for i, j, sc, hc, delta in flagged:
            crosses = "yes" if (i < SPLIT_AT) != (j < SPLIT_AT) else "no"
            lines.append(f"| q{i}-q{j} | {crosses} | {sc:+.4f} | {hc:+.4f} | {delta:+.4f} |")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines))


def main() -> None:
    sim_counts, hw_counts = load_counts()
    sim_bits, sim_probs = counts_to_bits_and_probs(sim_counts)
    hw_bits, hw_probs = counts_to_bits_and_probs(hw_counts)

    sim_p1 = marginals(sim_bits, sim_probs)
    hw_p1 = marginals(hw_bits, hw_probs)
    marginals_path = plot_marginals(sim_p1, hw_p1)

    sim_corr = correlation_matrix(sim_bits, sim_probs)
    hw_corr = correlation_matrix(hw_bits, hw_probs)
    n_shots = 8192
    flagged = flag_divergent_pairs(sim_corr, hw_corr, n_shots)
    threshold = 2 * np.sqrt(2.0 / (n_shots - 3))
    correlations_path = plot_correlations(sim_corr, hw_corr, [(i, j) for i, j, *_ in flagged])

    rng = np.random.default_rng(0)
    sim_tree = build_partition_tree(sim_bits, sim_probs, list(range(N_QUBITS)), n_shots, sim_p1, rng)
    hw_tree = build_partition_tree(hw_bits, hw_probs, list(range(N_QUBITS)), n_shots, hw_p1, rng)
    dendrogram_path = plot_dendrograms(sim_tree, hw_tree)

    def significant_nodes(node: dict, label: str, out: list[str]) -> None:
        if node["leaf"]:
            return
        if node["z"] > Z_SIGNIFICANT:
            qs = ",".join(f"q{q}" for q in node["qubits"])
            out.append(f"{label}: [{qs}] split -- MI={node['mi']:.4f} bits, z={node['z']:.2f}")
        significant_nodes(node["left"], label, out)
        significant_nodes(node["right"], label, out)

    sig = []
    significant_nodes(sim_tree, "simulator", sig)
    significant_nodes(hw_tree, "hardware", sig)

    write_report(
        sim_p1,
        hw_p1,
        flagged,
        threshold,
        marginals_path,
        correlations_path,
        dendrogram_path,
        sim_tree,
        hw_tree,
        sig,
    )

    print(
        f"Root-level MI (qubits 0-5 vs 6-11): simulator={sim_tree['mi']:.4f} bits (z={sim_tree['z']:.2f}), "
        f"hardware={hw_tree['mi']:.4f} bits (z={hw_tree['z']:.2f})"
    )
    print(f"2-sigma correlation-divergence threshold: {threshold:.4f}")
    print(f"Flagged pairs: {len(flagged)} / {N_QUBITS * (N_QUBITS - 1) // 2}")
    for i, j, sc, hc, delta in flagged:
        crosses = "crosses 0-5|6-11" if (i < SPLIT_AT) != (j < SPLIT_AT) else "within one half"
        print(f"  q{i}-q{j} ({crosses}): sim={sc:+.4f} hw={hc:+.4f} delta={delta:+.4f}")
    print(f"Partition-tree nodes exceeding the z>2 independence-null significance bar: {len(sig)}")
    for line in sig:
        print(f"  {line}")
    print(f"\nWrote {marginals_path}, {correlations_path}, {dendrogram_path}, {REPORT_PATH}")


if __name__ == "__main__":
    main()
