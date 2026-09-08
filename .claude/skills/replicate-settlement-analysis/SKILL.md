---
name: replicate-settlement-analysis
description: Replicate a building-footprint analysis of informal-settlement population for a new country or territory. Use when adapting Barrios Visibles or a similar analysis to informal settlements, slums, barrios populares, asentamientos irregulares, camps, or other official settlement polygons. Research local official data and demographic parameters, choose an analysis design supported by those data, join building footprints to settlement boundaries, run sensitivity and data-quality checks, validate against independent official evidence where possible, and produce a reproducible research package. Replicate the research question, not another country's formula.
---

# Replicate informal-settlement population analysis

Replicate a building-footprint analysis of informal-settlement population for a new
country or territory.

The core question is:

> What does independent building-level evidence tell us about the population represented
> by the official informal-settlement data?

Do not assume the target country supports the same calculation as a previous analysis.

**Replicate the question, not the formula.**

## Principles

1. **Use the target country's evidence.** Never carry demographic constants, settlement
   classifications, administrative groupings, or formulas from another country without
   local justification.

2. **Choose the method after inspecting the data.** The fields available in the official
   settlement dataset determine what can be estimated or compared.

3. **Keep evidence independent where possible.** Do not calibrate a footprint estimate
   against a reference dataset that was itself substantially produced from satellite or
   building counting unless the methodological dependence is explicitly modeled. Use
   partially dependent sources as validation or comparison instead.

4. **Measure before asserting.** If a claim can be tested from the data, query it. Do not
   write that height, floor count, building type, coverage, or another attribute is
   "sparse" without reporting measured coverage.

5. **Do not tune toward the official answer.** A discrepancy from an official benchmark
   is a result, not a parameter-fitting problem.

6. **Expose uncertainty.** Put uncertain but defensible transformations into sensitivity
   analysis. Never hide an unsupported constant inside the central estimate.

7. **A failed replication is a valid result.** If building coverage is too weak, official
   boundaries are unusable, or population conversion cannot be supported, report that
   instead of forcing a population estimate.

## Before implementation

Inspect:

- the current repository;
- any reference analysis supplied by the user;
- the official settlement source;
- the building-footprint source and its schema;
- existing repository instructions and conventions.

If this repository already contains a completed country analysis, treat it as a worked
implementation, not as a source of demographic assumptions.

When adapting Barrios Visibles, understand the original method before changing it.
Identify separately:

- the research question;
- spatial operations;
- demographic assumptions;
- country-specific classifications;
- validation strategy;
- output structure.

Do not copy country-specific parameters merely because working code already contains
them.

## Phase 1: build the evidence matrix

Research the target country before writing the estimator.

Prefer primary sources in this order:

1. national statistical office;
2. ministry or agency maintaining the settlement register;
3. official census or post-enumeration documentation;
4. official municipal or subnational datasets;
5. peer-reviewed or institutional literature where official evidence is unavailable.

For each relevant input, record:

| Field | Meaning |
|---|---|
| Variable | What is being measured |
| Value(s) | Exact value or range |
| Unit | Persons, households, dwellings, etc. |
| Geography | National, regional, settlement-level |
| Vintage | Observation/reference date |
| Source | Primary URL and document/table/page where possible |
| Role | Input, calibration, validation, or benchmark |
| Independence | Whether it shares data or methods with the footprint estimate |
| Notes | Limitations or interpretation |

At minimum investigate:

- official settlement definition;
- settlement polygon count and vintage;
- stable settlement identifier;
- official population field, if any;
- official household/family field, if any;
- official dwelling field, if any;
- persons per dwelling;
- persons per household;
- households/families per dwelling where relevant;
- national population;
- official aggregate informal-settlement population;
- independent settlement-level reference datasets;
- meaningful local administrative/geographic groupings.

Record sources in `docs/sources.md` or the repository's equivalent.

### Never inherit constants

Values from another country are evidence about that country only.

For example, do not inherit:

- families per dwelling;
- persons per household;
- persons per dwelling;
- occupation or residential-share assumptions;
- urban classifications;
- metropolitan rings;
- footprint-size thresholds;
- vertical-density corrections.

A previous analysis can suggest **which quantities to investigate**, never what their
values should be.

## Phase 2: choose the analysis design

Choose the strongest design the target data support.

### A. Official settlement-level households or dwellings exist

Compare building evidence directly against the official counts for each settlement.

Possible outputs include:

- footprints / official dwellings;
- footprints / official households;
- geographic distribution of discrepancies;
- settlement-level conservative floors, **only if the relationship is substantively
  justified**.

Do not automatically reproduce a `max(official, footprint-derived)` formula from another
country.

### B. No official settlement-level counts exist

Use a footprints-forward analysis only if country-specific evidence supports conversion
from structures to dwellings or people.

Possible form:

```text
estimated_dwellings =
    building_count
    x residential_share
    x other locally justified adjustment

estimated_population =
    estimated_dwellings
    x persons_per_dwelling
```

