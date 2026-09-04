# Methodology

## What the pipeline does

For each of the 667 settlements in the RNAI 2024 register, count the Overture Maps
building footprints that intersect it, then convert footprints to people:

```
estimated_dwellings  = footprints x residential_share
estimated_population = estimated_dwellings x persons_per_dwelling
```

Four phases, each timed:

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

The three bracket a plausible range. None is a national measurement for 2026, because
Uruguay has not published one. The last national figure is fifteen years old, and the
national trend since then has been downward: household size fell from 2.82 in 2011 to 2.5
in 2023. Whether asentamientos followed that trend is unknown, which is why 3.0 and 3.55
sit on either side of 3.4 rather than replacing it.

### Residential share

0.85, 0.90, 0.95, 1.00. **This is a declared assumption, not a citation.** It stands for
the fraction of footprints inside a settlement boundary that are dwellings rather than
sheds, outbuildings, shops, or churches. No Uruguayan source publishes it, and the sweep
exists so the reader can see how much the answer depends on a number nobody has measured.

### Footprint size filters

None, 6 m², and 10 m². Carried over from the Argentine analysis as generic noise filters.
They are not country-specific parameters and nothing here treats them as such.

### Central scenario

No size filter, 0.90 residential share, 3.4 persons per dwelling. The headline number and
the per-settlement outputs use it. No size filter, because Overture already under-detects
in these settlements and discarding small footprints would compound that. The other two
are the middle of their sweeps.

## Two checks the data makes possible

### Against the definition

INE-PIAI defines an asentamiento as a grouping of more than 10 dwellings, and DINISU has
applied that definition unchanged since 2006. Every settlement in the register therefore
has at least 10 dwellings. Wherever Overture finds fewer than 10 footprints, the footprint
layer has missed buildings known to exist.

This gives a floor on the undercount that needs no external data. It is a floor, not a
measure: a settlement with 40 footprints and 90 dwellings passes the check while being
badly undercounted.

### Against Montevideo

The Observatorio de Asentamientos publishes dwelling and person counts for each of
Montevideo's 345 active settlements, slightly over half the national total. Both registers
code a settlement as departamento + CCZ + serial, inherited from the INE-PIAI 2006 census,
so `Codigo_AI` and `id asentamiento` join directly.

These counts never feed the national estimate. The Observatorio's field sheet lists
"interpretación propia de imágenes aéreas o satelitales (conteo de construcciones)" among
its sources, so calibrating a footprint estimate on them would be partly circular. Reported
side by side they still show where footprint counting agrees with a register built from
field work, administrative files, and imagery together, and where it does not.

## Limits

**No national ground truth per settlement.** Uruguay publishes a settlement count and a
national population in asentamientos, but nothing in between. INE and DINISU began imputing
census data to individual settlements in January 2025 and that work is not published. When
it is, it supersedes this estimate.

**The benchmark itself moved 22% in one revision.** INE's figure for people in
asentamientos went from 158,727 to 193,260 in May 2026, after reweighting for a 10.3%
census omission that fell hardest on low-income households. Agreement or disagreement with
193,260 should be read against that, not as a fixed target.

**Footprints are not dwellings.** One footprint can hold several households, and one
household can spread across several structures. The residential share knob gestures at this
and does not solve it.

**Boundaries are approximate.** The RNAI service describes its polygons as "límites
aproximados." A footprint just outside a boundary is not counted and one just inside is,
and neither error is measured here.

**Overture is a mosaic.** Its coverage in informal settlements comes from a mix of
contributors and machine extraction, and it varies by place and by date. The definition
check measures how far that falls short in the aggregate. It cannot correct it.

**One data quality issue survives into the output.** A single record carries
`Nombre_dep = 'Nuevo Comienzo'`, which is a settlement name in a departamento field. It is
reported as its own row in the departamento table rather than silently reassigned. The
RNAI service also returns 344 Montevideo polygons where the RNAI report and the Montevideo
Observatorio both say 345.
