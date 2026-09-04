# Uruguay informal settlement population estimates

How many people live in Uruguay's asentamientos irregulares? This estimates it from
building footprints, by counting Overture Maps buildings inside the 667 settlement
polygons of the national register and converting footprints to people with published
Uruguayan ratios.

The estimate is deliberately independent of any official population count. Uruguay
already has one: INE put 193,260 people in asentamientos when it reweighted the Censo
2023 microdata in May 2026. Running a footprint count against that number tests whether
open building data can measure informal settlement population in a country that has
already measured it, which is the only way to know whether the method is worth applying
where no such measurement exists.

## Running it

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

## Results

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
6.31 m², so the layer simply does not carry the small structures these places are built
from.

Full tables in [`results/settlement_analysis_summary.md`](results/settlement_analysis_summary.md).

## Method

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

## Two checks the data makes possible

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

## Origin

This replicates an [Argentina analysis](https://gist.github.com/nlebovits/fd3e5f9a0e5ea1eeb4c6313917fbbbbe)
that joined VIDA footprints to the RENABAP register. Uruguay's register carries no
household count, so the Argentine formula has no second term to compare against, and
every Argentine constant has been replaced. `docs/differences-from-argentina.md` covers
what changed.

## Licence

MIT. The data it downloads carries its own terms: Overture buildings under ODbL-1.0,
RNAI from DINISU-MVOT, and the Montevideo settlement data under the Intendencia's open
data licence.
