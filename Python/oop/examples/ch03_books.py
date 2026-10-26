from __future__ import annotations

from abc import ABC, abstractmethod


class Book(ABC):
    def __init__(self, isbn: str, title: str, author: str) -> None:
        self.isbn = isbn
        self.title = title
        self.author = author

    @property
    @abstractmethod
    def loan_days(self) -> int:
        ...

    def describe(self) -> str:
        return f"《{self.title}》 / {self.author}"

    def loan_policy(self) -> str:
        return f"{self.describe()}，可借 {self.loan_days} 天"


class PaperBook(Book):
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        pages: int,
    ) -> None:
        super().__init__(isbn, title, author)
        self.pages = pages

    @property
    def loan_days(self) -> int:
        return 14

    def describe(self) -> str:
        return f"{super().describe()}（纸质书，{self.pages} 页）"


class EBook(Book):
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        file_size_mb: float,
    ) -> None:
        super().__init__(isbn, title, author)
        self.file_size_mb = file_size_mb

    @property
    def loan_days(self) -> int:
        return 7

    def describe(self) -> str:
        return f"{super().describe()}（电子书，{self.file_size_mb} MB）"


class ReferenceBook(Book):
    @property
    def loan_days(self) -> int:
        return 3

    def describe(self) -> str:
        return f"{super().describe()}（工具书，仅供馆内查阅）"


def main() -> None:
    books: list[Book] = [
        PaperBook("978-7-111-40701-0", "Python 编程", "张三", 520),
        EBook("978-7-115-54608-7", "流畅的 Python", "李四", 8.5),
        ReferenceBook("978-7-5326-0000-0", "辞海", "王五"),
    ]

    for book in books:
        print(book.loan_policy())

    try:
        Book("000", "抽象书", "无名")
    except TypeError:
        print("Book 是抽象类，不能直接实例化")

    print("paper 是 Book 的实例吗？", isinstance(books[0], Book))


if __name__ == "__main__":
    main()