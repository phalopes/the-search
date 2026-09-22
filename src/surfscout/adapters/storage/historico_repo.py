import sqlite3
from contextlib import closing
from datetime import date, datetime, time
from pathlib import Path

from surfscout.domain.models import RegistroValidacao, TipoRegistro

_SCHEMA = """
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    horario TEXT,
    pico_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    nota REAL,
    observacao TEXT NOT NULL DEFAULT '',
    pico_recomendado TEXT,
    score_recomendado REAL,
    score_pico_escolhido REAL,
    criado_em TEXT NOT NULL
)
"""


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(path)
    conexao.execute(_SCHEMA)
    return conexao


def _para_registro(linha: sqlite3.Row) -> RegistroValidacao:
    return RegistroValidacao(
        id=linha["id"],
        data=date.fromisoformat(linha["data"]),
        horario=time.fromisoformat(linha["horario"]) if linha["horario"] else None,
        pico_id=linha["pico_id"],
        tipo=TipoRegistro(linha["tipo"]),
        nota=linha["nota"],
        observacao=linha["observacao"],
        pico_recomendado=linha["pico_recomendado"],
        score_recomendado=linha["score_recomendado"],
        score_pico_escolhido=linha["score_pico_escolhido"],
        criado_em=datetime.fromisoformat(linha["criado_em"]),
    )


def inserir_registro(path: Path, registro: RegistroValidacao) -> RegistroValidacao:
    with closing(_connect(path)) as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO registros (
                data, horario, pico_id, tipo, nota, observacao,
                pico_recomendado, score_recomendado, score_pico_escolhido, criado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                registro.data.isoformat(),
                registro.horario.isoformat() if registro.horario else None,
                registro.pico_id,
                registro.tipo.value,
                registro.nota,
                registro.observacao,
                registro.pico_recomendado,
                registro.score_recomendado,
                registro.score_pico_escolhido,
                registro.criado_em.isoformat(),
            ),
        )
        conexao.commit()
        return registro.model_copy(update={"id": cursor.lastrowid})


def listar_registros(path: Path, pico_id: str | None = None) -> list[RegistroValidacao]:
    with closing(_connect(path)) as conexao:
        conexao.row_factory = sqlite3.Row
        if pico_id is not None:
            cursor = conexao.execute(
                "SELECT * FROM registros WHERE pico_id = ? ORDER BY data, horario", (pico_id,)
            )
        else:
            cursor = conexao.execute("SELECT * FROM registros ORDER BY data, horario")
        return [_para_registro(linha) for linha in cursor.fetchall()]
