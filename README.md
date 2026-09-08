# Uruguay settlement population estimates

Building footprints from Overture Maps provide an independent estimate of the population
inside Uruguay's 667 registered informal settlements. The analysis compares that estimate
with official national figures and settlement-level data from Montevideo.

## Main result

| Measure | Result |
|---|---:|
| Overture footprints in registered settlements | 82,392 |
| Central population estimate | 252,120 |
| Sensitivity range | 197,671–292,492 |
| Official INE estimate | 193,260 |
| Central estimate divided by INE estimate | 1.30 |

The central scenario assumes that 90% of footprints are homes, with 3.4 people per
dwelling. The full sensitivity sweep changes the footprint size threshold, residential
share, and people per dwelling.

The [analysis summary](results/settlement_analysis_summary.md) contains the complete
results, departamento table, and validation statistics.

## Run the analysis

The project requires Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run uruguay-settlements estimate
```

The first run reads the public Overture buildings dataset and downloads the official
Uruguayan source data. It stores reproducible inputs under `data/`; later runs reuse
those files.

The command writes:

| Output | Contents |
|---|---|
| [`settlement_analysis_summary.md`](results/settlement_analysis_summary.md) | National results, sensitivity analysis, and validation |
| [`settlement_estimates.geojson`](results/settlement_estimates.geojson) | Footprint counts and estimates for each settlement |
| [`montevideo_validation.csv`](results/montevideo_validation.csv) | Overture counts compared with Montevideo's register |

## Estimation method

The pipeline counts Overture building footprints that intersect each RNAI settlement
polygon. It converts those counts with:

```text
estimated dwellings  = footprints × residential share
estimated population = estimated dwellings × people per dwelling
```

The central scenario uses no minimum footprint size, a 90% residential share, and 3.4
people per dwelling. The sensitivity analysis evaluates alternative values instead of
treating those assumptions as measurements.

[Methodology](docs/methodology.md) explains the parameters, spatial join, and checks.
[Sources](docs/sources.md) records each input and the figures taken from it.
[Differences from Argentina](docs/differences-from-argentina.md) explains why the
replicated analysis uses different evidence and formulas.

## How to interpret the result

A footprint represents a structure, while the official estimate counts people in
households. Sheds, shops, missed small buildings, and multiple households within one
structure all affect the comparison. The national census remains the authoritative
population figure.

The available data provides several useful checks:

- Overture footprint counts correlate with Montevideo dwelling counts at 0.981 across
  338 matched settlements. The median settlement has 1.11 footprints per dwelling.
- Overture finds fewer than 10 footprints in 30 registered settlements, even though the
  national definition requires more than 10 dwellings.
- Building attributes cannot support a vertical-density adjustment. Among 82,392
  footprints, zero have height, 17 have floor counts, and 101 have a subtype.
- INE revised its national settlement-population estimate from 158,727 to 193,260 in May
  2026 after adjusting for census omission.

Use the outputs as an independent sensitivity analysis of building-footprint estimates.

## Project files

| Path | Purpose |
|---|---|
| `src/uruguay_settlements/` | Download, spatial analysis, estimation, and reporting code |
| `docs/` | Methodology and source documentation |
| `results/` | Committed analysis outputs |
| `tests/` | Unit tests |
| `.claude/skills/replicate-settlement-analysis/` | Reusable workflow for another country |

## Reuse for another country

The
[`replicate-settlement-analysis` skill](.claude/skills/replicate-settlement-analysis/SKILL.md)
guides an agent through evidence collection, design, validation, and reporting. It
requires country-specific sources for demographic assumptions.

## Development

```bash
uv sync --extra dev
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev prek run --all-files
```

The final command runs Vale and proselint across the Markdown documentation.

## Licence

The code is MIT licensed. Downloaded datasets retain their source terms: Overture
buildings use ODbL-1.0, RNAI comes from DINISU-MVOT, and Montevideo data uses the
Intendencia's open-data licence.
