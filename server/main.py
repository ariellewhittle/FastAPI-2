import re
from datetime import datetime

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Book(BaseModel):
    title: str
    author: str
    publish_date: str
    isbn: str


def parse_date(value: str) -> str:
    for date_format in ("%Y-%m-%d", "%Y-%m", "%Y", "%B %d, %Y", "%B %Y"):
        try:
            parsed = datetime.strptime(value, date_format)
        except ValueError:
            continue

        if not 1800 <= parsed.year <= datetime.now().year:
            raise HTTPException(
                status_code=400,
                detail="Publication year is outside the allowed range",
            )
        return parsed.date().isoformat()

    return value


def fetch_book(isbn: str) -> Book:
    if not re.fullmatch(r"(?:[0-9]{10}|[0-9]{13})", isbn):
        raise HTTPException(
            status_code=400,
            detail="Invalid ISBN format (must be 10 or 13 digits)",
        )

    book_key = f"ISBN:{isbn}"
    try:
        response = requests.get(
            "https://openlibrary.org/api/books",
            params={"bibkeys": book_key, "format": "json", "jscmd": "data"},
            timeout=15,
        )
        response.raise_for_status()
        book = response.json().get(book_key)
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502, detail="Could not retrieve data from Open Library"
        ) from error

    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    authors = book.get("authors") or []
    return Book(
        title=book.get("title") or "Unknown",
        author=authors[0].get("name", "Unknown") if authors else "Unknown",
        publish_date=parse_date(book.get("publish_date") or "Unknown"),
        isbn=isbn,
    )

book_cache: dict[str, Book] = {}


@app.get("/book/{isbn}")
def get_book(isbn: str):
    if isbn in book_cache:
        return {"cached": True, "data": book_cache[isbn]}

    book = fetch_book(isbn)
    book_cache[isbn] = book
    return {"cached": False, "data": book}


@app.get("/books/search")
def search_books(title: str):
    try:
        response = requests.get(
            "https://openlibrary.org/search.json",
            params={
                "title": title,
                "limit": 5,
                "fields": "title,author_name,first_publish_year,isbn",
            },
            timeout=15,
        )
        response.raise_for_status()
        results = response.json().get("docs", [])
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502, detail="Could not search Open Library"
        ) from error

    return [
        {
            "title": result.get("title", "Unknown"),
            "author": (result.get("author_name") or ["Unknown"])[0],
            "publish_date": str(result.get("first_publish_year") or "Unknown"),
            "isbn": (result.get("isbn") or [None])[0],
        }
        for result in results[:5]
    ]


@app.post("/books/bulk")
def get_bulk(isbns: list[str]):
    results = []
    for isbn in isbns:
        try:
            results.append(get_book(isbn)["data"])
        except HTTPException as error:
            results.append(
                {"isbn": isbn, "status": error.status_code, "detail": error.detail}
            )
    return results
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

