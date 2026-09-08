# Methodology

## Pipeline stages

For each of the 667 settlements in the RNAI 2024 register, the pipeline counts the
intersecting Overture Maps building footprints and converts footprints to people:

```
estimated_dwellings  = footprints x residential_share
estimated_population = estimated_dwellings x persons_per_dwelling
```

The pipeline records the duration of each phase.

1. **Download.** The RNAI polygons through `gpio.extract_arcgis`, which pages the ArcGIS
   service and reprojects to EPSG:4326. The Montevideo Observatorio CSV over HTTP. The
   Overture buildings through a DuckDB query against the public S3 bucket, filtered to
   Uruguay's bounding box.
2. **Optimize.** Both layers get a bbox column and Hilbert ordering. Hilbert curves keep
   spatial neighbours in the same parquet row group, so the join reads a fraction of the
   buildings file instead of all of it.
3. **Join and sweep.** A bbox comparison rejects almost every building in the country
   with four double comparisons, and only survivors pay for `ST_Intersects`. Footprint
   areas come from `ST_Area(ST_Transform(geometry, 'EPSG:4326', 'EPSG:32721'))`, because
   areas in EPSG:4326 are square degrees and useless as a size filter.
4. **Report.** Per-settlement GeoJSON, the Montevideo validation CSV, and the summary.

## Parameters

### Persons per dwelling

The only axis where every value has a Uruguayan source.

| Value | Basis |
|---|---|
| 3.0 | 3.4 carried forward on the national fall in household size: 3.4 x (2.5 / 2.82) = 3.01 |
| 3.4 | PMB-UEM 2012, Cuadro 5, from Censo 2011 |
| 3.55 | Implied by the Montevideo Observatorio, April 2026: 132,874 / 37,413 |

Together, these values bracket a plausible range. None is a national measurement for 2026, because
Uruguay has not published one. The last national figure is fifteen years old, and the
national trend since then has been downward: household size fell from 2.82 in 2011 to 2.5
in 2023. Whether asentamientos followed that trend is unknown, so 3.0 and 3.55
sit on either side of 3.4 rather than replacing it.

### Residential share

0.85, 0.90, 0.95, 1.00. **This declared assumption lacks a citation.** It stands for
the fraction of footprints inside a settlement boundary that are dwellings rather than
sheds, outbuildings, shops, or churches. No Uruguayan source publishes it, and the sweep
exists so the reader can see how much the answer depends on a number nobody has measured.

### Footprint size filters

None, 6 m², and 10 m². Carried over from the Argentine analysis as generic noise filters,
they are generic rather than country-specific parameters.

On this data the 6 m² filter is inert. The smallest Overture footprint inside any
settlement is 6.31 m², so that filter and no filter return the same 82,392 footprints, and
the 36-row sweep holds 24 distinct results. The 10 m² filter removes 4,874 footprints, or
5.9%. The report flags the degenerate filter rather than leaving two identical blocks of
rows unexplained.

### Central scenario

No size filter, 0.90 residential share, 3.4 persons per dwelling. The headline number and
the per-settlement outputs use it. No size filter, because Overture already under-detects
in these settlements and discarding small footprints would compound that. The other two
are the middle of their sweeps.

## Checks supported by the data

### Against the definition

INE-PIAI defines an asentamiento as a grouping of more than 10 dwellings, and DINISU has
applied that definition unchanged since 2006. Each settlement in the register has at
least 10 dwellings, so fewer than 10 Overture footprints reveal missing buildings.

This gives a floor on the undercount that needs no external data. It is a floor, not a
measure: a settlement with 40 footprints and 90 dwellings passes the check while being
badly undercounted.

### Montevideo validation

The Observatorio de Asentamientos publishes dwelling and person counts for each of
Montevideo's 345 active settlements, slightly over half the national total. Both registers
code a settlement as departamento + CCZ + serial, inherited from the INE-PIAI 2006 census,
so `Codigo_AI` and `id asentamiento` join directly.

The national estimate excludes these counts. The Observatorio's field sheet lists
"interpretación propia de imágenes aéreas o satelitales (conteo de construcciones)" among
its sources, so calibrating a footprint estimate on them would be partly circular. Reported
side by side they still show where footprint counting agrees with a register built from
field work plus administrative and imagery sources, and where it does not.

## Limits

**No national ground truth per settlement.** Uruguay publishes a settlement count and a
national population in asentamientos, but nothing in between. INE and DINISU began imputing
census data to individual settlements in January 2025 and that work is not published. When
it is, it supersedes this estimate.

**The benchmark itself moved 22% in one revision.** INE's figure for people in
asentamientos went from 158,727 to 193,260 in May 2026, after reweighting for a 10.3%
census omission that fell hardest on low-income households. Agreement or disagreement with
193,260 should be read against that, not as a fixed target.

**Footprints are not dwellings.** One footprint can contain several households, and one
household can spread across several structures. The residential share knob gestures at this
and does not solve it.

**One footprint can be counted twice.** A building inside two overlapping settlement
polygons joins to both. Exactly one of the 667 polygons overlaps another, so the effect
is negligible here, but the join does not deduplicate.

**Boundaries are approximate.** The RNAI service describes its polygons as "límites
aproximados." A footprint just outside a boundary is not counted and one just inside is,
and neither error is measured here.

**The attribute columns are empty.** Overture publishes `height`, `num_floors`, and
`subtype`, and inside Uruguayan settlements all three are effectively absent: 0, 17, and
101 of 82,392 footprints respectively. That rules out a vertical-density analysis and
prevents the residential share from being measured instead of assumed. `attribute_coverage`
in `pipeline.py` computes these figures on every run.

**Overture combines multiple sources.** Coverage in informal settlements comes from
contributors and machine extraction, and varies by place and date. The definition check
measures aggregate coverage gaps but cannot correct them.

**The output retains one source-data problem.** One record has
`Nombre_dep = 'Nuevo Comienzo'`, which is a settlement name in a departamento field. It is
reported as its own row in the departamento table rather than silently reassigned. The
RNAI service also returns 344 Montevideo polygons where the RNAI report and the Montevideo
Observatorio both say 345.
