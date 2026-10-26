# 第 04 章：组合——用对象搭出一个系统

> 本章目标：让 `Library` 管理 `Book`、`Member`、`Loan`，理解「有一个」比「是一个」更适合搭系统。

---

## 4.1 从单个对象到对象网络

前几章我们一直在打磨 `Book`。但一个图书馆不可能只有书：

- 书要被图书馆管理
- 会员要能借书
- 借书会产生一条借阅记录
- 还书要更新库存和记录

这些对象之间不是继承关系，而是**协作关系**：

```text
Library  1 ─── * Book
   │
   ├── * Member
   │        │
   │        └── 1 ─── * Loan ─── 1 ─── Book
   │
   └── * Loan
```

用代码表达就是：

```python
class Library:
    def __init__(self) -> None:
        self._books: dict[str, Book] = {}
        self._members: dict[str, Member] = {}
        self._loans: list[Loan] = []
```

`Library` **有一个** 图书字典、**有一个** 会员字典、**有一个** 借阅记录列表。它不继承它们。

这就是组合：

> **通过持有其它对象，把简单对象组合成更复杂的系统。**

---

## 4.2 先运行

```bash
python -m examples.ch04_library
```

输出：

```text
小明 借了《Python 编程》，应还 2026-11-09
《Python 编程》剩余库存：1
小明 当前借阅：2 本
归还《Python 编程》后剩余库存：2
2026-12-01 的逾期记录：
- 小明 / 《算法导论》 / 应还 2026-11-09
搜索 python：['Python 编程']
```

完整代码在 [`examples/ch04_library.py`](../examples/ch04_library.py)。

---

## 4.3 四个类，各管什么

### `Book`：只管自己的库存

```python
class Book:
    def checkout(self) -> None:
        ...

    def checkin(self) -> None:
        ...
```

它不知道图书馆、会员、借阅记录的存在。这是好事：**职责越单一，越容易测试和复用。**

### `Member`：只管自己的借阅额度

```python
class Member:
    def __init__(self, member_id: str, name: str, max_loans: int = 3) -> None:
        ...
        self._loans: list[Loan] = []

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

会员不需要知道图书馆里有哪些书，它只关心「我已经借了几本、还能不能再借」。

### `Loan`：只管一条借阅记录

```python
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
```

它把「谁借了什么、什么时候还」固定下来。注意它持有的是 `Book` 和 `Member` 对象，而不是一堆字符串。这样需要书名时直接 `loan.book.title`，不用再查表。

### `Library`：协调者

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
        raise ValueError(f"《{book.title}》暂时无法借阅")
    if not member.can_borrow:
        raise ValueError(f"{member.name} 的借阅数量已达上限")

    book.checkout()
    loan = Loan(book, member, today, today + timedelta(days=14))
    member.add_loan(loan)
    self._loans.append(loan)
    return loan
```

`Library` 负责：

1. 找到书和会员
2. 检查能不能借
3. 让书减库存
4. 创建借阅记录
5. 把记录挂到会员和图书馆上

它不直接修改 `book._available`，而是调用 `book.checkout()`。**协调者负责流程，对象负责自己的规则。**

---

## 4.4 为什么 `borrow` 放在 `Library` 上

这是本章最重要的设计问题。

如果把 `borrow` 放到 `Book` 上：

```python
class Book:
    def borrow(self, member: Member, today: date) -> Loan:
        ...
```

`Book` 就需要知道：

- 会员是谁
- 会员还能借几本
- 借期多长
- 借阅记录存哪里

它从「一本书」变成了「一个借阅系统」，职责爆炸。

如果把 `borrow` 放到 `Member` 上：

```python
class Member:
    def borrow(self, isbn: str, today: date) -> Loan:
        ...
```

`Member` 就需要知道图书馆有哪些书、库存多少。它和 `Book` 之间产生了不必要的依赖。

放到 `Library` 上最自然，因为：

