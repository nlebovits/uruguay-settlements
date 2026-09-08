# What changed from the Argentina analysis

This replicates an
[Argentina analysis](https://gist.github.com/nlebovits/fd3e5f9a0e5ea1eeb4c6313917fbbbbe)
that joined VIDA building footprints to the RENABAP settlement register. The shape of the
pipeline carried over. Almost nothing else did.

## The formula lost a term

Argentina's estimate was:

```
max(building_count x occupation_rate x 1.1, renabap_families)
```

It takes the larger of a footprint estimate and RENABAP's own `familias_aproximadas`,
reading a higher official count as vertical density and a higher footprint count as
official undercounting.

Uruguay's RNAI layer has no household field. Its full schema is `OBJECTID`, `Codigo_AI`,
`Nombre_AI`, `Nombre_dep`, `Codigo_dep`, `Nombre_loc`, `Codigo_loc`, `Fecha_desd`,
`GlobalID`. There is nothing to take a maximum against, so Uruguay's estimate runs
footprints-forward only:

```
footprints x residential_share x persons_per_dwelling
```

Everything downstream follows from that. The missing per-settlement official count
removes the vertical-density comparison and per-settlement source attribution. It also
prevents detection of places where the official register captured more than the imagery.

## Country-specific constants

| Argentina | Uruguay | Why |
|---|---|---|
| 1.1 families per dwelling (SISU 2023a) | dropped | An Argentine multiplier for an Argentine register. Uruguay has no equivalent, and there is no household count to apply it to. |
| 2.8 persons per household (INDEC 2022) | 3.0 / 3.4 / 3.55 | Uruguayan sources: PMB-UEM 2012 measured 3.4 persons per dwelling in asentamientos, the Montevideo Observatorio implies 3.55, and the national fall in household size gives 3.0. |
| 3.35 persons, barrios-specific | dropped | Argentina-specific. |
| 46,700,000 population | 3,499,451 | INE, Censo 2023. |
| "Occupation rate" | "Residential share" | Same 0.85 to 1.00 sweep, honest label. It measures how many footprints are dwellings, not how many dwellings are occupied. |

## Geography

Argentina's CABA / Conurbano-AMBA / Other Gran Aglomerados / Outside tiers and its
27-partido Conurbano list are gone. Uruguay reports by departamento, which is how the RNAI
2024 report presents its own results.

## Layers dropped and added

**Dropped: the urban-areas intersection.** Argentina split settlements by whether they
intersect IGN Planta Urbana polygons. RNAI settlements sit in 91 census localities and are
urban by construction, so the split would separate nothing.

**Dropped: vertical density.** That analysis needed the RENABAP household count to compare
against. Overture's own height fields cannot stand in, and the shortfall is not marginal:

| Attribute | All Uruguay | Inside settlements |
|---|---|---|
| `height` | 3,004 of 6,237,966 (0.05%) | 0 of 82,392 (0.00%) |
| `num_floors` | 24,224 (0.39%) | 17 (0.02%) |
| `subtype` | 53,603 (0.86%) | 101 (0.12%) |

Overture reports height for zero buildings inside Uruguayan settlements. The 17 with a
floor count are too few to support analysis. `subtype` has the same problem, so the residential
share stays a declared assumption rather than a measurement: Overture cannot say which of
these footprints are dwellings. The pipeline reports these figures rather than asserting
them, so they update with each Overture release.

**Added: the definition check.** Uruguay's settlement definition carries a numeric floor of
10 dwellings, applied unchanged since 2006. Counting settlements where Overture finds fewer
than 10 footprints measures detection failure with no external data. Argentina's definition
has no such threshold.

**Added: Montevideo validation.** Argentina had a household count for every settlement and
built it into the estimate. Uruguay has one for 345 settlements, from a register that
partly uses satellite building counting itself, so it is reported beside the estimate
rather than folded into it.

## Footprints

Argentina used the VIDA Google/Microsoft/OSM Open Buildings mosaic, which provides a national
ARG parquet with an `area_in_meters` column. Uruguay uses Overture Maps release
2026-08-19.0, read straight from the public bucket and cut to a bounding box. Overture has
no area column, so footprint areas are computed with `ST_Transform` into EPSG:32721, the
UTM zone covering Uruguay.

The gpio optimization step uses the same bbox column, Hilbert ordering, and GeoParquet 1.1
structure. Those choices organize both source files for a spatial join.
