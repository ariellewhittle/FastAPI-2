from urllib.parse import quote

import requests
import typer

app = typer.Typer()
BASE_URL = "http://127.0.0.1:8000"


@app.callback()
def main():
    """Look up books through the FastAPI server."""


@app.command()
def get_book(isbn: str):
    """Fetch a book by ISBN."""
    try:
        response = requests.get(
            f"{BASE_URL}/book/{quote(isbn, safe='')}",
            timeout=20,
        )
    except requests.RequestException as error:
        typer.echo(f"Could not connect to the server: {error}", err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Status Code: {response.status_code}")
    try:
        typer.echo(typer.style("Response", bold=True))
        typer.echo(response.text)
    except BrokenPipeError:
        raise typer.Exit(code=1)

    if not response.ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()