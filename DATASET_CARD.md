# Degraded Traverse Records

## What this dataset contains

This is an original synthetic corpus of 3,400 survey traverse records. It was generated in full by a single deterministic program; no third-party imagery, survey measurement, map, or label is included or redistributed.

A traverse record describes one field survey. A network of 13 stations was established, and a surveyor walked a route that visited every station exactly once. The route was drawn onto a plan as straight legs between consecutive stations. The plan then degraded: on each leg a contiguous interior span of the line faded away, leaving both ends attached to their stations but the middle missing. The surveyed station coordinates and the station the route began from survived in the field book. The visiting order did not.

Each record therefore holds a 72x72 raster of the degraded plan, the 13 station coordinates, the starting station, and the true visiting order that produced the plan.

## Files

The raw upload contains exactly two files at the archive root.

- **`scenes.npz`** - a compressed NumPy archive holding the six arrays described below
- **`DATA_LICENSE.txt`** - the CC0 1.0 dedication and a statement of original authorship

## Arrays in `scenes.npz`

- **`images`** - `(3400, 72, 72)`, `uint8` - the degraded plan raster, 0 to 255
- **`ports`** - `(3400, 13, 2)`, `float32` - station xy coordinates in raster pixel units, 0 to 71
- **`visit_order`** - `(3400, 13)`, `int8` - the true route, a permutation of the station indices
- **`start_station`** - `(3400,)`, `int8` - the first entry of `visit_order`, repeated for convenience
- **`layout_id`** - `(3400,)`, `int32` - which station layout this record belongs to, 0 to 849
- **`raw_id`** - `(3400,)`, string - SHA-256 over the record's image and coordinates

## How the corpus was created

Every value comes from the published generator. The seven steps are deterministic under a fixed seed.

1. Draw 13 station positions uniformly in the unit square, rejecting any position closer than 0.115 to one already accepted.
2. Sort the stations by coordinate and number them in that spatial order, so a station number never reveals when it was visited.
3. Choose a starting station uniformly at random.
4. Extend the route one station at a time. With probability 0.45 step to the nearest station not yet visited; otherwise step to a uniformly random one. This keeps the route partly local, so coordinates alone remain weakly informative but far from sufficient.
5. Draw each leg as an anti-aliased straight line of half-width 0.9 pixels, then erase one contiguous interior span covering up to 88 percent of the leg. Both endpoints stay attached.
6. Mark every station with a small bright disc and add Gaussian pixel noise with standard deviation 0.05.
7. Quantise to 8-bit and hash the record.

Each of the 850 station layouts is reused for 4 independent routes, which is what makes a layout-disjoint split meaningful.

## Grouping and independence

The independent unit is the **station layout**, not the individual record. Four records share each layout, and they are correlated because they share station positions. Any split must keep whole layouts together. The preparation script does exactly this: 600 layouts become the fitting fold, 100 become the validation fold, and 150 are held back for evaluation.

## Intended use

This corpus is intended as a controlled benchmark for combinatorial structure recovery from degraded raster evidence. It suits research on jointly scoring local visual evidence and decoding a globally consistent permutation, and on how much a hard global constraint recovers when local evidence alone is ambiguous.

It is suitable for training and evaluating models that read a raster and emit a constrained ordering. It is not a source of survey data, a model of real surveying practice, or a basis for any geospatial measurement.

## Known limitations

- The corpus is entirely synthetic. It does not represent real survey plans, real drafting conventions, real paper or film degradation, or any real terrain.
- Degradation is a single contiguous erased span per leg plus uniform Gaussian noise. Real document decay involves stains, folds, tears, uneven fading and scanning artefacts, none of which appear here.
- Every network has exactly 13 stations, every route visits each station exactly once, and legs are always straight. Branching routes, repeated visits, curved traverses and missing stations are out of scope.
- Station coordinates are supplied without measurement error. Real surveys carry positional uncertainty.
- Route generation uses one fixed locality parameter. Conclusions drawn here need not transfer to routes that are far more local or far more arbitrary.
- The rasters are 72x72 and single channel. Behaviour at higher resolution or with colour separation is not established.

## Licence and provenance

Released under Creative Commons CC0 1.0 Universal, <https://creativecommons.org/publicdomain/zero/1.0/>.

The corpus is original work produced by the generator published with it. Because no external material is incorporated, no upstream licence, attribution requirement or redistribution restriction applies.
