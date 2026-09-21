"""Generator for the Degraded Traverse Records corpus.

A survey traverse visits every station in a network exactly once. The only
surviving record is a raster plan in which most of each leg has faded, plus the
surveyed station coordinates and the station the traverse began from. The
visiting order itself was never written down.

The corpus is original synthetic data produced entirely by this file. No
third-party imagery, measurements or labels are redistributed.

Deterministic: a fixed seed, sorted iteration and integer quantisation make the
output byte-identical across runs and platforms.

    python generate_raw.py --out scenes.npz
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np

SEED = 20260921
RES = 72
STATIONS = 13
HALF_WIDTH = 0.9
ERASE = 0.94
LOCALITY = 0.45
MIN_SEPARATION = 0.115
MARGIN = 0.07
NOISE = 0.05
SCENES_PER_LAYOUT = 4
LAYOUTS = 850


def sample_layout(rng: np.random.Generator) -> np.ndarray:
    """Station positions in the unit square with a minimum separation."""
    pts: list[np.ndarray] = []
    while len(pts) < STATIONS:
        p = rng.random(2) * (1.0 - 2 * MARGIN) + MARGIN
        if all(np.hypot(*(p - q)) > MIN_SEPARATION for q in pts):
            pts.append(p)
    pts = np.array(pts)
    # Canonical station IDs are spatial, never temporal, so an ID carries no
    # information about when the station was visited.
    return pts[np.lexsort((pts[:, 0], pts[:, 1]))]


def sample_order(rng: np.random.Generator, pts: np.ndarray) -> np.ndarray:
    """A partly local, partly arbitrary route over every station.

    LOCALITY is the probability of stepping to the nearest unvisited station.
    At 0 the route is a uniform permutation and the plan is an illegible
    tangle; at 1 it is nearest-neighbour and the coordinates alone would give
    the answer away. The chosen value keeps coordinates weakly informative and
    leaves the raster decisive.
    """
    remaining = list(range(STATIONS))
    start = int(rng.integers(STATIONS))
    remaining.remove(start)
    order = [start]
    while remaining:
        current = pts[order[-1]]
        if rng.random() < LOCALITY:
            nxt = remaining[int(np.argmin([np.hypot(*(pts[j] - current)) for j in remaining]))]
        else:
            nxt = remaining[int(rng.integers(len(remaining)))]
        order.append(nxt)
        remaining.remove(nxt)
    return np.array(order, dtype=np.int64)


def render(pts: np.ndarray, order: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Rasterise the legs, fading one contiguous interior span of each.

    Both endpoints of every leg stay attached, so a station never loses all of
    its incident evidence; what is destroyed is the middle, which is what makes
    a leg hard to tell from one that was never walked.
    """
    img = np.zeros((RES, RES), dtype=np.float64)
    yy, xx = np.mgrid[0:RES, 0:RES]
    scale = RES - 1
    for a, b in zip(order[:-1], order[1:]):
        p0, p1 = pts[a] * scale, pts[b] * scale
        seg = p1 - p0
        length = float(np.hypot(*seg))
        if length < 1e-6:
            continue
        t = np.clip(((xx - p0[0]) * seg[0] + (yy - p0[1]) * seg[1]) / length ** 2, 0.0, 1.0)
        dist = np.hypot(xx - (p0[0] + t * seg[0]), yy - (p0[1] + t * seg[1]))
        band = np.clip(1.0 - (dist - HALF_WIDTH), 0.0, 1.0)
        cut = float(rng.random()) * ERASE
        lo = float(rng.random()) * (1.0 - cut)
        img = np.maximum(img, np.where((t > lo) & (t < lo + cut), 0.0, band))
    for p in pts:
        c = p * scale
        img = np.maximum(img, np.clip(1.6 - np.hypot(xx - c[0], yy - c[1]), 0.0, 1.0))
    img = np.clip(img + rng.normal(0.0, NOISE, img.shape), 0.0, 1.0)
    return np.round(img * 255.0).astype(np.uint8)


def build() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(SEED)
    images, ports, orders, starts, layout_ids = [], [], [], [], []
    for layout in range(LAYOUTS):
        pts = sample_layout(rng)
        for _ in range(SCENES_PER_LAYOUT):
            order = sample_order(rng, pts)
            images.append(render(pts, order, rng))
            ports.append((pts * (RES - 1)).astype(np.float32))
            orders.append(order)
            starts.append(int(order[0]))
            layout_ids.append(layout)
    images = np.stack(images)
    raw_id = np.array(
        [hashlib.sha256(b"traverse-v1:" + im.tobytes() + po.tobytes()).hexdigest()
         for im, po in zip(images, np.stack(ports))]
    )
    return dict(
        images=images,
        ports=np.stack(ports),
        visit_order=np.stack(orders).astype(np.int8),
        start_station=np.array(starts, dtype=np.int8),
        layout_id=np.array(layout_ids, dtype=np.int32),
        raw_id=raw_id,
    )


def write_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(arrays):
            buf = io.BytesIO()
            np.save(buf, arrays[name], allow_pickle=False)
            info = zipfile.ZipInfo(name + ".npy", (2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            z.writestr(info, buf.getvalue(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("scenes.npz"))
    ap.add_argument("--report", type=Path, default=Path("generation.json"))
    args = ap.parse_args()

    arrays = build()
    write_npz(args.out, arrays)
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    report = dict(
        status="GENERATED",
        seed=SEED,
        scenes=int(len(arrays["images"])),
        layouts=LAYOUTS,
        scenes_per_layout=SCENES_PER_LAYOUT,
        stations=STATIONS,
        resolution=RES,
        erase_fraction_max=ERASE,
        locality=LOCALITY,
        distinct_images=int(len({im.tobytes() for im in arrays["images"]})),
        sha256=digest,
    )
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
