# 第 07 章：异常与协议——划清失败边界和依赖边界

> 本章目标：用自定义异常表达业务失败，用 `Protocol` 定义「只要会做什么就能替换」的接口。

---

## 7.1 先运行

```bash
python -m examples.ch07_errors
```

输出：

```text
借阅成功：《Python 编程》，应还 2026-11-09
借阅失败：BookNotAvailable: 《Python 编程》暂时无法借阅
归还成功：小明 归还了《Python 编程》
重复归还：InvalidReturn: 小明 没有借阅《Python 编程》
通知记录：['小明 借了《Python 编程》', '小明 归还了《Python 编程》']
```

完整代码在 [`examples/ch07_errors.py`](../examples/ch07_errors.py)。

---

## 7.2 为什么不用 `None` 表示失败

假设借书失败时返回 `None`：

```python
def borrow(self, isbn: str, member_id: str) -> Loan | None:
    if not self.find_book(isbn):
        return None
    if not self.find_member(member_id):
        return None
    if not book.is_available:
        return None
    ...
```

调用方只能这样：

```python
loan = library.borrow(isbn, member_id)
if loan is None:
    print("失败了")   # 为什么失败？不知道
```

`None` 丢失了失败原因：

- 书不存在？
- 会员不存在？
- 没有库存？
- 达到借阅上限？

而且调用方很容易忘记检查，继续用 `loan.book`，结果在很远的地方抛 `AttributeError`。

异常的好处是：

1. 失败原因明确
2. 不检查就继续执行会立刻报错，而不是带着 `None` 往下跑
3. 可以把「正常流程」和「失败处理」分开

---

## 7.3 自定义异常层级

```python
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
```

继承关系：

```text
Exception
└── LibraryError
    ├── BookNotFound
    ├── MemberNotFound
    ├── DuplicateBook
    ├── DuplicateMember
    ├── BookNotAvailable
    ├── LoanLimitReached
    └── InvalidReturn
```

这样设计的好处：

```python
try:
    library.borrow(isbn, member_id)
except BookNotAvailable:
    print("换一本或等归还")
except LoanLimitReached:
    print("先还几本")
except LibraryError as exc:
    print(f"其它业务错误：{exc}")
```

- 能精确处理的，捕获具体异常
- 不想逐一处理的，捕获基类 `LibraryError`
- 系统级错误（`MemoryError`、`KeyboardInterrupt`）不会被误吞

### 异常类放在哪里

建议单独放一个 `errors.py`，避免业务模块互相导入造成循环依赖。第 08 章的项目就是这么做的。

### 异常要不要带数据

可以：

```python
class BookNotAvailable(LibraryError):
    def __init__(self, isbn: str, message: str) -> None:
        super().__init__(message)
        self.isbn = isbn
```

这样调用方除了看消息，还能拿到结构化信息：

```python
except BookNotAvailable as exc:
    print(exc.isbn)
```

本章为了简洁，只传消息字符串。真实项目里可以按需增加字段。

---

## 7.4 `raise`、`from` 和异常链

### 主动抛出

```python
def _require_book(self, isbn: str) -> Book:
    try:
        return self._books[isbn]
    except KeyError:
        raise BookNotFound(f"找不到 ISBN 为 {isbn} 的图书") from None
```

`from None` 表示隐藏原始 `KeyError` 的上下文。否则报错会显示：

```text
KeyError: '...'
The above exception was the direct cause of the following exception:
BookNotFound: ...
```

对使用者来说，`KeyError` 是实现细节，没必要暴露。

### 保留异常链

如果你想把底层异常保留下来：

```python
try:
    data = read_config()
except OSError as exc:
    raise ConfigError("读取配置失败") from exc
```

这样既表达了「配置错误」，又保留了「文件打不开」的根因。排查问题时非常有用。

### 原则

- **能处理就处理，不能处理就往上抛**
- 不要捕获异常后什么都不做
- 不要捕获 `Exception` 然后 `pass`
- 转换异常时，想清楚要不要保留原因

---

## 7.5 `try / except / else / finally`

```python
try:
    loan = library.borrow(isbn, member_id, today)
except BookNotAvailable:
    print("没有库存")
except LoanLimitReached:
    print("借阅上限")
else:
    print(f"借阅成功：{loan.book.title}")
finally:
    print("本次借阅流程结束")
```