Every multiplier must be either:

- empirically supported for the target country; or
- explicitly labeled as an assumption and included in sensitivity analysis.

If no defensible population conversion exists, stop at building/dwelling evidence. Do not
manufacture a national population estimate.

### C. Independent reference data exist

Use them for validation.

Prefer settlement-level validation over a single national total.

Report, where meaningful:

- number and percentage of settlements matched;
- unmatched IDs;
- correlation;
- median ratio;
- mean or median absolute error;
- systematic bias;
- geographic pattern in errors;
- large outliers.

High correlation does not imply unbiased estimates. Report level agreement separately.

### Calibration versus validation

Before using a dataset for calibration, inspect how it was created.

If the reference count itself uses:

- satellite-image interpretation;
- automated building footprints;
- manual structure counting from imagery;
- the same census-derived inputs used by the estimator;

then calibration can become circular.

Unless there is a clear reason otherwise, keep such a source out of the estimating
formula and use it as a comparison or validation dataset.

Document this decision.

## Phase 3: inspect the building data

Do not treat a global building dataset as ground truth.

Measure its properties over the target country and, separately, inside settlement
polygons.

At minimum report:

- total footprint count;
- footprint count inside settlements;
- footprint area distribution;
- minimum observed footprint area;
- settlements with zero footprints;
- settlements with suspiciously low footprint counts;
- `height` coverage, if available;
- floor-count coverage, if available;
- building type/subtype/class coverage, if available;
- source or confidence fields, if relevant.

If the official settlement definition establishes a useful invariant, turn it into a QA
test.

Example:

> If an official settlement must contain at least N dwellings, any registered settlement
> with fewer than N detected building footprints is evidence of footprint under-detection
> or geometry mismatch.

Report these failures. Do not silently remove the settlements.

### Attribute coverage

For every attribute you want to use analytically, calculate:

```text
coverage = non_null_values / relevant_buildings
```

Calculate coverage both:

- nationally; and
- inside settlement polygons.

If coverage is too low to support an analysis, say so with the measured number and omit
that analysis.

Do not infer building height, vertical density, or residential use from fields that are
effectively absent.

## Phase 4: acquire and normalize data

Use the source's stable identifiers and preserve source attributes wherever practical.

Cache expensive downloads locally.

For large remote GeoParquet datasets:

1. inspect the schema first;
2. use bbox predicates for row-group pruning;
3. reduce to the target country or study area;
4. then use exact spatial predicates such as `ST_Intersects`.

Do not guess column names.

Where optimization materially improves the join, convert source data to spatially
organized GeoParquet with:

- bounding-box covering metadata;
- spatial/Hilbert ordering;
- appropriate row-group sizing;
- compression.

Keep raw reproducible inputs out of version control when large. Record exact source URLs,
releases, and retrieval dates.

Do not silently repair geometry. If `make_valid`, buffering, snapping, centroid
replacement, or another geometric intervention is necessary, document the operation and
its effect.

Use a locally appropriate projected CRS for area calculations. Do not carry the CRS from
another country.

## Phase 5: spatial analysis

The basic operation is settlement-level aggregation of building footprints.

Prefer explicit bbox pruning before exact intersection where supported:

```text
candidate building bbox intersects settlement bbox
AND
ST_Intersects(settlement_geometry, building_geometry)
```

Produce one canonical settlement-level table containing, where available:

- settlement ID;
- settlement name;
- administrative geography;
- polygon geometry;
- raw building count;
- counts under each size threshold;
- official dwellings;
- official households/families;
- official population;
- building-derived estimates;
- comparison ratios;
- QA flags.

Keep descriptive classifications separate from variables that generate the estimate.

## Phase 6: sensitivity analysis

Sensitivity analysis is required whenever uncertain parameters affect the headline
result.

Potential axes include:

- minimum building area;
- residential share;
- occupancy;
- structures-to-dwellings ratio;
- households per dwelling;
- persons per dwelling;
- persons per household;
- other locally justified adjustments.

Use ranges supported by local evidence when possible.

For assumptions without empirical support:

1. label them as assumptions;
2. explain what uncertainty they represent;
3. sweep a plausible range;
4. do not describe one arbitrary value as measured.

### Check that each sensitivity axis is real

After running the sweep, verify that changing each parameter changes the underlying data
or result.

If two filters produce identical data, report the axis as degenerate or inert.

Do not show duplicate scenarios as though they were independent evidence.

Choose a central scenario from the best a priori local evidence, not from whichever
parameters make the result closest to an official benchmark.

## Phase 7: interpret discrepancies

Treat over-counting and under-counting symmetrically.

Potential causes include:

- footprint false positives;
- footprint false negatives;
- non-residential structures;
- multi-dwelling structures;
- vertical construction;
- stale official boundaries;
- stale enumeration;
- mismatched vintages;
- census omission;
- differing settlement definitions;
- geometry errors;
- registry coverage gaps.

Test explanations where the available data permit.

Distinguish:

