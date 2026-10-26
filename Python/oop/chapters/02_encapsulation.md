# 第 02 章：封装——让对象自己守规则

> 本章目标：把「库存不能为负」这条规则放进 `Book` 内部，让外部只能通过安全的接口修改状态。

---

## 2.1 先看问题

第 01 章的 `Book` 长这样：

```python
class Book:
    def __init__(self, title: str, available: int) -> None:
        self.title = title
        self.available = available
```

外部可以随便改：

```python
book = Book("Python 编程", 2)
book.available = -100   # 不报错
book.available = 9999   # 也不报错
```

类的作者明明知道「库存不能为负」，但数据是公开的，规则就形同虚设。

封装的第一个目标：

> **不要让外部直接改内部状态，而是提供有意义的方法，让对象自己检查规则。**

---

## 2.2 先运行本章示例

```bash
python -m examples.ch02_book
```

输出：

```text
初始库存：1
借出一本后：0
再借：没有库存了
归还后：1
直接改 available：property 'available' of 'Book' object has no setter
```

完整代码在 [`examples/ch02_book.py`](../examples/ch02_book.py)：

```python
from __future__ import annotations


class Book:
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        total_copies: int = 1,
    ) -> None:
        if not isinstance(total_copies, int) or total_copies < 1:
            raise ValueError("total_copies 必须是正整数")

        self.isbn = isbn
        self.title = title
        self.author = author
        self._total_copies = total_copies
        self._available = total_copies

    @property
    def total_copies(self) -> int:
        return self._total_copies

    @property
    def available(self) -> int:
        return self._available

    @property
    def is_available(self) -> bool:
        return self._available > 0

    def checkout(self) -> None:
        if self._available <= 0:
            raise ValueError(f"《{self.title}》没有库存了")
        self._available -= 1

    def checkin(self) -> None:
        if self._available >= self._total_copies:
            raise ValueError(f"《{self.title}》的库存已满，无法归还")
        self._available += 1

    def describe(self) -> str:
        return (
            f"《{self.title}》 / {self.author} / "
            f"库存 {self._available}/{self._total_copies}"
        )


def main() -> None:
    book = Book("978-7-111-40701-0", "Python 编程", "张三", total_copies=1)
    print(f"初始库存：{book.available}")

    book.checkout()
    print(f"借出一本后：{book.available}")

    try:
        book.checkout()
    except ValueError as exc:
        print(f"再借：{exc}")

    book.checkin()
    print(f"归还后：{book.available}")

    try:
        book.available = 5
    except AttributeError as exc:
        print(f"直接改 available：{exc}")


if __name__ == "__main__":
    main()
```

---

## 2.3 下划线约定：`_available` 是什么意思

Python 没有像 Java 那样的 `private` 关键字，它靠约定：

| 写法 | 约定含义 | 外部能不能访问 |
| :--- | :--- | :--- |
| `available` | 公开属性 | 可以 |
| `_available` | 内部属性 | **不建议**，但语法上可以 |
| `__available` | 名称改写为 `_Book__available` | 强烈不建议绕过去访问 |

`_available` 的意思是：

> 这是类的内部实现，外部请不要依赖它。我要改这个名字时，不会提前通知你。

它**不是安全锁**。你仍然可以写：

```python
book._available = 999
```

Python 不会阻止你。但这是「你主动破坏了对象的约定」，后果自负。封装的本质是**设计边界**，不是阻止恶意代码。

### 为什么不用 `__available`

```python
class Book:
    def __init__(self) -> None:
        self.__available = 1
```

外部访问 `book.__available` 会失败，但实际上它被改名成了 `book._Book__available`，仍然能访问。名称改写主要服务于继承场景，避免子类意外覆盖父类属性。**初学阶段用单下划线就够了**，不要为了「更私有」滥用双下划线。

---

## 2.4 `@property`：把方法伪装成属性

```python
@property
def available(self) -> int:
    return self._available
```

加 `@property` 后，可以像读属性一样读：

```python
print(book.available)   # 1
```

但**不能**像属性一样写：

```python
book.available = 5      # AttributeError
```

因为这里只定义了 getter，没有定义 setter。这正好实现了「只读属性」。

### 对比：普通方法 vs property

```python
# 方法
def get_available(self) -> int:
    return self._available

# property
@property
def available(self) -> int:
    return self._available
```

调用方式：

```python
book.get_available()   # 方法
book.available         # property
```

什么时候用 property？

- 它描述的是对象的**状态**，不是动作
- 读取时不需要传参数
- 你希望外部像访问属性一样使用它

`book.available` 读起来像「书的可用数量」，比 `book.get_available()` 自然。

### 什么时候用普通方法？

- 有参数，例如 `book.matches("python")`
- 有副作用，例如 `book.checkout()` 会改变库存
- 动作语义明显，例如 `library.borrow(...)`

一个简单的判断：

> **名词用属性，动词用方法。**

---

## 2.5 不要写「贫血的 setter」

有些人学封装后，会这样写：

```python
@property
def available(self) -> int:
    return self._available

@available.setter
def available(self, value: int) -> None:
    self._available = value
```

这看起来封装了，实际上和公开属性没区别，外部还是能写：

```python
book.available = -100
```

**只是多了一层语法，规则一点没守住。**

真正有价值的是提供表达业务意图的方法：

```python
def checkout(self) -> None:
    ...

def checkin(self) -> None:
    ...
```

