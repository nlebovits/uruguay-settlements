# Sources

Every figure the pipeline uses, with the document it came from. All URLs accessed
2026-09-04.

## Settlement boundaries

**Registro Nacional de Asentamientos Irregulares (RNAI), capa 2024**
Dirección Nacional de Integración Social y Urbana (DINISU), Ministerio de Vivienda y
Ordenamiento Territorial.
<https://sit.mvot.gub.uy/arcgis/rest/services/05_MVOT/HABITAT_Y_VIVIENDA/MapServer/2>

667 polygons of settlements active at 2024-12-31. Fields: `OBJECTID`, `Codigo_AI`,
`Nombre_AI`, `Nombre_dep`, `Codigo_dep`, `Nombre_loc`, `Codigo_loc`, `Fecha_desd`,
`GlobalID`. There is no dwelling, household, or population field, which is the single
fact that most shapes this analysis.

Also catalogued at IDEuy:
<https://visualizador.ide.uy/geonetwork/srv/api/records/335f5f40-0aaa-4ccc-8997-c836d8ace6e2>

**Documento metodológico de síntesis y descripción de resultados de la actualización
cartográfica nacional de asentamientos irregulares 2024**
DINISU, Área de Diseño, Evaluación y Monitoreo. Montevideo, February 2025.
<https://sit.mvot.gub.uy/descargas/pdf/Informe_metodol%C3%B3gico_RNAI_2024_actualizado.pdf>

Taken from this report:

- 667 active settlements at 2024-12-31, across 18 of 19 departamentos and 91 census
  localities. Flores has none.
- The INE-PIAI 2006 definition, quoted verbatim on page 2: "Agrupamiento a partir de 10
  viviendas, ubicados en terrenos públicos o privados, construidos sin autorización del
  propietario en condiciones formalmente irregulares, sin respetar la normativa
  urbanística." This 10-dwelling floor is what makes the detection check possible.
- The series, corrected by DINISU in 2023-2024: 661 (2006), 638 (2011), 678 (2018), 691
  (March 2020), 667 (2024).
- Montevideo 345 and Canelones 128 in 2024, together 70.9% of the national total.
- The register carries no household or population counts. INE and DINISU began imputing
  census data to settlements in January 2025, and that work was still in progress when
  the report was written.

## Dwelling and person counts

**Asentamientos en Montevideo, April 2026**
Observatorio de Asentamientos Irregulares (OAI), División Tierras y Hábitat,
Intendencia de Montevideo. Updated every four months.
<https://ckan.montevideo.gub.uy/dataset/asentamientos-en-montevideo>

445 rows. Dropping `Regularizado`, `Relocalizado`, and `Dimensión dominial resuelta`
leaves 345 active settlements holding 37,413 viviendas and 132,874 personas, which
implies 3.55 persons per dwelling.

The field sheet (`OAI_Hoja descriptiva_Datos Abiertos_Asentamientos_Junio2025`) says the
viviendas and personas fields are estimates drawn from several sources: the INE-PIAI 2006
survey, the PMB-MVOT 2012 reprocessing of Censo 2011, departmental reports and files,
the Observatorio's own field surveys, and "interpretación propia de imágenes aéreas o
satelitales (conteo de construcciones)." That last source is why these counts validate
the footprint estimate but never calibrate it.

One discrepancy worth knowing: the field sheet states the geometry is EPSG:32721, but
the CSV's WKT holds decimal degrees, so it is EPSG:4326. The pipeline does not read that
geometry, joining on the settlement code instead.

**Relevamiento de asentamientos irregulares. Primeros resultados de población y
viviendas a partir del censo 2011**
Programa de Mejoramiento de Barrios, Unidad de Evaluación y Monitoreo. 2012.
<https://medios.presidencia.gub.uy/jm_portal/2012/noticias/NO_G241/piai-2011.pdf>

The last national measurement of population inside asentamientos:

- Cuadro 2: 589 settlements, 48,708 viviendas, 165,271 personas. Montevideo held 332
  settlements, 31,921 viviendas, and 112,101 personas.
- Cuadro 3, corrected 2006 figures for comparison: 662 settlements, 49,263 viviendas,
  179,545 personas.
- Cuadro 4: 5.5% of Uruguay's population in 2006, 5.0% in 2011.
- **Cuadro 5, persons per dwelling in asentamientos: 3.6 in 2006, 3.4 in 2011.** This is
  the source of the 3.4 value in the sweep.

**Relevamiento de asentamientos irregulares. Actualización de la cartografía nacional
2018**
Programa de Mejoramiento de Barrios, Unidad de Evaluación y Monitoreo.
<https://otu.opp.gub.uy/gestor/imagesbiblioteca/Asentamientos%20irregulares_informe_cartograf%C3%ADa2018_0.pdf>

This update mapped settlements without estimating households or people. Where it did need
dwelling counts, it got them the same way this analysis does: "La estimación de viviendas
se realizó a través de interpretación de imágenes satelitales." Settlements that appeared
after 2011 averaged 44 dwellings; those regularised or relocated in the same period
averaged 78.

## National population

**Censo 2023**
Instituto Nacional de Estadística.
<https://www.gub.uy/instituto-nacional-estadistica/censos2023pvh>

- Population 3,499,451; dwellings 1,659,044.
- 1,373,546 households in the May 2026 update, of which 1,309,448 urban and 64,098 rural.
- Average household size 2.5, down from 2.82 in Censo 2011. That ratio, 2.5 / 2.82, is
  what carries the 2011 persons-per-dwelling figure forward to the 3.0 sweep value.

**Censo 2023 ponderado**, published 2026-05-14.
<https://www.gub.uy/instituto-nacional-estadistica/comunicacion/noticias/censo-2023-ponderado>

INE reweighted the census microdata to correct an estimated 10.3% omission, against 4.1%
in 2011. The omission fell hardest on low-income households, so the settlement figure
moved most: **from 158,727 people (4.5% of the population) to 193,260 (5.5%)**. The
larger figure is the benchmark this analysis reports against.

Rural population was revised from about 142,000 to about 174,000 in the same exercise.

## Building footprints

**Overture Maps, buildings theme, release 2026-08-19.0**
<https://docs.overturemaps.org/buildings/building>
Licence ODbL-1.0. Read directly from
`s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building/`.

Documented in the Portolan mirror at
<https://github.com/nlebovits/overture-portolan>, which is where the column semantics,
release path, and asset layout for this analysis came from.
