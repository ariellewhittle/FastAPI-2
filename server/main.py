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
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue
    return value


@app.get("/book/{isbn}", response_model=Book)
def get_book(isbn: str):
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

