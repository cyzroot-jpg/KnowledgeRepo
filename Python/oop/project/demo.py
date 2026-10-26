from datetime import date

from library_system import Book, ConsoleNotifier, Library, LoanLimitReached, Member


def main() -> None:
    library = Library(ConsoleNotifier())
    today = date(2026, 10, 26)

    python_book = Book(
        "978-7-111-40701-0",
        "Python 编程",
        "张三",
        total_copies=2,
    )
    algo_book = Book("978-7-115-54608-7", "算法导论", "李四")
    clean_code = Book("978-7-121-33814-8", "代码整洁之道", "王五")

    for book in (python_book, algo_book, clean_code):
        library.add_book(book)

    alice = Member("M001", "小明", max_loans=2)
    bob = Member("M002", "小红")
    library.register_member(alice)
    library.register_member(bob)

    loan = library.borrow(python_book.isbn, alice.member_id, today)
    print(f"借阅成功：《{loan.book.title}》，应还 {loan.due_on}")

    library.borrow(algo_book.isbn, alice.member_id, today)

    try:
        library.borrow(clean_code.isbn, alice.member_id, today)
    except LoanLimitReached as exc:
        print(f"借阅失败：{exc}")

    library.return_book(python_book.isbn, alice.member_id, today)
    print(f"《Python 编程》剩余库存：{python_book.available}")

    library.borrow(python_book.isbn, bob.member_id, today)
    print(f"《Python 编程》剩余库存：{python_book.available}")

    print(f"馆藏 {len(library)} 种，当前借阅 {len(library.active_loans())} 条")
    print("搜索 python：", [book.title for book in library.search("python")])

    print("逾期记录：")
    for item in library.overdue_loans(date(2026, 11, 20)):
        print(f"- {item.member.name} / 《{item.book.title}》 / 应还 {item.due_on}")


if __name__ == "__main__":
    main()