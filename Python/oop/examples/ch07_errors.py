from __future__ import annotations

from datetime import date
from typing import Protocol

from examples.ch06_models import Book, Loan, Member


class LibraryError(Exception):
    pass


class BookNotFound(LibraryError):
    pass


class MemberNotFound(LibraryError):
    pass


class DuplicateBook(LibraryError):
    pass


class DuplicateMember(LibraryError):
    pass


class BookNotAvailable(LibraryError):
    pass


class LoanLimitReached(LibraryError):
    pass


class InvalidReturn(LibraryError):
    pass


class Notifier(Protocol):
    def notify(self, message: str) -> None:
        ...


class ConsoleNotifier:
    def notify(self, message: str) -> None:
        print(f"[通知] {message}")


class MemoryNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def notify(self, message: str) -> None:
        self.messages.append(message)


class Library:
    def __init__(self, notifier: Notifier | None = None) -> None:
        self._books: dict[str, Book] = {}
        self._members: dict[str, Member] = {}
        self._loans: list[Loan] = []
        self._notifier = notifier

    def add_book(self, book: Book) -> None:
        if book.isbn in self._books:
            raise DuplicateBook(f"ISBN {book.isbn} 已存在")
        self._books[book.isbn] = book

    def register_member(self, member: Member) -> None:
        if member.member_id in self._members:
            raise DuplicateMember(f"会员 ID {member.member_id} 已存在")
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
            raise BookNotAvailable(f"《{book.title}》暂时无法借阅")
        if not member.can_borrow:
            raise LoanLimitReached(f"{member.name} 的借阅数量已达上限")

        book.checkout()
        loan = Loan.create(book, member, today)
        member.add_loan(loan)
        self._loans.append(loan)
        self._notify(f"{member.name} 借了《{book.title}》")
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

        loan = next(
            (item for item in member.active_loans if item.book is book),
            None,
        )
        if loan is None:
            raise InvalidReturn(f"{member.name} 没有借阅《{book.title}》")

        loan.close(today)
        book.checkin()
        self._notify(f"{member.name} 归还了《{book.title}》")
        return loan

    def _require_book(self, isbn: str) -> Book:
        try:
            return self._books[isbn]
        except KeyError:
            raise BookNotFound(f"找不到 ISBN 为 {isbn} 的图书") from None

    def _require_member(self, member_id: str) -> Member:
        try:
            return self._members[member_id]
        except KeyError:
            raise MemberNotFound(f"找不到 ID 为 {member_id} 的会员") from None

    def _notify(self, message: str) -> None:
        if self._notifier is not None:
            self._notifier.notify(message)


def main() -> None:
    notifier = MemoryNotifier()
    library = Library(notifier)
    today = date(2026, 10, 26)

    book = Book("978-7-111-40701-0", "Python 编程", "张三", total_copies=1)
    member = Member("M001", "小明")
    library.add_book(book)
    library.register_member(member)

    loan = library.borrow(book.isbn, member.member_id, today)
    print(f"借阅成功：《{loan.book.title}》，应还 {loan.due_on}")

    try:
        library.borrow(book.isbn, member.member_id, today)
    except BookNotAvailable as exc:
        print(f"借阅失败：{type(exc).__name__}: {exc}")

    library.return_book(book.isbn, member.member_id, today)
    print(f"归还成功：{member.name} 归还了《{book.title}》")

    try:
        library.return_book(book.isbn, member.member_id, today)
    except InvalidReturn as exc:
        print(f"重复归还：{type(exc).__name__}: {exc}")

    print(f"通知记录：{notifier.messages}")


if __name__ == "__main__":
    main()