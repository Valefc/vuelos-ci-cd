import os
import subprocess
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

MESES = {1: "enero", 2: "febrero", 7: "julio"}
COLS = ["demora_salida_min", "demora_llegada_min"]
NOMBRES = {"demora_salida_min": "Demora de salida",
           "demora_llegada_min": "Demora de llegada"}
AUTOR = "Valeria Figueroa"
SALIDA = Path("sitio")
SALIDA.mkdir(exist_ok=True)

ref = pd.read_csv("datos/referencia.csv")
act = pd.read_csv("datos/actual.csv")

mes_act = MESES[pd.to_datetime(act["fecha"]).dt.month.iloc[0]]
mes_ref = MESES[pd.to_datetime(ref["fecha"]).dt.month.iloc[0]]

# ---------------------------------------------------------------- Evidently
reporte = Report(metrics=[DataDriftPreset(columns=COLS)])
reporte.run(reference_data=ref[COLS], current_data=act[COLS])
nombre_informe = f"informe_{mes_act}_vs_{mes_ref}.html"
reporte.save_html(str(SALIDA / nombre_informe))

drift = {}          # columna -> (detectado, score, test)
n_drift, n_cols = None, None
try:
    for m in reporte.as_dict()["metrics"]:
        r = m["result"]
        if "number_of_drifted_columns" in r:
            n_drift = r["number_of_drifted_columns"]
            n_cols = r["number_of_columns"]
        if "drift_by_columns" in r:
            for col, info in r["drift_by_columns"].items():
                drift[col] = (info["drift_detected"],
                              info["drift_score"],
                              info["stattest_name"])
except Exception:
    pass

# ------------------------------------------------------------------- Commit
commit = os.environ.get("GITHUB_SHA")
if not commit:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "desconocido"
repo = os.environ.get("GITHUB_REPOSITORY")
if repo and commit != "desconocido":
    commit_html = (f'<a href="https://github.com/{repo}/commit/{commit}" '
                   f'target="_blank" rel="noopener">{commit[:7]}</a>')
else:
    commit_html = commit[:7]

generado = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


# ---------------------------------------------------------------- Histograma
def histograma_svg(v_ref, v_act):
    LO, HI, ANCHO = -30, 120, 5
    bordes = np.arange(LO, HI + ANCHO, ANCHO)
    eps = 0.01
    hr, _ = np.histogram(np.clip(v_ref, LO, HI - eps), bins=bordes)
    ha, _ = np.histogram(np.clip(v_act, LO, HI - eps), bins=bordes)
    hr = hr / len(v_ref)
    ha = ha / len(v_act)

    W, H = 520, 230
    ml, mr, mt, mb = 44, 10, 10, 34
    pw, ph = W - ml - mr, H - mt - mb
    ymax = max(hr.max(), ha.max()) * 1.1
    n = len(hr)
    bw = pw / n

    p = [f'<svg viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Histograma comparativo" class="hist">']
    for k in range(5):
        y = mt + ph * (1 - k / 4)
        p.append(f'<line x1="{ml}" x2="{W - mr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        p.append(f'<text x="{ml - 6}" y="{y + 4:.1f}" class="eje" text-anchor="end">'
                 f'{ymax * k / 4 * 100:.0f}%</text>')
    for i in range(n):
        x = ml + i * bw
        h1 = hr[i] / ymax * ph
        h2 = ha[i] / ymax * ph
        p.append(f'<rect x="{x + 1:.1f}" y="{mt + ph - h1:.1f}" '
                 f'width="{bw - 2:.1f}" height="{h1:.1f}" class="b-ref"/>')
        p.append(f'<rect x="{x + 1:.1f}" y="{mt + ph - h2:.1f}" '
                 f'width="{bw - 2:.1f}" height="{h2:.1f}" class="b-act"/>')
    for v in range(LO, HI + 1, 30):
        x = ml + (v - LO) / (HI - LO) * pw
        txt = "120+" if v == HI else ("≤ -30" if v == LO else str(v))
        p.append(f'<text x="{x:.1f}" y="{H - 14}" class="eje" text-anchor="middle">{txt}</text>')
    p.append(f'<text x="{ml + pw / 2:.1f}" y="{H - 1}" class="eje" '
             f'text-anchor="middle">minutos de demora</text>')
    p.append("</svg>")
    return "".join(p)


