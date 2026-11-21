import json
from typing import Optional
from urllib.parse import quote

import requests
import typer

app = typer.Typer()
BASE_URL = "http://127.0.0.1:8000"


def send_request(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, BASE_URL + path, timeout=60, **kwargs)
    except requests.RequestException as error:
        typer.echo(f"Could not connect to the server: {error}", err=True)
        raise typer.Exit(1) from error

    typer.echo(f"Status Code: {response.status_code}")
    try:
        data = response.json()
    except ValueError:
        typer.echo(response.text, err=True)
        raise typer.Exit(1)

    if not response.ok:
        typer.echo(json.dumps(data, indent=2), err=True)
        raise typer.Exit(1)
    return data


@app.command()
def get_book(isbn: str, min_year: Optional[int] = typer.Option(None, "--min-year")):
    result = send_request("GET", f"/book/{quote(isbn, safe='')}")
    if min_year is not None:
        year_text = result["data"]["publish_date"][:4]
        if not year_text.isdigit():
            typer.echo("Filtered out because the publication year is unknown.")
            return
        if int(year_text) < min_year:
            typer.echo(f"Filtered out because {year_text} is earlier than {min_year}.")
            return
    typer.echo(json.dumps(result, indent=2))


@app.command()
def search_title(title: str):
    result = send_request("GET", "/books/search", params={"title": title})
    typer.echo(json.dumps(result, indent=2))


@app.command()
def get_bulk(isbns: list[str]):
    result = send_request("POST", "/books/bulk", json=isbns)
    typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()