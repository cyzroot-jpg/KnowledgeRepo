from __future__ import annotations

from datetime import date, timedelta


class Book:
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        total_copies: int = 1,
    ) -> None:
        if total_copies < 1:
            raise ValueError("total_copies 必须是正整数")
        self.isbn = isbn
        self.title = title
        self.author = author
        self._total_copies = total_copies
        self._available = total_copies

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
        if self._available >= self._total_copies:
            raise ValueError(f"《{self.title}》的库存已满")
        self._available += 1


class Member:
    def __init__(self, member_id: str, name: str, max_loans: int = 3) -> None:
        if max_loans < 1:
            raise ValueError("max_loans 必须是正整数")
        self.member_id = member_id
        self.name = name
        self.max_loans = max_loans
        self._loans: list[Loan] = []

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


class Loan:
    def __init__(
        self,
        book: Book,
        member: Member,
        borrowed_on: date,
        due_on: date,
    ) -> None:
        self.book = book
        self.member = member
        self.borrowed_on = borrowed_on
        self.due_on = due_on
        self.returned_on: date | None = None

    @property
    def is_active(self) -> bool:
        return self.returned_on is None

    def close(self, returned_on: date) -> None:
        if not self.is_active:
            raise ValueError("这条借阅记录已经归还")
        if returned_on < self.borrowed_on:
            raise ValueError("归还日期不能早于借阅日期")
        self.returned_on = returned_on

    def is_overdue(self, today: date) -> bool:
        return self.is_active and today > self.due_on


class Library:
    def __init__(self) -> None:
        self._books: dict[str, Book] = {}
        self._members: dict[str, Member] = {}
        self._loans: list[Loan] = []

    def add_book(self, book: Book) -> None:
        if book.isbn in self._books:
            raise ValueError(f"ISBN {book.isbn} 已存在")
        self._books[book.isbn] = book

    def register_member(self, member: Member) -> None:
        if member.member_id in self._members:
            raise ValueError(f"会员 ID {member.member_id} 已存在")
        self._members[member.member_id] = member

    def borrow(
        self,
        isbn: str,
        member_id: str,
        today: date | None = None,
    ) -> Loan:
        today = today or date.today()
        book = self._require_book(isbn)
        member = self._require_member(member_id)

        if not book.is_available:
            raise ValueError(f"《{book.title}》暂时无法借阅")
        if not member.can_borrow:
            raise ValueError(f"{member.name} 的借阅数量已达上限")

        book.checkout()
        loan = Loan(book, member, today, today + timedelta(days=14))
        member.add_loan(loan)
        self._loans.append(loan)
        return loan

    def return_book(
        self,
        isbn: str,
        member_id: str,
        today: date | None = None,
    ) -> Loan:
        today = today or date.today()
        book = self._require_book(isbn)
        member = self._require_member(member_id)

        for loan in member.active_loans:
            if loan.book is book:
                loan.close(today)
                book.checkin()
                return loan

        raise ValueError(f"{member.name} 没有借阅《{book.title}》")

    def search(self, keyword: str) -> list[Book]:
        keyword = keyword.casefold()
        return [
            book
            for book in self._books.values()
            if keyword in book.title.casefold()
            or keyword in book.author.casefold()
            or keyword in book.isbn.casefold()
        ]

    def overdue_loans(self, today: date | None = None) -> list[Loan]:
        today = today or date.today()
        return [loan for loan in self._loans if loan.is_overdue(today)]

    def _require_book(self, isbn: str) -> Book:
        try:
            return self._books[isbn]
        except KeyError:
            raise ValueError(f"找不到 ISBN 为 {isbn} 的图书") from None

    def _require_member(self, member_id: str) -> Member:
        try:
            return self._members[member_id]
        except KeyError:
            raise ValueError(f"找不到 ID 为 {member_id} 的会员") from None


def main() -> None:
    library = Library()
    today = date(2026, 10, 26)

    python_book = Book("978-7-111-40701-0", "Python 编程", "张三", total_copies=2)
    algo_book = Book("978-7-115-54608-7", "算法导论", "李四")
    library.add_book(python_book)
    library.add_book(algo_book)

    alice = Member("M001", "小明")
    library.register_member(alice)

    loan = library.borrow(python_book.isbn, alice.member_id, today)
    print(f"{alice.name} 借了《{loan.book.title}》，应还 {loan.due_on}")
    print(f"《{python_book.title}》剩余库存：{python_book.available}")

    library.borrow(algo_book.isbn, alice.member_id, today)
    print(f"{alice.name} 当前借阅：{alice.loan_count} 本")

    library.return_book(python_book.isbn, alice.member_id, today)
    print(f"归还《{python_book.title}》后剩余库存：{python_book.available}")

    print("2026-12-01 的逾期记录：")
    for item in library.overdue_loans(date(2026, 12, 1)):
        print(f"- {item.member.name} / 《{item.book.title}》 / 应还 {item.due_on}")

    print("搜索 python：", [book.title for book in library.search("python")])


if __name__ == "__main__":
    main()