执行顺序：

- `try` 成功 → 执行 `else`
- `try` 抛异常 → 匹配 `except`，不执行 `else`
- 无论成功失败 → 执行 `finally`

`else` 的价值是：**只在没有异常时执行**，避免把成功后的代码也放进 `try` 被误捕获。

`finally` 适合清理资源（关闭文件、释放锁）。如果只是普通打印，不需要 `finally`。

---

## 7.6 异常使用中的常见反模式

### 反模式 1：吞掉异常

```python
try:
    library.borrow(isbn, member_id)
except Exception:
    pass
```

出了问题完全没痕迹。至少记录日志或重新抛出。

### 反模式 2：用异常做普通分支

```python
try:
    value = items[index]
except IndexError:
    value = None
```

如果索引越界是正常情况，先用 `if index < len(items)` 判断更清楚。异常适合「意外 / 违反约定」的情况。

### 反模式 3：捕获过宽

```python
try:
    result = calculate()
except Exception:
    return 0
```

这会连 `KeyboardInterrupt`（在 Python 3 中 `KeyboardInterrupt` 不是 `Exception` 子类，但很多错误是）和真正的 bug 一起吞掉。捕获你具体知道怎么处理的异常。

### 反模式 4：异常信息没有上下文

```python
raise ValueError("错误")
```

调用方看不出是哪本书、哪个会员、哪个操作。消息里带上关键标识：

```python
raise BookNotFound(f"找不到 ISBN 为 {isbn} 的图书")
```

---

## 7.7 用 `Protocol` 定义可替换依赖

假设借书成功后要发通知。通知方式可能是：

- 控制台打印
- 发邮件
- 发短信
- 写入消息队列
- 测试时记录到列表

如果 `Library` 直接依赖某个具体的 `EmailService`：

```python
class Library:
    def __init__(self) -> None:
        self.email_service = EmailService()
```

测试时就必须真的发邮件，或者去改 `Library` 的源码。

### 定义协议

```python
from typing import Protocol


class Notifier(Protocol):
    def notify(self, message: str) -> None:
        ...
```

它只表达一件事：

> 任何对象，只要有 `notify(self, message: str) -> None` 方法，就可以当作通知器。

### 实现

```python
class ConsoleNotifier:
    def notify(self, message: str) -> None:
        print(f"[通知] {message}")


class MemoryNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def notify(self, message: str) -> None:
        self.messages.append(message)
```

`ConsoleNotifier` 和 `MemoryNotifier` **都没有继承 `Notifier`**，但它们满足协议。这就是结构化类型（structural typing）：

> 不看你是谁，只看你会不会做这件事。

### 注入

```python
class Library:
    def __init__(self, notifier: Notifier | None = None) -> None:
        self._notifier = notifier

    def _notify(self, message: str) -> None:
        if self._notifier is not None:
            self._notifier.notify(message)
```

使用：

```python
notifier = MemoryNotifier()
library = Library(notifier)
```

测试时传 `MemoryNotifier`，生产时传 `ConsoleNotifier` 或 `EmailNotifier`，`Library` 完全不用改。

### `Protocol` vs `ABC`

| | `ABC` | `Protocol` |
| :--- | :--- | :--- |
| 子类是否必须继承 | 是 | 否 |
| 检查方式 | 名义类型（nominal） | 结构类型（structural） |
| 运行时是否强制 | 实例化时检查抽象方法 | 默认不检查 |
| 适合 | 明确的类层级 | 可替换的依赖、第三方类适配 |

选择建议：

- 你自己的类家族，用 `ABC` 表达「必须实现什么」
- 依赖注入、测试替身、适配第三方类，用 `Protocol`
- 不要为了「更高级」滥用 Protocol；它主要服务于类型检查和可读性

### 运行时检查

默认情况下，`isinstance(obj, Notifier)` 会报错。如果确实需要：

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class Notifier(Protocol):
    def notify(self, message: str) -> None:
        ...
```

然后：

```python
isinstance(ConsoleNotifier(), Notifier)   # True
```

注意：`runtime_checkable` 只检查方法是否存在，不检查签名。不要用它做复杂的运行时类型分发。

---

## 7.8 本章代码的关键部分

### 构造函数注入

```python
class Library:
    def __init__(self, notifier: Notifier | None = None) -> None:
        self._books: dict[str, Book] = {}
        self._members: dict[str, Member] = {}
        self._loans: list[Loan] = []
        self._notifier = notifier
