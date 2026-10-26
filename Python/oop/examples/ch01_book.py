from __future__ import annotations


class Book:
    def __init__(self, isbn: str, title: str, author: str, year: int) -> None:
        self.isbn = isbn
        self.title = title
        self.author = author
        self.year = year

    def describe(self) -> str:
        return f"《{self.title}》 / {self.author} / {self.year}"

    def is_same_edition(self, other: Book) -> bool:
        return self.isbn == other.isbn


def main() -> None:
    book = Book("978-7-111-40701-0", "Python 编程", "张三", 2020)
    other = Book("978-7-111-40701-0", "Python 编程（第 2 版）", "张三", 2022)

    print(book.describe())
    print(book.is_same_edition(other))
    print(book.__dict__)
    print(isinstance(book, Book))


if __name__ == "__main__":
    main()