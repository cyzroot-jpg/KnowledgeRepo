# 第 08 章：综合实战——图书借阅系统

> 本章目标：把前面所有概念组装成一个完整、可运行、可测试的小项目。

---

## 8.1 需求

实现一个命令行可演示的图书借阅系统，支持：

1. 添加图书，同一 ISBN 不能重复添加
2. 注册会员，同一会员 ID 不能重复注册
3. 借书：
   - 图书必须存在
   - 会员必须存在
   - 有可用库存
   - 会员未达到借阅上限
4. 还书：
   - 必须是该会员借的、尚未归还的书
5. 查询：
   - 按书名 / 作者 / ISBN 搜索
   - 查看当前借阅
   - 查看逾期记录
6. 同一本书可以有多本库存
7. 所有失败都有明确的异常类型

我们不做数据库，也不做 Web 界面。重点是**对象设计**，不是外围设施。

---

## 8.2 领域模型

```text
Library  1 ─── * Book
   │
   ├── * Member  1 ─── * Loan  * ─── 1 Book
   │
   └── * Loan
```

| 对象 | 职责 | 不应该知道什么 |
| :--- | :--- | :--- |
| `Book` | 自己的库存、借出 / 归还 / 补货 | 会员、图书馆、借阅记录 |
| `Member` | 自己的借阅额度、借阅记录 | 图书馆有哪些书 |
| `Loan` | 一条借阅的期限和状态 | 图书馆的库存 |
| `Library` | 协调借书、还书、查询 | 具体怎么减库存、怎么算逾期 |
| `Notifier` | 发送通知 | 借阅业务规则 |

这就是「职责分离」：每个对象只做自己最了解的事。

---

## 8.3 项目结构

```text
project/
├── library_system/
│   ├── __init__.py      # 对外导出
│   ├── errors.py        # 异常层级
│   ├── models.py        # Book / Member / Loan
│   └── library.py       # Library / Notifier
├── demo.py              # 可运行演示
└── test_library.py      # 单元测试
```

为什么拆成三个模块？

- `errors.py`：不依赖任何业务代码，谁都可以导入，避免循环依赖
- `models.py`：只依赖 `errors.py`，可以单独测试
- `library.py`：依赖 `models.py` 和 `errors.py`，负责协调
- `__init__.py`：只做导出，让外部 `from library_system import Library` 更短

依赖方向是单向的：

```text
errors.py  ←  models.py  ←  library.py  ←  __init__.py
```

**不要出现 `models.py` 反过来导入 `library.py`。** 那通常说明职责放错了。

---

## 8.4 `errors.py`：先定义失败

完整代码：[`project/library_system/errors.py`](../project/library_system/errors.py)

```python
class LibraryError(Exception):
    pass


class ValidationError(LibraryError):
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
```

为什么不直接用 `ValueError`？

- 调用方可以精确捕获业务失败
- 错误类型本身就是文档
- 以后要给某类异常加字段（比如 `isbn`）时，有地方可加
- 测试可以断言异常类型，而不是匹配字符串

注意所有异常都继承 `LibraryError`，而 `LibraryError` 继承 `Exception`。这样既能统一捕获，又不会误吞系统级异常。

---

## 8.5 `models.py`：三个领域对象

完整代码：[`project/library_system/models.py`](../project/library_system/models.py)

### `Book`

```python
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
```

不变量：

```text
total_copies >= 1
0 <= available <= total_copies
```

维护不变量的方法：

```python
def checkout(self) -> None:
    if not self.is_available:
        raise BookNotAvailable(f"《{self.title}》暂时无法借阅")
    self._available -= 1

def checkin(self) -> None:
    if self._available >= self.total_copies:
        raise ValidationError(f"《{self.title}》的库存已满，无法归还")
    self._available += 1
```

注意 `available` 是只读 property，外部不能直接写。想改库存，只能走 `checkout` / `checkin` / `add_copies`。

### `Member`

```python
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
```

借阅记录用 `_loans` 保存，外部只能读到元组：

```python
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
```

为什么不直接公开 `_loans` 列表？

- 外部可以随意 `append` 一条不属于自己的记录
- 外部可以 `clear()` 抹掉借阅历史
- 返回元组后，调用方可以遍历，但不能改结构

### `Loan`

```python
@dataclass
class Loan:
    book: Book
    member: Member
    borrowed_on: date
    due_on: date
    returned_on: date | None = None
```

`Loan.create` 负责计算应还日期：

```python
@classmethod
def create(cls, book: Book, member: Member, today: date, days: int = 14) -> Loan:
    if not isinstance(days, int) or days < 1:
        raise ValidationError("借阅天数必须是正整数")
    return cls(book, member, today, today + timedelta(days=days))
```

`close` 负责归还，并校验日期：