调用方不需要知道库存字段叫什么，也不需要自己判断能不能借。它只需要说「我要借」，对象负责执行规则。

这就是封装和「无脑 getter/setter」的区别：

| 写法 | 外部需要知道什么 | 规则在哪 |
| :--- | :--- | :--- |
| `book.available -= 1` | 字段名、判断逻辑 | 散落在外部 |
| `book.checkout()` | 只需要知道「借书」这个动作 | 在 `Book` 内部 |

---

## 2.6 不变量：对象始终要满足的规矩

`Book` 有两个不变量（invariant）：

```text
0 <= available <= total_copies
total_copies >= 1
```

不变量是「任何时候都必须成立的条件」。封装的职责就是：

- 创建对象时检查
- 每个修改状态的方法都检查
- 外部无法绕过这些方法直接破坏它

在本章的 `Book` 里：

| 入口 | 检查 |
| :--- | :--- |
| `__init__` | `total_copies` 必须是正整数 |
| `checkout` | `available > 0` 才能减 |
| `checkin` | `available < total_copies` 才能加 |
| 外部写 `available` | 没有 setter，直接报错 |

于是 `available` 永远不可能变成负数，也不可能超过总库存。

---

## 2.7 一个容易被忽略的细节：参数校验

```python
if not isinstance(total_copies, int) or total_copies < 1:
    raise ValueError("total_copies 必须是正整数")
```

为什么先判断 `isinstance`？

因为 `True` 在 Python 里是 `int` 的子类：

```python
isinstance(True, int)   # True
```

如果你不想接受 `True` 当作库存 1，可以写得更严格：

```python
if type(total_copies) is not int or total_copies < 1:
    ...
```

初学阶段不用纠结这个细节。重点是：**非法数据要在边界处尽早失败**，不要让它悄悄流进系统，最后在很远的地方爆炸。

---

## 2.8 动手改

在 `examples/ch02_book.py` 中完成：

1. 增加方法 `add_copies(self, count: int) -> None`：
   - `count` 必须是正整数，否则 `ValueError`
   - 同时增加 `_total_copies` 和 `_available`
2. 增加只读 property `is_out_of_stock`，库存为 0 时返回 `True`。
3. 在 `main` 中调用 `add_copies(2)`，打印新的总库存和可用库存。

参考实现：

```python
def add_copies(self, count: int) -> None:
    if not isinstance(count, int) or count < 1:
        raise ValueError("count 必须是正整数")
    self._total_copies += count
    self._available += count

@property
def is_out_of_stock(self) -> bool:
    return self._available == 0
```

---

## 2.9 常见坑

### 坑 1：property 里递归调用自己

```python
@property
def available(self) -> int:
    return self.available      # 无限递归！
```

应该返回内部字段：

```python
return self._available
```

### 坑 2：setter 里也递归

```python
@available.setter
def available(self, value: int) -> None:
    self.available = value     # 又调用 setter，无限递归
```

应该写：

```python
self._available = value
```

### 坑 3：只写了 `_available`，却忘了 property

```python
book._available   # 能访问，但这是内部字段
book.available    # AttributeError，因为没定义 property
```

### 坑 4：把校验写在 setter，却允许外部改内部字段

```python
book._available = -1   # 绕过 setter，依然能破坏
```

所以真正重要的不是「有没有 setter」，而是**外部是否只能通过有意义的方法修改状态**。业务代码里不要主动碰别人的 `_xxx` 字段。

### 坑 5：所有属性都加 property

不是所有属性都需要。`title`、`author` 这类不需要额外校验、也不会破坏不变量的字段，公开即可。过度封装会让代码又长又难读。

---

## 2.10 本章练习

### 练习 A：给 `Member` 加封装

设计一个 `Member` 类：

- 属性：`member_id`、`name`
- 内部字段：`_loans: list[str]`
- 只读属性：`loan_count`
- 方法：`borrow(self, book_title: str) -> None`，借阅数达到 3 时抛 `ValueError`
- 方法：`give_back(self, book_title: str) -> None`，没借过这本书时抛 `ValueError`

要求外部不能直接把 `_loans` 改成任意内容。

### 练习 B：给 `Book` 加「预约」规则

新增：

- 内部字段 `_reserved: int`，默认 0
- 只读属性 `reserved`
- 方法 `reserve()`：库存为 0 时抛 `ValueError`，否则 `_reserved += 1`
- 方法 `cancel_reservation()`：没有预约时抛 `ValueError`

思考：预约会减少 `available` 吗？如果不会，`available` 和 `reserved` 的关系是什么？先想清楚业务规则再写代码。

### 练习 C：判断该不该用 property

下面哪些更适合 property，哪些更适合普通方法？

1. `book.available`
2. `book.borrow_to("小明")`
3. `library.book_count`
4. `library.search("python")`
5. `member.is_over_limit`

---

## 2.11 检查点

1. `_available` 和 `available` 有什么区别？
2. 为什么 `book.available = 5` 会报错？
3. 只定义 getter、不定义 setter，能带来什么保证？
4. 为什么「给每个字段都加 getter/setter」不叫好的封装？
5. `Book` 的两个不变量是什么？哪些方法在维护它们？

如果第 3、4 题能说清，说明你已经理解封装的核心。

---

[← 上一章：类与实例](./01_class_and_instance.md) | [下一章：继承与多态 →](./03_inheritance.md)