```

`notifier` 是可选依赖。不传就静默工作，传了就发通知。

### 借书失败的不同异常

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
```

每个失败原因对应一个异常类型，调用方可以精确处理。

### 重复归还

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

注意：先检查记录，再调用 `loan.close()` 和 `book.checkin()`。失败时不会产生半更新状态。

---

## 7.9 动手改

在 `examples/ch07_errors.py` 中：

1. 确保 `register_member` 在会员 ID 重复时抛出 `DuplicateMember`。示例代码已经包含这个异常，试着自己从零写一遍，并补一段 `try/except` 验证。
2. 增加 `Library.overdue_loans(today)`，返回逾期记录。
3. 增加 `EmailNotifier`，实现 `notify`，打印 `[邮件] ...`，并在 `main` 里替换 `MemoryNotifier` 验证 `Library` 不需要改。

参考实现：

```python
class DuplicateMember(LibraryError):
    pass

def register_member(self, member: Member) -> None:
    if member.member_id in self._members:
        raise DuplicateMember(f"会员 ID {member.member_id} 已存在")
    self._members[member.member_id] = member

def overdue_loans(self, today: date | None = None) -> list[Loan]:
    today = today or date.today()
    return [loan for loan in self._loans if loan.is_overdue(today)]

class EmailNotifier:
    def notify(self, message: str) -> None:
        print(f"[邮件] {message}")
```

---

## 7.10 常见坑

### 坑 1：自定义异常没有继承 `Exception`

```python
class MyError:   # 不是异常类
    pass

raise MyError()  # TypeError
```

必须继承 `Exception` 或其子类。

### 坑 2：异常层级过深

```text
Exception -> LibraryError -> BookError -> BookStateError -> BookNotAvailable -> ...
```

调用方很难记住该捕哪个。通常一层基类 + 几个具体子类就够了。

### 坑 3：用 `except Exception` 包住所有代码

这会让真正的 bug 被隐藏。只捕获你明确知道如何处理的异常。

### 坑 4：Protocol 只是静态约定

```python
library = Library(notifier=object())
```

运行时不报错，直到调用 `notify` 才 `AttributeError`。Protocol 不会自动做运行时校验，除非加 `runtime_checkable` 并显式检查。

### 坑 5：`NotImplemented` 和 `NotImplementedError` 混用

- `NotImplemented`：比较方法的返回值，表示「我无法处理这个比较」
- `NotImplementedError`：抽象方法未实现时抛出的异常

它们不是一回事。

---

## 7.11 本章练习

### 练习 A：给异常加字段

把 `BookNotAvailable` 改成携带 `isbn` 和 `available`：

```python
class BookNotAvailable(LibraryError):
    def __init__(self, isbn: str, available: int) -> None:
        super().__init__(f"ISBN {isbn} 当前可用库存为 {available}")
        self.isbn = isbn
        self.available = available
```

更新 `Library.borrow`，在 `main` 中捕获并打印 `exc.isbn`。

### 练习 B：`SmsNotifier`

实现 `SmsNotifier`，满足 `Notifier` 协议，把消息追加到 `sent` 列表。用它替换 `MemoryNotifier`，确认 `Library` 不需要改。

### 练习 C：设计异常层级

为下面这些失败设计异常：

- 图书不存在
- 会员不存在
- 书已全部借出
- 会员达到上限
- 归还一本没借过的书
- 重复添加同一本书

画出继承关系，并说明哪些应该继承 `LibraryError`。本章的代码可以作为起点，但请自己先想一遍。

---

## 7.12 检查点

1. 为什么用异常而不是返回 `None` 表示失败？
2. 自定义异常为什么要有一个共同基类？
3. `raise ... from exc` 和 `from None` 有什么区别？
4. `ABC` 和 `Protocol` 的核心区别是什么？
5. 为什么 `Library` 依赖 `Notifier` 协议，而不是直接 new 一个 `EmailNotifier`？
6. 什么是异常链？排查问题时它有什么用？

如果第 2、4、5 题能说清，你已经能为系统设计清晰的边界了。

---

[← 上一章：类方法与 dataclass](./06_classmethod_dataclass.md) | [下一章：综合实战 →](./08_project.md)