```python
def close(self, returned_on: date) -> None:
    if not self.is_active:
        raise ValidationError("这条借阅记录已经归还")
    if returned_on < self.borrowed_on:
        raise ValidationError("归还日期不能早于借阅日期")
    self.returned_on = returned_on
```

注意 `returned_on` 是可变的，因为借阅记录会从「借出」变成「已归还」。这是实体对象，不是不可变值对象。

---

## 8.6 `library.py`：协调者

完整代码：[`project/library_system/library.py`](../project/library_system/library.py)

### 构造与依赖注入

```python
class Library:
    def __init__(self, notifier: Notifier | None = None) -> None:
        self._books: dict[str, Book] = {}
        self._members: dict[str, Member] = {}
        self._loans: list[Loan] = []
        self._notifier = notifier
```

`Notifier` 是一个 `Protocol`：

```python
class Notifier(Protocol):
    def notify(self, message: str) -> None:
        ...
```

`Library` 不关心通知是打印、发邮件还是写数据库，只要求「有个 `notify` 方法」。

### 借书流程

```python
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
```

按顺序看：

```text
1. 确定“今天”
2. 找书、找会员（找不到抛 BookNotFound / MemberNotFound）
3. 检查会员额度（超了抛 LoanLimitReached）
4. 让书减库存（没库存抛 BookNotAvailable）
5. 创建借阅记录
6. 把记录挂到会员和图书馆
7. 发通知
8. 返回记录
```

为什么先检查会员额度，再减库存？

因为减库存是有副作用的操作。如果先减库存，再发现会员超限，就必须回滚，逻辑更复杂。**先做所有能提前做的检查，再执行修改。**

### 还书流程

```python
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
```

关键点：

- 从**该会员**的当前借阅里找，不会把别人借的书还给当前会员
- 用 `item.book is book` 判断同一对象
- 先 `loan.close()`，成功后再 `book.checkin()`，避免半更新

### 查询

```python
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
```

注意 `overdue_loans` 没有自己计算日期，而是让每条 `Loan` 自己判断。**规则跟着数据走。**

### 魔术方法

```python
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
```

于是可以自然地说：

```python
len(library)
for book in library:
    ...
"978-7-111-40701-0" in library
print(library)
```

---

## 8.7 运行项目

进入项目目录：

```bash
cd Python/oop/project
python demo.py
```

如果 `python` 命令不可用，但你装了 `uv`，可以：

```bash
uv run python demo.py
```

输出：

```text
[通知] 小明 借了《Python 编程》
借阅成功：《Python 编程》，应还 2026-11-09
[通知] 小明 借了《算法导论》
借阅失败：小明 的借阅数量已达上限
[通知] 小明 归还了《Python 编程》
《Python 编程》剩余库存：2
[通知] 小红 借了《Python 编程》
《Python 编程》剩余库存：1
馆藏 3 种，当前借阅 2 条
搜索 python： ['Python 编程']
逾期记录：
- 小明 / 《算法导论》 / 应还 2026-11-09
- 小红 / 《Python 编程》 / 应还 2026-11-09
```

对照需求检查：

- 小明最多借 2 本，第三本失败
- 归还后库存恢复
- 小红借走了另一本，库存从 2 变 1
- 搜索忽略大小写
- 2026-11-20 时，两本未还的书都逾期

---

## 8.8 运行测试

```bash
python -m unittest -v
```

输出：

```text
test_borrow_decreases_available ... ok
test_cannot_borrow_when_no_copies ... ok
test_duplicate_book ... ok
test_invalid_book ... ok
test_loan_limit ... ok
test_member_not_found ... ok
test_overdue ... ok
test_return_restores_available ... ok
test_return_without_loan ... ok
test_search ... ok

----------------------------------------------------------------------
Ran 10 tests in 0.001s

OK
```

测试覆盖了：

| 测试 | 验证的行为 |
| :--- | :--- |
| `test_borrow_decreases_available` | 借书后库存减一、会员借阅数加一 |
| `test_return_restores_available` | 还书后库存恢复、记录关闭 |
| `test_cannot_borrow_when_no_copies` | 库存为 0 时抛 `BookNotAvailable` |
| `test_loan_limit` | 达到上限时抛 `LoanLimitReached` |
| `test_overdue` | 到期日当天不逾期，次日逾期，归还后不再逾期 |
| `test_duplicate_book` | 重复 ISBN 抛 `DuplicateBook` |
| `test_invalid_book` | 非法库存抛 `ValidationError` |
| `test_return_without_loan` | 没借过就还不能成功 |
| `test_member_not_found` | 会员不存在抛 `MemberNotFound` |
| `test_search` | 按书名、作者搜索，忽略大小写 |

这些测试都在 `setUp` 里创造独立数据，互不影响。测试里传入固定的 `today`，所以结果不会随真实日期变化。

---

## 8.9 为什么这样设计

### 1. 为什么 `Book` 不直接调用 `Library`

