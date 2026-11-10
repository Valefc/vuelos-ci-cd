# Monitoreo de demoras de vuelos NYC 2013 (CI/CD + Evidently)

Sistema que valida lotes de vuelos, compara las demoras de salida y llegada
con Evidently frente a enero de 2013 y publica el informe del último lote
válido en GitHub Pages.

- Sitio: https://TU_USUARIO.github.io/monitoreo-demoras-vuelos-nyc/
- Fuente de datos: nycflights13 (vuelos 2013 desde JFK, LGA y EWR)
- Autor: Valeria Figueroa

## Instalación

    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

## Ejecución local

    python scripts/preparar_lotes.py     # genera los lotes desde datos/original
    python scripts/validar.py            # valida referencia.csv y actual.csv
    pytest -q                            # pruebas automatizadas
    python scripts/generar_informes.py   # genera sitio/index.html y el informe de Evidently

## Datos

| Archivo | Contenido |
|---|---|
| datos/original/vuelos_nyc_2013.csv | CSV descargado, intacto (36.000 filas) |
| datos/referencia.csv | Enero 2013 (fijo) |
| datos/control.csv | Febrero 2013 |
| datos/nuevo.csv | Julio 2013 |
| datos/actual.csv | Copia de control.csv o nuevo.csv: es el lote que se publica |

## Reglas de validación

- Ocho encabezados y al menos una fila.
- vuelo_id: entero positivo y único.
- fecha: válida (AAAA-MM-DD) y del mes del lote.
- origen: JFK, LGA o EWR. destino: tres letras mayúsculas.
- Demoras: enteros (incluye cero y negativos). distancia_millas: entero positivo.
- referencia.csv solo contiene el lote referencia. actual.csv solo contiene control o nuevo.

## CI/CD

En cada push a main: instalar dependencias, pruebas, validación, generación del
sitio y subida del artefacto (job `ci`). El job `cd` depende de `ci` y despliega
en GitHub Pages el artefacto de esa misma ejecución. Si algo falla, `cd` se omite
y Pages conserva la última versión válida.