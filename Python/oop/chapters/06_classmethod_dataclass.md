# 第 06 章：类属性、类方法与 dataclass

> 本章目标：用 `@classmethod` 造对象，用 `@staticmethod` 放工具函数，用 `@dataclass` 消除重复样板代码。

---

## 6.1 先运行

```bash
python -m examples.ch06_models
```

输出：

```text
Book(isbn='978-7-111-40701-0', title='Python 编程', author='张三', total_copies=2)
Member(member_id='M001', name='小明', max_loans=3)
Loan(book=Book(...), member=Member(...), borrowed_on=datetime.date(2026, 10, 26), due_on=datetime.date(2026, 11, 9), returned_on=None)
Book 可用库存：1
Member 当前借阅：1
Loan 是否逾期（2026-11-20）：True
字段： ['isbn', 'title', 'author', 'total_copies', '_available']
```

> `Loan` 的 `repr` 会嵌套显示完整的 `Book` 和 `Member`，上面为了可读性做了省略。

完整代码在 [`examples/ch06_models.py`](../examples/ch06_models.py)。

---

## 6.2 类属性和实例属性

先看两种写法：

```python
class Book:
    category = "图书"          # 类属性

    def __init__(self, title: str) -> None:
        self.title = title     # 实例属性
```

- `category` 属于类，所有实例共享
- `title` 属于每个实例，各自独立

```python
b1 = Book("Python 编程")
b2 = Book("算法导论")

print(b1.category)   # 图书
print(b2.category)   # 图书
print(Book.category) # 图书
```

### 读类属性：实例会向上查找

```python
print(b1.category)
```

实例上找不到 `category`，就去类上找。

### 写类属性：会在实例上新建

```python
b1.category = "计算机"
print(b1.category)    # 计算机
print(b2.category)    # 图书
print(Book.category)  # 图书
```

`b1.category = ...` 并没有修改类属性，而是给 `b1` 新建了一个同名实例属性。这个区别很重要。

如果想改类属性：

```python
Book.category = "计算机"
print(b2.category)    # 计算机
```

### 可变类属性的经典陷阱

```python
class Library:
    books = []   # 所有实例共享同一个列表

    def add(self, book: str) -> None:
        self.books.append(book)
```

```python
a = Library()
b = Library()
a.add("Python")
print(b.books)   # ['Python']，b 也“有了”这本书
```

因为 `a.books` 和 `b.books` 指向同一个列表。正确做法是在 `__init__` 里创建实例属性：

```python
class Library:
    def __init__(self) -> None:
        self.books: list[str] = []
```

**规则：可变对象不要作为类属性。** 需要每个实例一份，就放到 `__init__` 或 `field(default_factory=...)` 里。

---

## 6.3 `@classmethod`：用类来造对象

```python
class Book:
    def __init__(self, isbn: str, title: str, author: str, total_copies: int = 1) -> None:
        ...

    @classmethod
    def from_row(cls, row: tuple[str, str, str, int]) -> Book:
        isbn, title, author, total_copies = row
        return cls(isbn, title, author, total_copies)
```

调用：

```python
book = Book.from_row(("978-7-111-40701-0", "Python 编程", "张三", 2))
```

关键点：

- 第一个参数是 `cls`，代表类本身，不是实例
- 通过 `cls(...)` 创建对象，而不是写死 `Book(...)`
- 这样子类调用 `from_row` 时，会创建子类实例

### 为什么用 `cls` 而不是写死类名

```python
class EBook(Book):
    pass

ebook = EBook.from_row(("...", "...", "...", 1))
print(type(ebook))   # <class 'EBook'>
```

如果 `from_row` 里写的是 `return Book(...)`，得到的就是 `Book`，不是 `EBook`。用 `cls` 才能保留多态。

### 什么时候用 classmethod

适合「另一种创建方式」：

- 从数据库行创建：`Book.from_row(...)`
- 从字典创建：`Member.from_dict(...)`
- 从 JSON 创建：`Loan.from_json(...)`
- 创建默认配置：`Config.default()`

一句话：**classmethod 是工厂方法。**

---

## 6.4 `@staticmethod`：放在类里的普通函数

```python
class Book:
    @staticmethod
    def is_valid_isbn(isbn: str) -> bool:
        return len(isbn.replace("-", "")) in {10, 13}
```

调用：

```python
Book.is_valid_isbn("978-7-111-40701-0")   # True
book.is_valid_isbn("...")                  # 也能调用
```

它不接收 `self`，也不接收 `cls`，本质上就是一个普通函数，只是放在类的命名空间里。

### 什么时候用 staticmethod

- 逻辑和这个类高度相关
- 但不需要访问实例或类状态
- 放在类里能让调用方更容易发现

比如「ISBN 格式校验」和 `Book` 相关，但不需要某本具体的书。放在 `Book` 里比放一个全局函数更清晰。

### classmethod vs staticmethod

