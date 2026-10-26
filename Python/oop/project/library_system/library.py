from __future__ import annotations

from datetime import date
from typing import Iterator, Protocol

from .errors import (
    BookNotFound,
    DuplicateBook,
    DuplicateMember,
    InvalidReturn,
    LoanLimitReached,
    MemberNotFound,
)
from .models import Book, Loan, Member


class Notifier(Protocol):
    def notify(self, message: str) -> None:
        ...


class ConsoleNotifier:
    def notify(self, message: str) -> None:
        print(f"[通知] {message}")


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

    def search(self, keyword: str) -> list[Book]:
        keyword = keyword.strip().casefold()
        if not keyword:
            return []
        return [
            book
            for book in self._books.values()
            if keyword in book.title.casefold()
            or keyword in book.author.casefold()
            or keyword in book.isbn.casefold()
        ]

    def active_loans(self) -> list[Loan]:
        return [loan for loan in self._loans if loan.is_active]

    def overdue_loans(self, today: date | None = None) -> list[Loan]:
        today = today or date.today()
        return [loan for loan in self._loans if loan.is_overdue(today)]

    def member_loans(self, member_id: str) -> list[Loan]:
        member = self._require_member(member_id)
        return list(member.active_loans)

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

    def __len__(self) -> int:
        return len(self._books)

    def __iter__(self) -> Iterator[Book]:
        return iter(self._books.values())

    def __contains__(self, isbn: object) -> bool:
        return isinstance(isbn, str) and isbn in self._books

    def __repr__(self) -> str:
        return (
            f"Library(books={len(self._books)}, "
            f"members={len(self._members)}, "
            f"loans={len(self._loans)})"
        )