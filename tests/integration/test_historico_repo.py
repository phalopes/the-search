from datetime import date, time

import pytest

from surfscout.adapters.storage.historico_repo import inserir_registro, listar_registros
from surfscout.domain.models import RegistroValidacao, TipoRegistro

pytestmark = pytest.mark.integration


def test_inserir_e_listar_registro(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "historico.db"
    registro = RegistroValidacao(
        data=date(2026, 9, 22),
        horario=time(7, 0),
        pico_id="matadeiro",
        tipo=TipoRegistro.SESSAO_REAL,
        nota=4,
        observacao="Vento sul bateu certinho",
        pico_recomendado="matadeiro",
        score_recomendado=90.2,
    )

    salvo = inserir_registro(db_path, registro)
    assert salvo.id is not None

    registros = listar_registros(db_path)
    assert len(registros) == 1
    assert registros[0].pico_id == "matadeiro"
    assert registros[0].nota == 4
    assert registros[0].horario == time(7, 0)


def test_listar_filtra_por_pico(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "historico.db"
    inserir_registro(db_path, RegistroValidacao(data=date(2026, 9, 10), pico_id="campeche", nota=3))
    inserir_registro(
        db_path, RegistroValidacao(data=date(2026, 9, 15), pico_id="matadeiro", nota=4)
    )

    registros = listar_registros(db_path, pico_id="matadeiro")

    assert len(registros) == 1
    assert registros[0].pico_id == "matadeiro"


def test_listar_em_banco_inexistente_retorna_vazio(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert listar_registros(tmp_path / "novo.db") == []