| | `@classmethod` | `@staticmethod` |
| :--- | :--- | :--- |
| 第一个参数 | `cls` | 没有 |
| 能否访问类属性 | 能 | 不能（除非写死类名） |
| 典型用途 | 工厂方法 | 工具函数 |
| 返回实例 | 常见 | 不一定 |

如果你不确定用哪个，先问：

- 需要创建对象或访问类状态吗？→ `classmethod`
- 只是一个和类相关的纯函数吗？→ `staticmethod`
- 需要访问实例吗？→ 普通实例方法

---

## 6.5 `@dataclass`：自动生成样板代码

手写一个数据类：

```python
class Book:
    def __init__(self, isbn: str, title: str, author: str) -> None:
        self.isbn = isbn
        self.title = title
        self.author = author

    def __repr__(self) -> str:
        return f"Book(isbn={self.isbn!r}, title={self.title!r}, author={self.author!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Book):
            return NotImplemented
        return (self.isbn, self.title, self.author) == (other.isbn, other.title, other.author)
```

`@dataclass` 自动帮你生成 `__init__`、`__repr__`、`__eq__`：

```python
from dataclasses import dataclass


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    total_copies: int = 1
```

等价于上面一大堆样板代码，还更好维护。

```python
book = Book("978-7-111-40701-0", "Python 编程", "张三", 2)
print(book)
print(book == Book("978-7-111-40701-0", "Python 编程", "张三", 2))
```

### 默认值

```python
@dataclass
class Book:
    isbn: str
    title: str
    total_copies: int = 1
```

有默认值的字段必须放在没有默认值的字段后面，和函数参数规则一样。

### `field(default_factory=...)`

可变默认值不能直接写：

```python
@dataclass
class Member:
    loans: list[str] = []   # ValueError: mutable default
```

因为所有实例会共享同一个列表。正确写法：

```python
from dataclasses import field

@dataclass
class Member:
    loans: list[str] = field(default_factory=list)
```

`default_factory` 是一个函数，每次创建实例时调用一次，返回新的列表。

### `__post_init__`

`dataclass` 生成的 `__init__` 只负责赋值。如果你需要校验或计算派生字段，用 `__post_init__`：

```python
@dataclass
class Book:
    isbn: str
    title: str
    total_copies: int = 1
    _available: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.total_copies < 1:
            raise ValueError("total_copies 必须是正整数")
        self._available = self.total_copies
```

关键点：

- `field(init=False)` 表示这个字段不出现在 `__init__` 参数里
- `repr=False` 表示不参与自动生成的 `__repr__`
- `compare=False` 表示不参与自动生成的 `__eq__`
- `__post_init__` 在自动生成的 `__init__` 末尾被调用

### `frozen=True`

```python
@dataclass(frozen=True)
class Point:
    x: int
    y: int
```

冻结后不能修改属性：

```python
p = Point(1, 2)
p.x = 3   # FrozenInstanceError
```

适合值对象，比如坐标、金额、日期范围。注意：`frozen=True` 也会自动生成 `__hash__`，可以安全地作为 `set` 元素。

### `order=True`

```python
@dataclass(order=True)
class Version:
    major: int
    minor: int
```

自动生成 `<`、`<=`、`>`、`>=`，按字段顺序比较。

### dataclass 不是万能的

它适合「以数据为主、行为较少」的类。如果类的主要职责是复杂行为、状态机或资源管理，手写类可能更清楚。

---

## 6.6 本章模型的关键设计

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
        if not self.isbn.strip():
            raise ValueError("isbn 不能为空")
        if not self.title.strip():
            raise ValueError("title 不能为空")
        if not self.author.strip():
            raise ValueError("author 不能为空")
        if self.total_copies < 1:
            raise ValueError("total_copies 必须是正整数")
        self._available = self.total_copies
```

为什么 `_available` 用 `field(init=False)`？

- 它是由 `total_copies` 推导出来的，不应该让调用方随便传
- 它不参与 `repr`，避免输出太长
- 它不参与 `eq`，因为库存是可变状态，不应该决定「两本书是否相同」

### `Member`

```python
@dataclass
class Member:
    member_id: str
    name: str
    max_loans: int = 3
    _loans: list[Loan] = field(default_factory=list, init=False, repr=False)

    @property
    def active_loans(self) -> tuple[Loan, ...]:
        return tuple(loan for loan in self._loans if loan.is_active)

    @property
    def can_borrow(self) -> bool:
        return len(self.active_loans) < self.max_loans

    def add_loan(self, loan: Loan) -> None:
        if not self.can_borrow:
            raise ValueError("借阅数量已达上限")
        self._loans.append(loan)
```

`_loans` 用 `default_factory=list`，保证每个会员有自己的列表。

> 这里 `Loan` 在后面才定义，示例文件顶部有 `from __future__ import annotations`，所以类型标注不会在这一行立刻求值。

### `Loan`

```python
@dataclass
class Loan:
    book: Book
    member: Member
    borrowed_on: date
    due_on: date
    returned_on: date | None = None

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

    def close(self, returned_on: date) -> None:
        if not self.is_active:
            raise ValueError("这条借阅记录已经归还")
        if returned_on < self.borrowed_on:
            raise ValueError("归还日期不能早于借阅日期")
        self.returned_on = returned_on
