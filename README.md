# Informal settlement population from building footprints

How many people live in an informal settlement register, according to evidence that did
not come from the register? This repository answers that question twice: once as a
reusable method, and once as a finished analysis of Uruguay.

The method is the point. Uruguay is the demonstration that it runs.

## The skill

[`.claude/skills/replicate-settlement-analysis/SKILL.md`](.claude/skills/replicate-settlement-analysis/SKILL.md)
takes an agent from an official settlement register to an auditable population estimate,
anywhere the register exists. It walks eight phases: build an evidence matrix from
national sources, choose a design the local data can support, measure the building layer
instead of trusting it, join footprints to polygons, sweep every uncertain parameter,
interpret the gap against the official benchmark, verify, and write the research package.

Its governing rule is that a previous country's analysis tells you **which quantities to
investigate**, never what their values are. Persons per dwelling, residential share,
families per dwelling, and size thresholds are all local evidence. Carrying one across a
border makes the estimate a restatement of the source country.

The skill also refuses to make a discrepancy disappear. If the footprint count disagrees
with the official figure, that is a result. If the building layer is too thin to convert
structures into people, the correct output is a report saying so, not a population
number.

Point Claude Code at a country with a settlement register and invoke the skill. It
handles the research, the pipeline, and the documentation.

## The worked example: Uruguay

Uruguay is a hard test on purpose. INE already published an official asentamientos
population, 193,260 people, when it reweighted the Censo 2023 microdata in May 2026.
Running a footprint estimate against a country that has already measured itself is the
only way to learn whether the method is worth applying where nobody has.

```bash
uv sync
uv run uruguay-settlements estimate
```

The first run cuts a Uruguay-sized slice out of the Overture buildings layer. That step
reads the parquet footer of every part file in the global release before bbox pruning can
help, so it takes about six minutes and pulls down 6,237,966 buildings. Everything after
that is cached and the pipeline re-runs in six seconds.

Outputs land in `results/`:

| File | Contents |
|---|---|
| `settlement_analysis_summary.md` | The report: sensitivity sweep, departamento breakdown, validation |
| `settlement_estimates.geojson` | Per-settlement footprint counts and estimates |
| `montevideo_validation.csv` | Footprints against the Montevideo Observatorio's own counts |

### Results

Overture finds **82,392 footprints** inside the 667 registered settlements. At 90%
residential share and 3.4 persons per dwelling, that is **252,120 people**, 7.20% of
Uruguay's population and **1.30x** INE's figure of 193,260. Across the full sweep the
estimate runs from 197,671 to 292,492 people, or 1.02x to 1.51x INE.

Footprint counting overshoots, and three things explain most of the gap.

**The two counts measure different things.** A footprint is a structure. INE counts
people in households. Between them sit sheds, outbuildings, shops, and churches, and the
residential-share axis is a guess at how many. Even the most aggressive setting, 85%,
still lands above INE.

**Overture agrees with Montevideo's own register on shape, not on level.** Across the
338 settlements that join, footprint counts correlate with the Observatorio's dwelling
counts at **0.981**, but the median settlement has 1.11 footprints per dwelling. The
method ranks settlements well and overcounts them consistently.

**The benchmark is not fixed.** INE's own number moved from 158,727 to 193,260 in May
2026 after reweighting for a 10.3% census omission that fell hardest on low-income
households. Against the pre-revision figure the footprint estimate would have looked 59%
too high. Against the revised one it is 30% high. Nothing about the imagery changed.

Overture carries none of the attributes that would narrow any of this. Inside
settlements, 0 of 82,392 footprints have a `height`, 17 have a `num_floors`, and 101 have
a `subtype`. There is no vertical-density analysis to run, and no way to replace the
residential-share guess with a measurement.

Overture also undercounts in the other direction. Thirty of the 667 settlements hold
fewer than 10 footprints, which the INE-PIAI definition says is impossible, and one holds
none at all. Twenty of the thirty are in Montevideo, where settlements are densest and
structures smallest. The smallest footprint Overture places inside any settlement is
6.31 m², so the layer does not carry the small structures these places are built
from.

Full tables in [`results/settlement_analysis_summary.md`](results/settlement_analysis_summary.md).

### Method

For each settlement, count the Overture footprints that intersect it, then:

```
estimated_dwellings  = footprints x residential_share
estimated_population = estimated_dwellings x persons_per_dwelling
```

The sweep runs 3 footprint size filters x 4 residential shares x 3 persons-per-dwelling
values, 36 rows. Two of the size filters return the same footprint count, so 24 of those
rows are distinct. Only the persons-per-dwelling axis has a Uruguayan citation behind
every value:

| Persons per dwelling | Source |
|---|---|
| 3.0 | 3.4 carried forward on the national fall in household size, 2.82 (2011) to 2.5 (2023) |
| 3.4 | PMB-UEM 2012, Cuadro 5, from Censo 2011 |
| 3.55 | Implied by the Montevideo Observatorio de Asentamientos, April 2026 |

`docs/methodology.md` explains each parameter and what it can and cannot support.
`docs/sources.md` lists every source with its URL and the exact figure taken from it.

### Two checks the data makes possible

**The definition test.** INE-PIAI defines an asentamiento as a grouping of more than 10
dwellings, so every settlement in the register has at least 10. Any settlement where
Overture finds fewer than 10 footprints is a detection failure, and counting them
measures the floor on how much the footprint layer misses.

**Montevideo.** The Observatorio de Asentamientos publishes dwelling and person counts
for each of Montevideo's 345 active settlements, slightly over half the national total.
Comparing footprint counts to those figures settlement by settlement shows where the
method agrees and where it breaks down. Those counts never feed the national estimate,
because the Observatorio's own field sheet lists satellite building counting among its
sources, and calibrating on a partly footprint-derived reference would be circular.

## What Uruguay teaches about the next country

Two decisions here show why the skill insists on local evidence.

Uruguay's RNAI register has no household field. Its whole schema is `OBJECTID`,
`Codigo_AI`, `Nombre_AI`, `Nombre_dep`, `Codigo_dep`, `Nombre_loc`, `Codigo_loc`,
`Fecha_desd`, `GlobalID`. The Argentina analysis this replicates took
`max(footprint_estimate, official_families)` per settlement. With no second term, that
formula does not exist in Uruguay, and the design became footprints-forward. A missing
column changed the research design, not one parameter.

The Montevideo Observatorio would have been the obvious calibration target. Its field
sheet lists satellite building counting among its methods, so tuning the footprint
estimate against it would have measured Overture against imagery. It validates instead.

Every Argentine constant was dropped. `docs/differences-from-argentina.md` records what
carried over and what did not, which is the audit trail the skill asks every replication
to leave behind.

## Repository layout

| Path | Contents |
|---|---|
| `.claude/skills/replicate-settlement-analysis/` | The portable method |
| `src/uruguay_settlements/` | The Uruguay pipeline: download, optimize, join, sweep, report |
| `docs/` | Methodology, sources, and what changed from Argentina |
| `results/` | Committed outputs, regenerated by the pipeline |
| `tests/` | Arithmetic and parsing tests |

## Origin

This started as a replication of an
[Argentina analysis](https://gist.github.com/nlebovits/fd3e5f9a0e5ea1eeb4c6313917fbbbbe)
that joined VIDA footprints to the RENABAP register. Doing the replication honestly
produced the skill.

## Licence

MIT. The data it downloads carries its own terms: Overture buildings under ODbL-1.0,
RNAI from DINISU-MVOT, and the Montevideo settlement data under the Intendencia's open
data licence.
