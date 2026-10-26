from __future__ import annotations

from time import perf_counter
from typing import Iterator


class Book:
    def __init__(self, isbn: str, title: str) -> None:
        self.isbn = isbn
        self.title = title

    def __str__(self) -> str:
        return f"《{self.title}》"

    def __repr__(self) -> str:
        return f"Book(isbn={self.isbn!r}, title={self.title!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Book):
            return NotImplemented
        return self.isbn == other.isbn

    def __hash__(self) -> int:
        return hash(self.isbn)


class Library:
    def __init__(self) -> None:
        self._books: dict[str, Book] = {}

    def add(self, book: Book) -> None:
        self._books[book.isbn] = book

    def __len__(self) -> int:
        return len(self._books)

    def __iter__(self) -> Iterator[Book]:
        return iter(self._books.values())

    def __contains__(self, isbn: object) -> bool:
        return isinstance(isbn, str) and isbn in self._books

    def __repr__(self) -> str:
        return f"Library(books={len(self)})"


class Timer:
    def __init__(self, label: str) -> None:
        self.label = label
        self._start = 0.0

    def __enter__(self) -> Timer:
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        elapsed = perf_counter() - self._start
        print(f"{self.label}: {elapsed:.3f}s")


def main() -> None:
    b1 = Book("978-7-111-40701-0", "Python 编程")
    b2 = Book("978-7-111-40701-0", "Python 编程（第 2 版）")
    b3 = Book("978-7-115-54608-7", "算法导论")

    print(b1)
    print(repr(b1))
    print(b1 == b2)
    print(len({b1, b2, b3}))

    library = Library()
    library.add(b1)
    library.add(b3)
    print(library)
    print(len(library))
    print("978-7-111-40701-0" in library)
    for book in library:
        print(book)

    with Timer("求和"):
        total = sum(range(1_000_001))
    print(total)


if __name__ == "__main__":
    main()