from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date, timedelta


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    total_copies: int = 1
    _available: int = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.isbn.strip():
            raise ValueError("isbn 不能为空")
        if not self.title.strip():
            raise ValueError("title 不能为空")
        if not self.author.strip():
            raise ValueError("author 不能为空")
        if self.total_copies < 1:
            raise ValueError("total_copies 必须是正整数")
        self._available = self.total_copies

    @property
    def available(self) -> int:
        return self._available

    @property
    def is_available(self) -> bool:
        return self._available > 0

    def checkout(self) -> None:
        if not self.is_available:
            raise ValueError(f"《{self.title}》没有库存了")
        self._available -= 1

    def checkin(self) -> None:
        if self._available >= self.total_copies:
            raise ValueError(f"《{self.title}》的库存已满")
        self._available += 1

    @classmethod
    def from_row(cls, row: tuple[str, str, str, int]) -> Book:
        isbn, title, author, total_copies = row
        return cls(isbn, title, author, total_copies)

    @staticmethod
    def is_valid_isbn(isbn: str) -> bool:
        return len(isbn.replace("-", "")) in {10, 13}


@dataclass
class Member:
    member_id: str
    name: str
    max_loans: int = 3
    _loans: list[Loan] = field(
        default_factory=list,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not self.member_id.strip():
            raise ValueError("member_id 不能为空")
        if not self.name.strip():
            raise ValueError("name 不能为空")
        if self.max_loans < 1:
            raise ValueError("max_loans 必须是正整数")

    @property
    def active_loans(self) -> tuple[Loan, ...]:
        return tuple(loan for loan in self._loans if loan.is_active)

    @property
    def loan_count(self) -> int:
        return len(self.active_loans)

    @property
    def can_borrow(self) -> bool:
        return self.loan_count < self.max_loans

    def add_loan(self, loan: Loan) -> None:
        if not self.can_borrow:
            raise ValueError("借阅数量已达上限")
        self._loans.append(loan)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Member:
        return cls(
            str(data["member_id"]),
            str(data["name"]),
            int(data.get("max_loans", 3)),
        )


@dataclass
class Loan:
    book: Book
    member: Member
    borrowed_on: date
    due_on: date
    returned_on: date | None = None

    def __post_init__(self) -> None:
        if self.due_on < self.borrowed_on:
            raise ValueError("应还日期不能早于借阅日期")
        if self.returned_on is not None and self.returned_on < self.borrowed_on:
            raise ValueError("归还日期不能早于借阅日期")

    @classmethod
    def create(
        cls,
        book: Book,
        member: Member,
        today: date,
        days: int = 14,
    ) -> Loan:
        return cls(book, member, today, today + timedelta(days=days))

    @property
    def is_active(self) -> bool:
        return self.returned_on is None

    def is_overdue(self, today: date) -> bool:
        return self.is_active and today > self.due_on

    def days_left(self, today: date) -> int:
        return (self.due_on - today).days

    def close(self, returned_on: date) -> None:
        if not self.is_active:
            raise ValueError("这条借阅记录已经归还")
        if returned_on < self.borrowed_on:
            raise ValueError("归还日期不能早于借阅日期")
        self.returned_on = returned_on


def main() -> None:
    book = Book.from_row(("978-7-111-40701-0", "Python 编程", "张三", 2))
    member = Member.from_dict({"member_id": "M001", "name": "小明"})
    book.checkout()
    loan = Loan.create(book, member, date(2026, 10, 26))

    print(book)
    print(member)
    print(loan)
    print(f"Book 可用库存：{book.available}")

    member.add_loan(loan)
    print(f"Member 当前借阅：{member.loan_count}")
    print(f"Loan 是否逾期（2026-11-20）：{loan.is_overdue(date(2026, 11, 20))}")
    print("字段：", [item.name for item in fields(Book)])


if __name__ == "__main__":
    main()