def tarjeta(col):
    vr, va = ref[col], act[col]
    med_r, med_a = vr.median(), va.median()
    dif = med_a - med_r
    signo = "+" if dif > 0 else ""
    if col in drift:
        detectado, score, test = drift[col]
        if detectado:
            badge = '<span class="badge mal">Drift detectado</span>'
        else:
            badge = '<span class="badge bien">Sin drift</span>'
        detalle = f"{escape(str(test))} · puntaje {score:.3f}"
    else:
        badge = '<span class="badge nd">n/d</span>'
        detalle = "Resultado no disponible"
    return f"""
    <article class="tarjeta">
      <div class="tarjeta-cab">
        <h3>{NOMBRES[col]}</h3>{badge}
      </div>
      <p class="detalle">{detalle}</p>
      {histograma_svg(vr.values, va.values)}
      <div class="leyenda">
        <span><i class="pt ref"></i>{mes_ref.capitalize()}</span>
        <span><i class="pt act"></i>{mes_act.capitalize()}</span>
      </div>
      <table class="mini">
        <tr><th></th><th>{mes_ref.capitalize()}</th><th>{mes_act.capitalize()}</th></tr>
        <tr><td>Mediana</td><td>{med_r:g}</td><td>{med_a:g} <small>({signo}{dif:g})</small></td></tr>
        <tr><td>Media</td><td>{vr.mean():.1f}</td><td>{va.mean():.1f}</td></tr>
        <tr><td>Percentil 90</td><td>{vr.quantile(.9):g}</td><td>{va.quantile(.9):g}</td></tr>
      </table>
    </article>"""


tarjetas = "".join(tarjeta(c) for c in COLS)
med_sal = act["demora_salida_min"].median()
med_lle = act["demora_llegada_min"].median()
drift_txt = f"{n_drift} de {n_cols}" if n_drift is not None else "n/d"
if n_drift is None:
    drift_nota = "Revisa el informe"
elif n_drift == 0:
    drift_nota = "variables con cambio"
else:
    drift_nota = "variables con cambio · revisar"

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitoreo de demoras · Vuelos NYC 2013</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#f4f6fb; --card:#fff; --tx:#16213a; --mut:#5d6b88; --line:#e3e8f2;
  --pri:#4f46e5; --pri2:#06b6d4; --ref:#94a3b8; --act:#4f46e5;
  --ok:#0f9d6b; --okbg:#e3f6ee; --bad:#d9372b; --badbg:#fde8e6;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:Inter,system-ui,-apple-system,"Segoe UI",Arial,sans-serif;
  background:var(--bg);color:var(--tx);line-height:1.6}
a{color:var(--pri)}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}

/* Hero */
.hero{background:linear-gradient(135deg,#1e1b4b 0%,#4f46e5 55%,#06b6d4 120%);
  color:#fff;padding:64px 0 110px;position:relative;overflow:hidden}
.hero::after{content:"";position:absolute;right:-120px;top:-120px;width:420px;height:420px;
  border-radius:50%;background:rgba(255,255,255,.08)}
.hero::before{content:"";position:absolute;left:-80px;bottom:-160px;width:360px;height:360px;
  border-radius:50%;background:rgba(255,255,255,.06)}
.chip{display:inline-block;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.3);
  padding:5px 14px;border-radius:99px;font-size:.82rem;font-weight:600;letter-spacing:.3px}
.hero h1{font-size:clamp(2rem,5vw,3.2rem);font-weight:800;line-height:1.15;margin:18px 0 12px}
.hero p{max-width:640px;font-size:1.08rem;opacity:.92}
.cta{display:inline-block;margin-top:26px;background:#fff;color:#312e81;text-decoration:none;
  font-weight:700;padding:13px 24px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.25);
  transition:transform .15s}
.cta:hover{transform:translateY(-2px)}
.cta small{display:block;font-weight:500;color:#5b5f97;font-size:.78rem}

/* KPIs */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;
  margin-top:-70px;position:relative;z-index:2}
.kpi{background:var(--card);border-radius:16px;padding:22px;border:1px solid var(--line);
  box-shadow:0 10px 30px rgba(30,27,75,.08)}
.kpi .et{font-size:.78rem;text-transform:uppercase;letter-spacing:.8px;color:var(--mut);font-weight:600}
.kpi .v{font-size:2.2rem;font-weight:800;margin:4px 0 0;line-height:1.15}
.kpi .n{font-size:.85rem;color:var(--mut)}
.kpi.dest .v{background:linear-gradient(90deg,var(--pri),var(--pri2));
  -webkit-background-clip:text;background-clip:text;color:transparent}

