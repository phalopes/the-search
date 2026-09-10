import datetime as dt
from pathlib import Path

import typer

from surfscout.adapters.storage.spots_repo import load_spots
from surfscout.adapters.weather.open_meteo import fetch_readings
from surfscout.domain.models import NivelUsuario
from surfscout.domain.scoring import score_spot

app = typer.Typer(add_completion=False)

DEFAULT_SPOTS_PATH = Path(__file__).resolve().parent.parent / "spots.yaml"


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
