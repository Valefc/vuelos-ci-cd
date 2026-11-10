import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

MESES = {1: "enero", 2: "febrero", 7: "julio"}
COLS = ["demora_salida_min", "demora_llegada_min"]
AUTOR = "Valeria Figueroa"
SALIDA = Path("sitio")
SALIDA.mkdir(exist_ok=True)

ref = pd.read_csv("datos/referencia.csv")
act = pd.read_csv("datos/actual.csv")

mes_act = MESES[pd.to_datetime(act["fecha"]).dt.month.iloc[0]]
mes_ref = MESES[pd.to_datetime(ref["fecha"]).dt.month.iloc[0]]

# Evidently (misma configuración para febrero y julio)
reporte = Report(metrics=[DataDriftPreset(columns=COLS)])
reporte.run(reference_data=ref[COLS], current_data=act[COLS])
nombre_informe = f"informe_{mes_act}_vs_{mes_ref}.html"
reporte.save_html(str(SALIDA / nombre_informe))

# Resumen de drift (si falla la lectura, no rompe el sitio)
resumen = "No disponible"
try:
    for m in reporte.as_dict()["metrics"]:
        r = m["result"]
        if "number_of_drifted_columns" in r:
            resumen = (f"{r['number_of_drifted_columns']} de "
                       f"{r['number_of_columns']} variables con drift")
except Exception:
    pass

# Commit
commit = os.environ.get("GITHUB_SHA")
if not commit:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "desconocido"

generado = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
med_sal = act["demora_salida_min"].median()
med_lle = act["demora_llegada_min"].median()

html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Monitoreo de demoras NYC 2013</title>
<style>body{{font-family:Arial,sans-serif;max-width:760px;margin:40px auto;padding:0 16px}}
td,th{{border:1px solid #ccc;padding:6px 12px;text-align:left}}table{{border-collapse:collapse}}</style>
</head><body>
<h1>Monitoreo de demoras en vuelos de Nueva York (2013)</h1>
<h2>Último mes publicado: {mes_act.capitalize()}</h2>
<table>
<tr><th>Registros analizados</th><td>{len(act):,}</td></tr>
<tr><th>Mediana demora de salida (min)</th><td>{med_sal:g}</td></tr>
<tr><th>Mediana demora de llegada (min)</th><td>{med_lle:g}</td></tr>
<tr><th>Resultado de drift</th><td>{resumen}</td></tr>
<tr><th>Fecha de generación</th><td>{generado}</td></tr>
<tr><th>Commit</th><td>{commit[:7]}</td></tr>
</table>
<p><a href="{nombre_informe}">Informe Evidently: {mes_act} vs {mes_ref}</a></p>
<hr>
<p>Autor: {AUTOR}<br>
Fuente: paquete <a href="https://cran.r-project.org/package=nycflights13">nycflights13</a>
(vuelos 2013 desde JFK, LGA y EWR; muestra de 12.000 vuelos por mes).</p>
</body></html>"""
(SALIDA / "index.html").write_text(html, encoding="utf-8")
print("Sitio generado:", mes_act, "vs", mes_ref, "| commit", commit[:7])