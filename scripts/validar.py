import re
import sys
from datetime import datetime

import pandas as pd

COLUMNAS = ["vuelo_id", "fecha", "origen", "destino",
            "demora_salida_min", "demora_llegada_min",
            "distancia_millas", "lote"]
ORIGENES = {"JFK", "LGA", "EWR"}
MES_LOTE = {"referencia": 1, "control": 2, "nuevo": 7}
ANIO = 2013
RE_ENTERO = re.compile(r"^-?\d+$")
RE_DESTINO = re.compile(r"^[A-Z]{3}$")


def validar_df(df, nombre, lotes_permitidos):
    """Devuelve una lista de errores (vacía si todo está bien)."""
    errores = []

    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes:
        return [f"{nombre}: faltan encabezados {faltantes}"]
    if len(df) == 0:
        return [f"{nombre}: el archivo no tiene filas"]

    ids_vistos = set()
    for i, fila in enumerate(df.to_dict("records"), start=2):  # fila 1 = encabezado
        def err(campo, msg):
            errores.append(f"{nombre}, fila {i}, campo '{campo}': {msg}")

        # vuelo_id
        v = fila["vuelo_id"]
        if not RE_ENTERO.match(v) or int(v) <= 0:
            err("vuelo_id", f"debe ser entero positivo (valor '{v}')")
        elif v in ids_vistos:
            err("vuelo_id", f"duplicado ({v})")
        else:
            ids_vistos.add(v)

        # lote
        lote = fila["lote"]
        if lote not in lotes_permitidos:
            err("lote", f"'{lote}' no permitido (esperado: {sorted(lotes_permitidos)})")

        # fecha
        try:
            f = datetime.strptime(fila["fecha"], "%Y-%m-%d")
            if lote in MES_LOTE and (f.year != ANIO or f.month != MES_LOTE[lote]):
                err("fecha", f"{fila['fecha']} no corresponde al lote '{lote}'")
        except ValueError:
            err("fecha", f"fecha inválida '{fila['fecha']}'")

        # origen / destino
        if fila["origen"] not in ORIGENES:
            err("origen", f"'{fila['origen']}' no es JFK, LGA ni EWR")
        if not RE_DESTINO.match(fila["destino"]):
            err("destino", f"'{fila['destino']}' debe tener 3 letras mayúsculas")

        # demoras (enteros, cero y negativos válidos)
        for campo in ("demora_salida_min", "demora_llegada_min"):
            if not RE_ENTERO.match(fila[campo]):
                err(campo, f"debe ser entero (valor '{fila[campo]}')")

        # distancia
        d = fila["distancia_millas"]
        if not RE_ENTERO.match(d) or int(d) <= 0:
            err("distancia_millas", f"debe ser entero positivo (valor '{d}')")

    return errores


def validar_archivo(ruta, lotes_permitidos):
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    return validar_df(df, ruta, lotes_permitidos)


def main():
    errores = []
    errores += validar_archivo("datos/referencia.csv", {"referencia"})
    errores += validar_archivo("datos/actual.csv", {"control", "nuevo"})

    if errores:
        print(f"VALIDACIÓN FALLIDA: {len(errores)} error(es)")
        for e in errores[:50]:
            print(" -", e)
        sys.exit(1)
    print("Validación OK: referencia.csv y actual.csv")


if __name__ == "__main__":
    main()