- 它本来就持有书和会员
- 它是唯一能同时看到两边状态的对象
- 它负责协调，但不承担具体规则

一个判断职责的技巧：

> **问「这个动作需要知道谁的状态？」**
>
> 只需要自己的状态 → 放到自己身上。
> 需要协调多个对象 → 放到更高层的协调者身上。

---

## 4.5 组合 vs 继承，再强调一次

| 场景 | 选择 | 原因 |
| :--- | :--- | :--- |
| `PaperBook` 是一种 `Book` | 继承 | is-a |
| `Library` 有很多 `Book` | 组合 | has-a |
| `Loan` 关联一个 `Book` 和一个 `Member` | 组合 | has-a |
| `Library` 想把借阅规则换成「学生 7 天、教师 30 天」 | 组合一个规则对象 | 行为可替换 |

继承是「我是什么」，组合是「我有什么、我和谁协作」。

真实系统里，**组合远多于继承**。继承适合表达稳定的类型层级，组合适合应对变化。

---

## 4.6 依赖注入：把 `today` 传进来

注意 `borrow` 的签名：

```python
def borrow(self, isbn: str, member_id: str, today: date | None = None) -> Loan:
    today = today or date.today()
```

为什么不直接在里面写 `date.today()`？

因为写死之后，测试会变得很难：

```python
# 想测试「逾期」，难道要等到 15 天后？
loan = library.borrow("...", "...")
assert loan.is_overdue(date.today() + timedelta(days=15))
```

把「今天」作为参数传进来，测试就能控制时间：

```python
borrowed = date(2026, 1, 1)
loan = library.borrow("...", "...", today=borrowed)
assert loan.is_overdue(date(2026, 1, 20))
```

这叫**依赖注入**（dependency injection）：

> 对象不自己创建依赖，而是由外部传进来。

它不只适用于时间。数据库连接、通知服务、随机数生成器，都可以通过构造函数或方法参数注入。第 07 章会看到更完整的用法。

---

## 4.7 不要越过对象直接改它的内部

假设你想给会员续借，可能会写：

```python
loan = library._members["M001"]._loans[0]
loan.due_on += timedelta(days=7)
```

这行代码跨了三层：

- 访问 `library._members`
- 访问 `member._loans`
- 直接改 `loan.due_on`

问题：

- 你依赖了三个对象的内部结构
- 任何一层改名，这行就崩
- 绕过了所有校验

更好的方式是在 `Loan` 上提供 `renew`：

```python
def renew(self, days: int) -> None:
    if days < 1:
        raise ValueError("续借天数必须是正整数")
    if not self.is_active:
        raise ValueError("已归还的记录不能续借")
    self.due_on += timedelta(days=days)
```

然后调用：

```python
loan.renew(7)
```

这叫「告诉对象做什么，而不是把它的数据掏出来自己做」。

一个相关的原则叫**迪米特法则**（Law of Demeter）：

> 只和直接的朋友说话，不要跟朋友的朋友的朋友打交道。

`library._members["M001"]._loans[0].due_on` 就是典型的「跟朋友的朋友的朋友打交道」。

---

## 4.8 本章代码的关键方法

### `_require_book` / `_require_member`

```python
def _require_book(self, isbn: str) -> Book:
    try:
        return self._books[isbn]
    except KeyError:
        raise ValueError(f"找不到 ISBN 为 {isbn} 的图书") from None
```

`_require_` 前缀表示「内部辅助方法」。它把「找不到就报错」的逻辑收在一处，避免每个方法都写一遍。

`raise ... from None` 会隐藏原始 `KeyError` 的上下文，让报错信息更干净。第 07 章会详细讲异常链。

### `return_book`

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

    for loan in member.active_loans:
        if loan.book is book:
            loan.close(today)
            book.checkin()
            return loan

    raise ValueError(f"{member.name} 没有借阅《{book.title}》")
