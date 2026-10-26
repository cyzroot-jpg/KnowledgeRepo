import unittest
from datetime import date, timedelta

from library_system import (
    Book,
    BookNotAvailable,
    DuplicateBook,
    InvalidReturn,
    Library,
    LoanLimitReached,
    Member,
    MemberNotFound,
    ValidationError,
)


class LibraryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.library = Library()
        self.today = date(2026, 1, 1)
        self.book = Book("978-7-111-40701-0", "Python 编程", "张三", total_copies=2)
        self.member = Member("M001", "小明")
        self.library.add_book(self.book)
        self.library.register_member(self.member)

    def test_borrow_decreases_available(self) -> None:
        loan = self.library.borrow(self.book.isbn, self.member.member_id, self.today)

        self.assertEqual(self.book.available, 1)
        self.assertTrue(loan.is_active)
        self.assertEqual(self.member.loan_count, 1)
        self.assertEqual(len(self.library.active_loans()), 1)

    def test_return_restores_available(self) -> None:
        self.library.borrow(self.book.isbn, self.member.member_id, self.today)
        loan = self.library.return_book(
            self.book.isbn,
            self.member.member_id,
            self.today,
        )

        self.assertEqual(self.book.available, 2)
        self.assertFalse(loan.is_active)
        self.assertEqual(self.member.loan_count, 0)

    def test_cannot_borrow_when_no_copies(self) -> None:
        self.library.borrow(self.book.isbn, self.member.member_id, self.today)
        self.library.borrow(self.book.isbn, self.member.member_id, self.today)

        with self.assertRaises(BookNotAvailable):
            self.library.borrow(self.book.isbn, self.member.member_id, self.today)

    def test_loan_limit(self) -> None:
        limited = Member("M002", "小红", max_loans=1)
        other_book = Book("978-7-115-54608-7", "算法导论", "李四")
        self.library.register_member(limited)
        self.library.add_book(other_book)

        self.library.borrow(self.book.isbn, limited.member_id, self.today)

        with self.assertRaises(LoanLimitReached):
            self.library.borrow(other_book.isbn, limited.member_id, self.today)

    def test_overdue(self) -> None:
        loan = self.library.borrow(self.book.isbn, self.member.member_id, self.today)

        self.assertFalse(loan.is_overdue(self.today + timedelta(days=14)))
        self.assertTrue(loan.is_overdue(self.today + timedelta(days=15)))

        self.library.return_book(
            self.book.isbn,
            self.member.member_id,
            self.today + timedelta(days=16),
        )
        self.assertFalse(loan.is_overdue(self.today + timedelta(days=20)))

    def test_duplicate_book(self) -> None:
        with self.assertRaises(DuplicateBook):
            self.library.add_book(
                Book("978-7-111-40701-0", "另一本 Python", "张三")
            )

    def test_invalid_book(self) -> None:
        with self.assertRaises(ValidationError):
            Book("978-7-111-40701-0", "Python 编程", "张三", total_copies=0)

    def test_return_without_loan(self) -> None:
        with self.assertRaises(InvalidReturn):
            self.library.return_book(
                self.book.isbn,
                self.member.member_id,
                self.today,
            )

    def test_member_not_found(self) -> None:
        with self.assertRaises(MemberNotFound):
            self.library.borrow(self.book.isbn, "M999", self.today)

    def test_search(self) -> None:
        self.assertEqual(
            [book.title for book in self.library.search("python")],
            ["Python 编程"],
        )
        self.assertEqual(
            [book.title for book in self.library.search("张三")],
            ["Python 编程"],
        )
        self.assertEqual(self.library.search("不存在"), [])


if __name__ == "__main__":
    unittest.main()