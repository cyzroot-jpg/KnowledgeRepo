from __future__ import annotations


class Book:
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        total_copies: int = 1,
    ) -> None:
        if not isinstance(total_copies, int) or total_copies < 1:
            raise ValueError("total_copies 必须是正整数")

        self.isbn = isbn
        self.title = title
        self.author = author
        self._total_copies = total_copies
        self._available = total_copies

    @property
    def total_copies(self) -> int:
        return self._total_copies

    @property
    def available(self) -> int:
        return self._available

    @property
    def is_available(self) -> bool:
        return self._available > 0

    def checkout(self) -> None:
        if self._available <= 0:
            raise ValueError(f"《{self.title}》没有库存了")
        self._available -= 1

    def checkin(self) -> None:
        if self._available >= self._total_copies:
            raise ValueError(f"《{self.title}》的库存已满，无法归还")
        self._available += 1

    def describe(self) -> str:
        return (
            f"《{self.title}》 / {self.author} / "
            f"库存 {self._available}/{self._total_copies}"
        )


def main() -> None:
    book = Book("978-7-111-40701-0", "Python 编程", "张三", total_copies=1)
    print(f"初始库存：{book.available}")

    book.checkout()
    print(f"借出一本后：{book.available}")

    try:
        book.checkout()
    except ValueError as exc:
        print(f"再借：{exc}")

    book.checkin()
    print(f"归还后：{book.available}")

    try:
        book.available = 5
    except AttributeError as exc:
        print(f"直接改 available：{exc}")


if __name__ == "__main__":
    main()