```

`Loan.create` 是一个 classmethod 工厂：调用方不需要自己算 `due_on`，也不容易算错。`close` 负责关闭记录，并维护「归还日期不能早于借阅日期」这条规则。

### `from_row` 和 `from_dict`

```python
@classmethod
def from_row(cls, row: tuple[str, str, str, int]) -> Book:
    isbn, title, author, total_copies = row
    return cls(isbn, title, author, total_copies)

@classmethod
def from_dict(cls, data: dict[str, object]) -> Member:
    return cls(
        str(data["member_id"]),
        str(data["name"]),
        int(data.get("max_loans", 3)),
    )
```

这两个方法是「适配器」：把外部数据格式（数据库行、字典）转换成领域对象。它们让创建逻辑集中在类里，而不是散落在业务代码中。

---

## 6.7 动手改

在 `examples/ch06_models.py` 中：

1. 给 `Book` 增加 `from_dict`，从 `{"isbn": ..., "title": ..., "author": ..., "total_copies": ...}` 创建对象。
2. 给 `Loan` 增加 `is_due_soon(self, today: date, days: int = 3) -> bool`：未归还且距离到期不超过 `days` 天时返回 `True`。可以复用已有的 `days_left`。
3. 把 `Book` 改成 `@dataclass(frozen=True)`，看看哪些代码会报错，思考为什么。

参考实现：

```python
@classmethod
def from_dict(cls, data: dict[str, object]) -> Book:
    return cls(
        str(data["isbn"]),
        str(data["title"]),
        str(data["author"]),
        int(data.get("total_copies", 1)),
    )

def is_due_soon(self, today: date, days: int = 3) -> bool:
    return self.is_active and 0 <= self.days_left(today) <= days
```

改成 `frozen=True` 后，`checkout()` 里的 `self._available -= 1` 会失败，因为冻结对象不可变。这说明：**库存会变化，`Book` 不适合冻结。**

---

## 6.8 常见坑

### 坑 1：可变类属性

```python
class Library:
    books = []
```

所有实例共享。用 `__init__` 或 `default_factory`。

### 坑 2：dataclass 可变默认值

```python
@dataclass
class Member:
    loans: list[str] = []
```

直接报 `ValueError`。用 `field(default_factory=list)`。

### 坑 3：`field(init=False)` 后忘记赋值

```python
@dataclass
class Book:
    _available: int = field(init=False)

    def __post_init__(self) -> None:
        pass   # 没有给 _available 赋值
```

访问 `book._available` 会报 `AttributeError`。在 `__post_init__` 里补上。

### 坑 4：以为 dataclass 自动处理所有校验

它只生成 `__init__` / `__repr__` / `__eq__`，不校验类型，也不校验业务规则。校验要自己写在 `__post_init__` 或方法里。

### 坑 5：`frozen=True` 还去修改字段

冻结对象适合值对象，不适合有可变状态的实体（比如库存会变的 `Book`）。

### 坑 6：classmethod 里写死类名

```python
@classmethod
def from_row(cls, row):
    return Book(*row)   # 子类调用时返回 Book，不是子类
```

应该用 `cls(*row)`。

---

## 6.9 本章练习

### 练习 A：`Loan.from_dict`

实现：

```python
@classmethod
def from_dict(cls, data: dict[str, object]) -> Loan:
    ...
```

输入示例：

```python
{
    "book": book,
    "member": member,
    "borrowed_on": "2026-10-26",
    "due_on": "2026-11-09",
    "returned_on": None,
}
```

提示：用 `date.fromisoformat(...)` 解析字符串。`returned_on` 为 `None` 时不要解析。

### 练习 B：`Member` 的工厂

给 `Member` 增加 `from_tuple(cls, row: tuple[str, str, int])`，并用它创建对象。

### 练习 C：思考

下面三个方法分别应该用实例方法、classmethod 还是 staticmethod？

1. `book.describe()`
2. `Book.from_row(row)`
3. `Book.is_valid_isbn(isbn)`
4. `member.borrow(book)`

第 4 题没有唯一答案。先判断职责，再决定放在哪个类上。

---

## 6.10 检查点

1. 类属性和实例属性有什么区别？可变类属性有什么风险？
2. `@classmethod` 的第一个参数是什么？为什么工厂方法要用它？
3. `@staticmethod` 和普通函数有什么区别？
4. `@dataclass` 自动生成了哪些方法？
5. `field(default_factory=list)` 解决了什么问题？
6. `__post_init__` 什么时候执行？

如果第 2、4、5 题能说清，你已经能写出更专业的模型层了。

---

[← 上一章：魔术方法](./05_magic_methods.md) | [下一章：异常与协议 →](./07_errors_protocols.md)