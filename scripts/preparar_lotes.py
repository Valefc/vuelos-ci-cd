import pandas as pd

ORIGINAL = "datos/original/vuelos_nyc_2013.csv"
LOTES = {"referencia": "referencia", "control": "control", "nuevo": "nuevo"}
COLUMNAS = ["vuelo_id", "fecha", "origen", "destino",
            "demora_salida_min", "demora_llegada_min",
            "distancia_millas", "lote"]

df = pd.read_csv(ORIGINAL, dtype=str, keep_default_na=False)
assert list(df.columns) == COLUMNAS, f"Encabezados distintos: {list(df.columns)}"

for lote, archivo in LOTES.items():
    sub = df[df["lote"] == lote]
    assert len(sub) == 12000, f"{lote}: {len(sub)} filas"
    sub.to_csv(f"datos/{archivo}.csv", index=False, sep=",")
    print(f"datos/{archivo}.csv -> {len(sub)} filas")