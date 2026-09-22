import datetime as dt
from pathlib import Path

import typer

from surfscout.adapters.storage.historico_repo import inserir_registro, listar_registros
from surfscout.adapters.storage.spots_repo import load_spots
from surfscout.adapters.weather.open_meteo import fetch_readings
from surfscout.domain.models import NivelUsuario, RegistroValidacao, TipoRegistro
from surfscout.domain.scoring import score_spot

app = typer.Typer(add_completion=False)

DEFAULT_SPOTS_PATH = Path(__file__).resolve().parent.parent / "spots.yaml"
DEFAULT_DB_PATH = Path("data") / "historico.db"


def _amanha_as_7h() -> dt.datetime:
    amanha = dt.date.today() + dt.timedelta(days=1)
    return dt.datetime.combine(amanha, dt.time(7, 0))


@app.command()
def recommend(
    nivel: NivelUsuario = typer.Option(NivelUsuario.INTERMEDIARIO, help="Seu nível de surf"),
    when: str = typer.Option(
        "", help="Data/hora alvo ISO (ex. 2026-09-10T07:00). Padrão: amanhã 07:00"
    ),
    spots_path: Path = typer.Option(DEFAULT_SPOTS_PATH, help="Caminho do spots.yaml"),
) -> None:
    """Recomenda os melhores picos para a janela de tempo escolhida."""
    alvo = dt.datetime.fromisoformat(when) if when else _amanha_as_7h()
    spots = load_spots(spots_path)

    resultados = []
    for spot in spots:
        swell, vento, mare = fetch_readings(spot.coordenadas, alvo)
        resultados.append(score_spot(spot, swell, vento, mare, nivel))

    resultados.sort(key=lambda r: r.score_total, reverse=True)

    typer.echo(f"Recomendação para {alvo.isoformat()} (nível: {nivel.value})\n")
    for posicao, resultado in enumerate(resultados, start=1):
        typer.echo(f"{posicao}. {resultado.spot_nome} — {resultado.score_total}/100")
        for fator in resultado.fatores:
            typer.echo(f"   - {fator.nome} ({fator.peso * 100:.0f}%): {fator.explicacao}")
        typer.echo("")


@app.command()
def log(
    data: str = typer.Option(..., help="Data da sessão/julgamento, ISO (ex. 2026-09-22)"),
    pico: str = typer.Option(..., help="Id do pico (ex. matadeiro, campeche) — ver spots.yaml"),
    nota: float | None = typer.Option(
        None, min=1, max=5, help="Nota de 1 a 5, aceita casa decimal (opcional)"
    ),
    obs: str = typer.Option("", help="Observação livre sobre a sessão"),
    tipo: TipoRegistro = typer.Option(
        TipoRegistro.SESSAO_REAL, help="sessao_real ou julgamento_pre_sessao"
    ),
    horario: str | None = typer.Option(None, help="Horário HH:MM (opcional)"),
    pico_recomendado: str | None = typer.Option(
        None, help="Id do pico que o sistema recomendou em 1º (opcional, pra comparar)"
    ),
    score_recomendado: float | None = typer.Option(
        None, help="Score do 1º colocado do sistema (opcional)"
    ),
    score_pico: float | None = typer.Option(
        None, help="Score que o sistema deu pro pico escolhido, se diferente do 1º (opcional)"
    ),
    spots_path: Path = typer.Option(DEFAULT_SPOTS_PATH, help="Caminho do spots.yaml"),
    db_path: Path = typer.Option(DEFAULT_DB_PATH, help="Caminho do banco de histórico"),
) -> None:
    """Registra uma sessão real ou julgamento pré-sessão no histórico local."""
    ids_validos = {spot.id for spot in load_spots(spots_path)}
    if pico not in ids_validos:
        typer.echo(f"Pico '{pico}' não encontrado em {spots_path}. Válidos: {sorted(ids_validos)}")
        raise typer.Exit(code=1)
    if pico_recomendado is not None and pico_recomendado not in ids_validos:
        typer.echo(f"pico_recomendado '{pico_recomendado}' não encontrado em {spots_path}.")
        raise typer.Exit(code=1)

    registro = RegistroValidacao(
        data=dt.date.fromisoformat(data),
        horario=dt.time.fromisoformat(horario) if horario else None,
        pico_id=pico,
        tipo=tipo,
        nota=nota,
        observacao=obs,
        pico_recomendado=pico_recomendado,
        score_recomendado=score_recomendado,
        score_pico_escolhido=score_pico,
    )
    salvo = inserir_registro(db_path, registro)
    typer.echo(f"Registro #{salvo.id} salvo em {db_path}: {salvo.data} — {salvo.pico_id}")


@app.command()
def historico(
    pico: str | None = typer.Option(None, help="Filtra por id de pico (opcional)"),
    db_path: Path = typer.Option(DEFAULT_DB_PATH, help="Caminho do banco de histórico"),
) -> None:
    """Lista os registros salvos no histórico local."""
    registros = listar_registros(db_path, pico_id=pico)
    if not registros:
        typer.echo("Nenhum registro encontrado.")
        return

    for registro in registros:
        linha = f"#{registro.id} {registro.data} {registro.pico_id} (tipo: {registro.tipo.value})"
        if registro.nota is not None:
            linha += f" — nota {registro.nota:g}/5"
        if registro.pico_recomendado is not None:
            linha += f" — sistema recomendou {registro.pico_recomendado}"
            if registro.score_recomendado is not None:
                linha += f" ({registro.score_recomendado})"
        typer.echo(linha)
        if registro.observacao:
            typer.echo(f"   {registro.observacao}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
