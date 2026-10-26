# 第 01 章：类与实例——写出第一个真正可用的类

> 本章目标：能独立写出一个带属性、带方法的类，并说清 `__init__`、`self`、实例属性分别是什么。

---

## 1.1 先运行

在 `Python/oop` 目录下执行：

```bash
python -m examples.ch01_book
```

输出：

```text
《Python 编程》 / 张三 / 2020
True
{'isbn': '978-7-111-40701-0', 'title': 'Python 编程', 'author': '张三', 'year': 2020}
True
```

完整代码在 [`examples/ch01_book.py`](../examples/ch01_book.py)：

```python
from __future__ import annotations


class Book:
    def __init__(self, isbn: str, title: str, author: str, year: int) -> None:
        self.isbn = isbn
        self.title = title
        self.author = author
        self.year = year

    def describe(self) -> str:
        return f"《{self.title}》 / {self.author} / {self.year}"

    def is_same_edition(self, other: Book) -> bool:
        return self.isbn == other.isbn


def main() -> None:
    book = Book("978-7-111-40701-0", "Python 编程", "张三", 2020)
    other = Book("978-7-111-40701-0", "Python 编程（第 2 版）", "张三", 2022)

    print(book.describe())
    print(book.is_same_edition(other))
    print(book.__dict__)
    print(isinstance(book, Book))


if __name__ == "__main__":
    main()
```

先别急着往下看。试着回答：

1. `Book` 是什么？
2. `book` 是什么？
3. `book.describe()` 为什么不需要传参数？
4. `book.__dict__` 里为什么有四个键？

---

## 1.2 定义一个类

最小语法：

```python
class Book:
    pass
```

`class` 后面是类名，Python 约定用 **大驼峰**（`Book`、`LoanRecord`、`LibraryMember`）。

`pass` 表示「先占个位置」。现在 `Book` 是一个空的类，可以创建实例，但没有任何数据和行为：

```python
book = Book()
print(book)   # <__main__.Book object at 0x...>
```

这个输出说明：`book` 是一个 `Book` 对象，后面那串是内存地址。它能用，但没什么用。

---

## 1.3 `__init__`：对象创建后自动执行

我们通常希望对象一创建就带上数据：

```python
class Book:
    def __init__(self, isbn: str, title: str, author: str, year: int) -> None:
        self.isbn = isbn
        self.title = title
        self.author = author
        self.year = year
```

几个关键点：

- `__init__` 是**初始化方法**，不是构造函数。对象已经被创建出来了，它负责给对象填初始数据。
- 它的第一个参数是 `self`。
- 它**不应该返回值**，返回 `None` 是约定。你写 `return` 返回别的东西，Python 创建对象时会报错。
- 调用 `Book(...)` 时，Python 自动调用 `__init__`，你不需要手动写 `book.__init__(...)`。

执行：

```python
book = Book("978-7-111-40701-0", "Python 编程", "张三", 2020)
```

大致发生：

```text
1. 创建一个空的 Book 实例
2. 把实例作为 self，连同四个参数一起传给 __init__
3. __init__ 把 isbn/title/author/year 挂到 self 上
4. 返回这个实例，赋值给 book
```

---

## 1.4 `self`：当前对象的引用

```python
def __init__(self, title: str) -> None:
    self.title = title
```

`self.title = title` 的意思是：

> 把参数 `title` 的值，保存到「当前这个对象」的 `title` 属性上。

左边的 `self.title` 是对象属性，右边的 `title` 是局部参数。名字可以不同，但同名最直观。

为什么不能省略 `self`？

```python
class Book:
    def __init__(self, title: str) -> None:
        title = title       # 只是给局部变量自己赋值，对象上什么都没有
```

这样写不会报错，但 `book.title` 会抛出 `AttributeError`，因为对象上根本没有 `title` 这个属性。

所以记住一句话：

> **想在对象上存东西，必须写 `self.xxx = ...`。**

---

## 1.5 实例属性：每个对象各有一份

```python
b1 = Book("978-7-111-40701-0", "Python 编程", "张三", 2020)
b2 = Book("978-7-115-54608-7", "算法导论", "李四", 2019)

print(b1.title)   # Python 编程
print(b2.title)   # 算法导论
```

`b1` 和 `b2` 是两个独立实例。它们的 `title` 互不影响：

```python
b2.title = "算法导论（第 3 版）"
print(b1.title)   # Python 编程
print(b2.title)   # 算法导论（第 3 版）
```

每个实例的属性集合可以用 `__dict__` 观察：

```python
print(b1.__dict__)
```

```text
{'isbn': '978-7-111-40701-0', 'title': 'Python 编程', 'author': '张三', 'year': 2020}
```

`__dict__` 是 Python 用来存实例属性的字典。初学阶段用它理解「属性到底存在哪」很有帮助，但**业务代码里不要依赖它**。

---

## 1.6 方法：对象能做什么

```python
def describe(self) -> str:
    return f"《{self.title}》 / {self.author} / {self.year}"
```

这是一个实例方法。调用：

```python
print(book.describe())
```

注意 `describe` 定义时有一个 `self`，调用时却没有传参数。这是因为：