section{padding:56px 0 8px}
h2{font-size:1.6rem;font-weight:800;margin-bottom:6px}
.sub{color:var(--mut);margin-bottom:26px;max-width:720px}

/* Tarjetas de variable */
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:20px}
.tarjeta{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px;
  box-shadow:0 6px 20px rgba(30,27,75,.05)}
.tarjeta-cab{display:flex;justify-content:space-between;align-items:center;gap:10px}
.tarjeta h3{font-size:1.15rem}
.detalle{color:var(--mut);font-size:.85rem;margin-bottom:8px}
.badge{padding:4px 12px;border-radius:99px;font-size:.78rem;font-weight:700;white-space:nowrap}
.badge.bien{background:var(--okbg);color:var(--ok)}
.badge.mal{background:var(--badbg);color:var(--bad)}
.badge.nd{background:#eceff5;color:var(--mut)}
.hist{width:100%;height:auto;display:block}
.hist .grid{stroke:var(--line);stroke-width:1}
.hist .eje{fill:var(--mut);font-size:11px;font-family:inherit}
.hist .b-ref{fill:var(--ref);opacity:.75}
.hist .b-act{fill:var(--act);opacity:.6}
.leyenda{display:flex;gap:18px;font-size:.85rem;color:var(--mut);margin:6px 0 12px}
.pt{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.pt.ref{background:var(--ref)} .pt.act{background:var(--act)}
table.mini{width:100%;border-collapse:collapse;font-size:.92rem}
table.mini th,table.mini td{padding:7px 4px;border-top:1px solid var(--line);text-align:right}
table.mini th:first-child,table.mini td:first-child{text-align:left;color:var(--mut)}
table.mini th{font-size:.78rem;text-transform:uppercase;color:var(--mut);border-top:0}
table.mini small{color:var(--mut)}

/* Pasos */
.pasos{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;counter-reset:p}
.paso{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;
  position:relative;counter-increment:p}
.paso::before{content:counter(p);display:flex;align-items:center;justify-content:center;
  width:34px;height:34px;border-radius:50%;color:#fff;font-weight:800;margin-bottom:12px;
  background:linear-gradient(135deg,var(--pri),var(--pri2))}
.paso h4{margin-bottom:4px}
.paso p{font-size:.9rem;color:var(--mut)}

/* Dos tipos de problema */
.dos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}
.caja{border-radius:16px;padding:24px;border:1px solid var(--line);background:var(--card)}
.caja.rojo{border-top:5px solid var(--bad)} .caja.azul{border-top:5px solid var(--pri)}
.caja h3{margin-bottom:8px}
.caja ul{padding-left:18px;color:var(--mut);font-size:.93rem}

/* Meta + footer */
.meta{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:6px 24px}
.meta div{display:flex;justify-content:space-between;gap:16px;padding:12px 0;
  border-bottom:1px solid var(--line);font-size:.95rem}
.meta div:last-child{border-bottom:0}
.meta span:first-child{color:var(--mut)}
footer{margin-top:64px;background:#14122e;color:#c9cbe8;padding:36px 0;font-size:.9rem}
footer a{color:#9ad8ff}
footer .fila{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px}
@media(max-width:520px){.grid2{grid-template-columns:1fr}.tarjeta{padding:16px}}
</style>
</head>
<body>

<header class="hero">
  <div class="wrap">
    <span class="chip">Monitoreo automático · CI/CD + Evidently</span>
    <h1>¿Cambió el patrón de demoras de los vuelos de Nueva York?</h1>
    <p>Comparamos las demoras de <b>{{MES_ACT}}</b> con las de <b>{{MES_REF}}</b> de 2013
       en los aeropuertos JFK, LGA y EWR. El sitio se actualiza solo con cada lote válido.</p>
    <a class="cta" href="{{INFORME}}">Ver informe de Evidently
      <small>{{MES_ACT}} vs {{MES_REF}}</small></a>
  </div>
</header>

<main class="wrap">

  <div class="kpis">
    <div class="kpi dest"><div class="et">Último mes publicado</div>
      <div class="v">{{MES_ACT}}</div><div class="n">comparado con {{MES_REF}}</div></div>
    <div class="kpi"><div class="et">Registros analizados</div>
      <div class="v">{{N}}</div><div class="n">vuelos del lote actual</div></div>
    <div class="kpi"><div class="et">Mediana salida</div>
      <div class="v">{{MED_SAL}} min</div><div class="n">demora de salida</div></div>
    <div class="kpi"><div class="et">Mediana llegada</div>
      <div class="v">{{MED_LLE}} min</div><div class="n">demora de llegada</div></div>
    <div class="kpi"><div class="et">Drift (Evidently)</div>
      <div class="v">{{DRIFT}}</div><div class="n">{{DRIFT_NOTA}}</div></div>
  </div>

  <section id="distribuciones">
    <h2>Así se ven las distribuciones</h2>
    <p class="sub">Cada barra muestra qué porcentaje de vuelos cae en un rango de 5 minutos.
      Los valores extremos se agrupan en los bordes del gráfico. Un valor negativo significa
      que el vuelo salió o llegó antes de lo previsto.</p>
    <div class="grid2">{{TARJETAS}}</div>
  </section>

  <section id="flujo">
    <h2>Cómo se publica este sitio</h2>
    <p class="sub">Cada <code>push</code> a <code>main</code> activa el flujo de GitHub Actions.</p>
    <div class="pasos">
      <div class="paso"><h4>Push a main</h4><p>Se sube un cambio en los datos o en el código.</p></div>
      <div class="paso"><h4>Pruebas</h4><p>pytest verifica las reglas de validación con datos pequeños.</p></div>
      <div class="paso"><h4>Validación</h4><p>Se revisan completos referencia.csv y actual.csv.</p></div>
      <div class="paso"><h4>Informe</h4><p>Evidently compara las demoras y se genera este sitio.</p></div>
      <div class="paso"><h4>Despliegue</h4><p>Solo si todo pasó, GitHub Pages publica el artefacto.</p></div>
    </div>
  </section>

  <section id="diferencia">
    <h2>Dos tipos de problema, dos respuestas</h2>
    <p class="sub">No es lo mismo un dato mal escrito que un cambio real en el comportamiento.</p>
    <div class="dos">
      <div class="caja rojo"><h3>Fila inválida → se bloquea</h3>
        <ul><li>Distancia en cero, fecha imposible, identificador repetido o encabezado faltante.</li>
        <li>CI falla, CD se omite y Pages conserva el último sitio válido.</li>
        <li>Se corrige el dato y se vuelve a publicar.</li></ul></div>
      <div class="caja azul"><h3>Cambio de distribución → se revisa</h3>
        <ul><li>Los datos son válidos, pero las demoras se comportan distinto que en enero.</li>
        <li>Evidently lo marca como drift y el equipo investiga aeropuertos o rutas.</li>
        <li>No bloquea la publicación: es información para decidir.</li></ul></div>
    </div>
  </section>

  <section id="detalles">
    <h2>Detalles de esta publicación</h2>
    <p class="sub">Trazabilidad de la versión que estás viendo.</p>
    <div class="meta">
      <div><span>Meses comparados</span><span><b>{{MES_ACT}}</b> frente a <b>{{MES_REF}}</b> de 2013</span></div>
      <div><span>Informe completo</span><span><a href="{{INFORME}}">{{INFORME}}</a></span></div>
      <div><span>Fecha de generación</span><span>{{GENERADO}}</span></div>
      <div><span>Commit</span><span>{{COMMIT}}</span></div>
    </div>
  </section>
</main>

<footer>
  <div class="wrap fila">
    <div><b>Autor:</b> {{AUTOR}}<br>Universidad Privada del Valle · Unidad de Aprendizaje 5</div>
    <div><b>Fuente:</b> <a href="https://cran.r-project.org/package=nycflights13"
      target="_blank" rel="noopener">nycflights13</a><br>
      Vuelos 2013 desde JFK, LGA y EWR · muestra de 12.000 vuelos por mes</div>
  </div>
</footer>
</body>
</html>"""

valores = {
    "MES_ACT": mes_act.capitalize(), "MES_REF": mes_ref.capitalize(),
    "INFORME": nombre_informe, "N": f"{len(act):,}".replace(",", "."),
    "MED_SAL": f"{med_sal:g}", "MED_LLE": f"{med_lle:g}",
    "DRIFT": drift_txt, "DRIFT_NOTA": drift_nota, "TARJETAS": tarjetas,
    "GENERADO": generado, "COMMIT": commit_html, "AUTOR": AUTOR,
}
html = PLANTILLA
for k, v in valores.items():
    html = html.replace("{{" + k + "}}", v)

(SALIDA / "index.html").write_text(html, encoding="utf-8")
print("Sitio generado:", mes_act, "vs", mes_ref, "| commit", commit[:7])