```

两个细节：

- 用 `loan.book is book` 判断是不是同一本书。`is` 比较对象身份，不是内容。
- 先 `loan.close()`，再 `book.checkin()`。如果 `close` 失败（比如日期不合法），库存不会被错误地加回去。

### `overdue_loans`

```python
def overdue_loans(self, today: date | None = None) -> list[Loan]:
    today = today or date.today()
    return [loan for loan in self._loans if loan.is_overdue(today)]
```

它遍历所有借阅记录，让每条记录自己判断是否逾期。`Library` 不需要知道逾期规则的具体实现。

---

## 4.9 动手改

在 `examples/ch04_library.py` 中：

1. 给 `Library` 增加只读属性 `member_count`，返回已注册会员数。
2. 给 `Library` 增加 `member_loans(member_id: str) -> list[Loan]`，返回某个会员当前未归还的记录。
3. 给 `Loan` 增加 `renew(self, days: int) -> None`，要求：
   - `days` 必须是正整数
   - 只有未归还的记录能续借
   - 续借后 `due_on` 增加相应天数

参考实现：

```python
@property
def member_count(self) -> int:
    return len(self._members)

def member_loans(self, member_id: str) -> list[Loan]:
    member = self._require_member(member_id)
    return list(member.active_loans)

def renew(self, days: int) -> None:
    if days < 1:
        raise ValueError("续借天数必须是正整数")
    if not self.is_active:
        raise ValueError("已归还的记录不能续借")
    self.due_on += timedelta(days=days)
```

---

## 4.10 常见坑

### 坑 1：让底层对象知道上层

```python
class Book:
    def __init__(self, library: Library) -> None:
        self.library = library
```

书不需要知道图书馆。这种反向依赖会让对象难以单独测试。

### 坑 2：把协调逻辑塞进 `Book` 或 `Member`

看到 `book.borrow(member, library)` 这种签名就要警惕：一个借书动作牵扯三个对象，说明职责放错了。

### 坑 3：直接访问别人的内部字段

```python
library._books[isbn]._available -= 1
```

绕过 `checkout()`，库存校验全部失效。

### 坑 4：对象之间循环引用

`Library` 持有 `Member`，`Member` 持有 `Loan`，`Loan` 又持有 `Member`。适度的双向引用没问题，但要小心序列化和内存泄漏。能用 ID 关联的地方，不一定非要对象引用。

### 坑 5：把 `date.today()` 写死

测试时间相关逻辑时非常痛苦。像本章这样通过参数注入「今天」，是更可测的写法。

---

## 4.11 本章练习

### 练习 A：借阅上限

在 `Library.borrow` 中，会员达到上限时抛出的 `ValueError` 信息应该包含：

- 会员名
- 当前借阅数
- 上限

先写测试数据，再改代码，确认信息符合预期。

### 练习 B：改进搜索

示例中的 `search` 已经能匹配书名、作者、ISBN。请继续改进：

1. 关键词先 `strip()`，空关键词直接返回 `[]`
2. 返回结果按书名排序
3. 为「空关键词」「大小写」「作者匹配」各补一个测试

提示：`sorted(books, key=lambda book: book.title)`。

### 练习 C：设计题

如果图书馆要支持「预约」：

- 谁应该持有预约记录？
- 预约和借阅是什么关系？
- 一本书被预约后，`borrow` 的行为要怎么变？

画出类关系图，写一段伪代码，不用完整实现。

---

## 4.12 检查点

1. 组合和继承的区别是什么？用「是一个 / 有一个」各举一例。
2. 为什么 `borrow` 放在 `Library` 而不是 `Book`？
3. `Loan` 为什么持有 `Book` 和 `Member` 对象，而不是只存 ID？
4. 什么是依赖注入？本章哪里用到了它？
5. 为什么不要写 `library._members["M001"]._loans[0].due_on`？

如果第 2、3、4 题能说清，你已经具备搭一个小系统的基本直觉。

---

[← 上一章：继承与多态](./03_inheritance.md) | [下一章：魔术方法 →](./05_magic_methods.md)