- **coverage:** whether the settlement exists in the official register;
- **internal enumeration:** whether the people/dwellings within an existing polygon are
  counted correctly;
- **footprint detection:** whether the building dataset captures the built stock;
- **population conversion:** whether detected structures can defensibly be translated
  into people.

Do not collapse these into a single "undercount" explanation.

## Phase 8: verification

Before reporting results:

1. Verify settlement IDs and feature counts against official metadata.
2. Report source vintages.
3. Test the spatial join on known settlements.
4. Measure building attribute coverage.
5. Run definition-based QA checks where possible.
6. Inspect settlements with zero or implausibly low footprint counts.
7. Verify sensitivity axes are not accidentally inert.
8. Check reference-data join rates.
9. Inspect major outliers.
10. Run the complete pipeline from clean inputs.
11. Run tests and repository lint/type/style checks.
12. Re-run the analysis after any methodological change so committed results match
    committed code.

Do not hard-code a mutable registry's current feature count as an eternal invariant. Pin
a source vintage or report drift explicitly.

## Required outputs

Fit the existing repository structure when one exists. Otherwise prefer:

```text
src/
    reproducible analysis code

tests/
    arithmetic tests
    parsing/schema tests
    data-quality invariants

results/
    settlement_estimates.geojson or parquet
    analysis_summary.md
    validation.csv              # when available

docs/
    methodology.md
    sources.md
    differences-from-reference.md

README.md
```

### `docs/methodology.md`

Explain:

- research question;
- datasets;
- analysis design;
- formula;
- every parameter;
- sensitivity analysis;
- validation;
- data-quality checks;
- limitations;
- what the analysis cannot support.

### `docs/sources.md`

For every substantive external number include:

- publisher;
- title;
- URL;
- publication/reference date;
- access date;
- table/page/field where possible;
- exact quantity taken from it;
- how that quantity enters the analysis.

### `docs/differences-from-reference.md`

If adapting a prior country analysis, explain:

- what carried over;
- what did not;
- which inputs were unavailable;
- which assumptions were replaced;
- why the estimating formula changed;
- which analyses became possible or impossible;
- which validation opportunities are new.

This document should make methodological adaptation auditable.

### `results/analysis_summary.md`

Include:

- headline result;
- full sensitivity range;
- central scenario and why it was chosen;
- comparison with official benchmark(s);
- geographic breakdown;
- footprint QA;
- validation results;
- important outliers;
- limitations.

Do not report only the central estimate.

## Research and citation rules

Prefer original official documents over summaries or search-result snippets.

For every externally sourced claim that affects the methodology:

- open the underlying source;
- verify the value in context;
- capture its date and geography;
- cite it in the repository.

Do not treat a derived arithmetic result as an independent source.

If two official sources disagree, report the disagreement and determine whether they
represent different vintages, definitions, or revisions.

Never silently select the value that best fits the building estimate.

## Autonomy

Proceed without unnecessary methodological questions.

If reasonable alternatives exist:

1. choose the most conservative design supported by the evidence;
2. put uncertain choices into sensitivity analysis;
3. document the decision.

Ask the user only when the unresolved choice changes the research question itself or when
required source data cannot be identified.

Do not stop merely because the target country's data differ from the reference analysis.
Adapting to that difference is the purpose of this skill.

## Completion criteria

The replication is complete only when:

- country-specific sources replace inherited assumptions;
- the estimating design matches the data available;
- expensive factual claims about the building dataset are measured;
- uncertainty is visible in sensitivity analysis;
- validation is methodologically independent or its dependence is disclosed;
- known data failures remain visible;
- outputs reproduce from code;
- tests pass;
- results and documentation agree;
- the repository states clearly what can and cannot be concluded.

A clean spatial join is not completion. The objective is a defensible, auditable
comparison between official settlement data and independent built evidence.

## The worked example in this repository

Uruguay is one pass through these phases. Read it for the shape of the work, never for
its numbers.

| File | What it demonstrates |
|---|---|
| `docs/sources.md` | The evidence matrix of Phase 1, one entry per external number |
| `docs/differences-from-argentina.md` | Phase 2 design change forced by a missing field, and every Argentine constant dropped |
| `src/uruguay_settlements/pipeline.py` | Phase 4 and Phase 5: bbox pruning, Hilbert ordering, `ST_Intersects`, attribute coverage |
| `src/uruguay_settlements/config.py` | Parameters isolated from code, each with its citation |
| `results/settlement_analysis_summary.md` | Phase 6 sweep, Phase 7 discrepancy analysis, Phase 8 QA output |
| `tests/` | Arithmetic tests and parsing tests that survive a parameter change |

Two decisions there show the principles under load. Uruguay's register carries no
household field, so the Argentine `max(footprint_estimate, official_families)` formula
lost its second term and the design changed to footprints-forward. The Montevideo
Observatorio publishes settlement-level dwelling counts, but its field sheet lists
satellite building counting among its sources, so it validates the estimate and never
calibrates it.
