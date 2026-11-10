import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validar import validar_df  # noqa: E402

PERMITIDOS = {"control", "nuevo"}


def fila(**cambios):
    base = {"vuelo_id": "1", "fecha": "2013-02-10", "origen": "JFK",
            "destino": "LAX", "demora_salida_min": "5",
            "demora_llegada_min": "-3", "distancia_millas": "2475",
            "lote": "control"}
    base.update(cambios)
    return base


def df(*filas):
    return pd.DataFrame(list(filas), dtype=str)


def test_registro_valido():
    assert validar_df(df(fila()), "t.csv", PERMITIDOS) == []


def test_demora_negativa_valida():
    d = df(fila(demora_salida_min="-15", demora_llegada_min="0"))
    assert validar_df(d, "t.csv", PERMITIDOS) == []


def test_encabezado_faltante():
    d = df(fila()).drop(columns=["distancia_millas"])
    errores = validar_df(d, "t.csv", PERMITIDOS)
    assert len(errores) == 1 and "distancia_millas" in errores[0]


def test_fecha_invalida():
    errores = validar_df(df(fila(fecha="2013-02-30")), "t.csv", PERMITIDOS)
    assert any("fecha" in e for e in errores)


def test_fecha_de_otro_mes():
    errores = validar_df(df(fila(fecha="2013-03-10")), "t.csv", PERMITIDOS)
    assert any("no corresponde" in e for e in errores)


def test_identificador_duplicado():
    d = df(fila(vuelo_id="7"), fila(vuelo_id="7"))
    errores = validar_df(d, "t.csv", PERMITIDOS)
    assert any("duplicado" in e for e in errores)


def test_distancia_invalida():
    errores = validar_df(df(fila(distancia_millas="0")), "t.csv", PERMITIDOS)
    assert any("distancia_millas" in e for e in errores)


def test_lote_no_permitido():
    errores = validar_df(df(fila(lote="referencia", fecha="2013-01-10")),
                         "t.csv", PERMITIDOS)
    assert any("lote" in e for e in errores)