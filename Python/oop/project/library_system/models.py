from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .errors import BookNotAvailable, ValidationError


def _require_text(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} 不能为空")


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    total_copies: int = 1
    _available: int = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_text(self.isbn, "isbn")
        _require_text(self.title, "title")
        _require_text(self.author, "author")
        if not isinstance(self.total_copies, int) or self.total_copies < 1:
            raise ValidationError("total_copies 必须是正整数")
        self._available = self.total_copies

    @property
    def available(self) -> int:
        return self._available

    @property
    def is_available(self) -> bool:
        return self._available > 0

    def checkout(self) -> None:
        if not self.is_available:
            raise BookNotAvailable(f"《{self.title}》暂时无法借阅")
        self._available -= 1

    def checkin(self) -> None:
        if self._available >= self.total_copies:
            raise ValidationError(f"《{self.title}》的库存已满，无法归还")
        self._available += 1

    def add_copies(self, count: int) -> None:
        if not isinstance(count, int) or count < 1:
            raise ValidationError("count 必须是正整数")
        self.total_copies += count
        self._available += count


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
        _require_text(self.member_id, "member_id")
        _require_text(self.name, "name")
        if not isinstance(self.max_loans, int) or self.max_loans < 1:
            raise ValidationError("max_loans 必须是正整数")

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
        if loan.member is not self:
            raise ValidationError("借阅记录的会员与当前会员不一致")
        if not self.can_borrow:
            raise ValidationError("借阅数量已达上限")
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
            raise ValidationError("应还日期不能早于借阅日期")
        if self.returned_on is not None and self.returned_on < self.borrowed_on:
            raise ValidationError("归还日期不能早于借阅日期")

    @classmethod
    def create(
        cls,
        book: Book,
        member: Member,
        today: date,
        days: int = 14,
    ) -> Loan:
        if not isinstance(days, int) or days < 1:
            raise ValidationError("借阅天数必须是正整数")
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
            raise ValidationError("这条借阅记录已经归还")
        if returned_on < self.borrowed_on:
            raise ValidationError("归还日期不能早于借阅日期")
        self.returned_on = returned_on