因为书不需要知道图书馆。让底层对象依赖上层对象，会导致：

- 无法单独测试 `Book`
- 循环依赖
- 职责膨胀

### 2. 为什么 `Library` 不自己改 `_available`

因为它不应该知道库存字段叫什么、怎么减。它只调用 `book.checkout()`，把规则留在 `Book` 内部。

### 3. 为什么 `Loan` 持有对象而不是 ID

```python
loan.book.title
loan.member.name
```

比：

```python
book = library.find_book(loan.isbn)
member = library.find_member(loan.member_id)
```

更直接，也减少了「查不到」的分支。代价是对象之间引用更紧密，但在内存中的小系统里完全可接受。

### 4. 为什么用 dataclass

`Book`、`Member`、`Loan` 都是「数据 + 少量行为」的模型。`dataclass` 自动生成 `__init__`、`__repr__`、`__eq__`，让代码聚焦在业务规则上。

### 5. 为什么异常分这么细

因为调用方可能对不同失败做不同处理：

- 没库存 → 提示换一本
- 达到上限 → 提示先还书
- 会员不存在 → 引导注册

如果所有失败都抛 `ValueError`，调用方只能匹配字符串，非常脆弱。

### 6. 为什么用 Protocol

通知方式未来可能变，测试也需要替换。`Protocol` 让 `Library` 依赖「会 notify 的东西」，而不是某个具体类。

---

## 8.10 动手扩展

按难度从低到高：

### 扩展 A：续借

给 `Loan` 增加：

```python
def renew(self, days: int) -> None:
    ...
```

规则：

- 只有未归还的记录能续借
- `days` 必须是正整数
- 最多续借一次（需要增加 `_renewed: bool` 字段）

然后给 `Library` 增加 `renew(isbn, member_id, days)`。

### 扩展 B：会员类型

新增 `StudentMember`、`TeacherMember`，不同会员借期不同：

- 学生 14 天
- 教师 30 天

思考：借期应该放在 `Member`、`Loan` 还是 `Library`？如果不想用继承，能不能用组合一个 `LoanPolicy` 对象？

### 扩展 C：持久化

把图书、会员、借阅记录保存到 JSON：

```text
data/
├── books.json
├── members.json
└── loans.json
```

要求：

- 启动时加载
- 修改后保存
- 用 `from_dict` / `to_dict` 做序列化
- 不要破坏领域对象的不变量

### 扩展 D：命令行

用 `argparse` 实现：

```bash
python -m library_system.cli add-book --isbn ... --title ...
python -m library_system.cli borrow --isbn ... --member ...
python -m library_system.cli list
```

把「解析命令行」和「业务逻辑」分开，`cli.py` 只负责输入输出，不直接改库存。

---

## 8.11 设计自查清单

写完一个类，问自己：

- [ ] 这个类的职责能用一句话说清吗？
- [ ] 它需要知道这么多别的对象吗？
- [ ] 有没有外部代码直接改它的内部字段？
- [ ] 非法状态能不能通过公开方法制造出来？
- [ ] 失败时抛出的异常是否足够具体？
- [ ] 新增一种类型 / 一种通知方式，需要改多少地方？
- [ ] 能不能不启动整个系统，单独测试这个类？

如果有一项答不上来，通常还有重构空间。

---

## 8.12 本章练习

### 练习 A：补测试

为下面三种情况补测试：

1. 书不存在时借书，抛 `BookNotFound`
2. 重复注册会员，抛 `DuplicateMember`
3. 会员还一本别人借的书，抛 `InvalidReturn`

### 练习 B：加「借阅历史」

`Member._loans` 里已经保存了所有借阅记录，但 `active_loans` 只返回未归还的。增加：

```python
@property
def loan_history(self) -> tuple[Loan, ...]:
    ...
```

并给 `Library` 增加 `member_history(member_id)`。

### 练习 C：重构

把 `Library.borrow` 中的「检查 + 修改」拆成两个私有方法：

```python
def _ensure_can_borrow(self, member: Member) -> None:
    ...

def _create_loan(self, book: Book, member: Member, today: date) -> Loan:
    ...
```

思考：拆完之后真的更清楚了吗？如果只是把代码搬来搬去，没有降低复杂度，就不要拆。

---

## 8.13 检查点

1. 四个领域对象各自的职责是什么？
2. 借书流程为什么先检查会员额度，再减库存？
3. 还书时为什么先 `loan.close()` 再 `book.checkin()`？
4. 项目的依赖方向是什么？为什么不能反过来？
5. `Library` 为什么依赖 `Notifier` 协议，而不是具体通知类？
6. 如果新增「教师会员借期 30 天」，你会改哪些文件？

如果第 1、2、4、6 题能说清，你已经完成了一次完整的面向对象设计。

---

[← 上一章：异常与协议](./07_errors_protocols.md) | [下一章：测试与进阶 →](./09_testing_next.md)