```python
book.describe()
```

等价于：

```python
Book.describe(book)
```

Python 自动把 `book` 绑到 `self` 上。你可以手动验证：

```python
print(Book.describe(book))
```

输出一样。但平时不要这么写，`book.describe()` 才是正常风格。

### 方法可以接收其它参数

```python
class Book:
    def __init__(self, title: str) -> None:
        self.title = title

    def rename(self, new_title: str) -> None:
        self.title = new_title

    def matches(self, keyword: str) -> bool:
        return keyword.lower() in self.title.lower()
```

```python
book = Book("Python 编程")
book.rename("Python 实战")
print(book.matches("python"))   # True
```

`rename` 修改对象状态，`matches` 只读取状态。**修改状态的方法要谨慎设计**，这是第 02 章封装的主题。

---

## 1.7 类本身也是对象

```python
print(type(book))    # <class '__main__.Book'>
print(type(Book))    # <class 'type'>
```

- `book` 是 `Book` 的实例
- `Book` 是 `type` 的实例（类也是对象）
- `isinstance(book, Book)` 判断 `book` 是不是 `Book` 的实例，返回 `True`

`isinstance` 在后面的多态和异常处理中会经常出现：

```python
print(isinstance(book, Book))   # True
print(isinstance(book, object)) # True，所有类最终都继承 object
```

---

## 1.8 一个类可以创建很多对象

```python
books = [
    Book("978-7-111-40701-0", "Python 编程", "张三", 2020),
    Book("978-7-115-54608-7", "算法导论", "李四", 2019),
    Book("978-7-121-33814-8", "深入理解计算机系统", "王五", 2016),
]

for book in books:
    print(book.describe())
```

输出：

```text
《Python 编程》 / 张三 / 2020
《算法导论》 / 李四 / 2019
《深入理解计算机系统》 / 王五 / 2016
```

这里已经有一点「面向对象」的味道了：**数据和处理数据的方法绑定在一起，循环只负责让每个对象做自己的事。**

---

## 1.9 动手改

打开 `examples/ch01_book.py`，完成下面三件事：

1. 给 `Book` 增加一个 `pages: int` 属性，并更新 `describe`，让它输出页数。
2. 增加方法 `is_long(self) -> bool`，页数大于 500 返回 `True`。
3. 在 `main` 里创建一本 800 页的书，打印 `is_long()`。

改完后运行：

```bash
python -m examples.ch01_book
```

先自己写，不要直接看答案。参考实现：

```python
class Book:
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        year: int,
        pages: int,
    ) -> None:
        self.isbn = isbn
        self.title = title
        self.author = author
        self.year = year
        self.pages = pages

    def describe(self) -> str:
        return f"《{self.title}》 / {self.author} / {self.year} / {self.pages} 页"

    def is_long(self) -> bool:
        return self.pages > 500
```

---

## 1.10 常见错误

| 错误 | 原因 | 修复 |
| :--- | :--- | :--- |
| `TypeError: Book.__init__() missing 1 required positional argument: 'title'` | 创建实例时少传参数 | 按 `__init__` 的参数补全 |
| `AttributeError: 'Book' object has no attribute 'title'` | `__init__` 里写成了 `title = title` | 改成 `self.title = title` |
| `TypeError: describe() takes 1 positional argument but 2 were given` | 方法定义时漏了 `self` | 第一个参数加 `self` |
| `TypeError: __init__() should return None` | `__init__` 里写了 `return 某个值` | 删掉返回值 |
| 两个对象的属性互相影响 | 使用了类属性或可变默认值 | 第 06 章会专门讲，实例属性优先写在 `self` 上 |

---

## 1.11 本章练习

### 练习 A：`Member` 类

写一个 `Member` 类：

- 属性：`member_id`、`name`、`max_loans`
- 方法 `describe()`，返回 `"M001 / 小明 / 最多借 3 本"`
- 方法 `can_borrow(self, current_loans: int) -> bool`，当前借阅数小于上限时返回 `True`

创建两个会员并打印描述。

### 练习 B：`Loan` 类

写一个 `Loan` 类：

- 属性：`book_title`、`member_name`、`days`
- 方法 `summary()`，返回 `"小明 借了《Python 编程》，借期 14 天"`
- 方法 `is_overdue(self, days_used: int) -> bool`

创建一条借阅记录并打印摘要。

### 练习 C：思考题

下面两种写法有什么区别？

```python
# 写法一
book.describe()

# 写法二
Book.describe(book)
```

如果 `book` 是 `None`，两种写法分别会发生什么？

---

## 1.12 检查点

1. `__init__` 什么时候执行？它应该返回什么？
2. `self` 是什么？为什么实例方法需要它？
3. 实例属性存在哪里？两个实例的属性会互相影响吗？
4. `book.describe()` 为什么可以不给 `self` 传参？
5. 什么情况下你其实不需要写类？

能回答前 4 题，就进入第 02 章。第 5 题没有标准答案，但希望你能意识到：**类不是越多越好。**

---

[← 上一章：心智模型](./00_mental_model.md) | [下一章：封装 →](./02_encapsulation.md)