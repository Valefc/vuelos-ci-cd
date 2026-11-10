# Monitoreo de demoras de vuelos NYC 2013 (CI/CD + Evidently)

## Instalación
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

## Ejecución local
python scripts/preparar_lotes.py      # genera los lotes desde datos/original
python scripts/validar.py             # valida referencia.csv y actual.csv
pytest -q                             # pruebas automatizadas
python scripts/generar_informes.py    # genera sitio/index.html y el informe

## Datos
referencia.csv = enero (fijo) · control.csv = febrero · nuevo.csv = julio
actual.csv es una copia de control.csv o nuevo.csv.