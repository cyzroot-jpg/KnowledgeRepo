# 第 00 章：先建立正确的心智模型

> 本章不写复杂代码，只解决一个问题：**为什么需要对象？**

---

## 0.1 先看一段「没有对象」的代码

假设要记录一本书，最直接的做法是用字典：

```python
book = {
    "isbn": "978-7-111-40701-0",
    "title": "Python 编程",
    "author": "张三",
    "available": 2,
}
```

要借出一本，就写一个函数：

```python
def checkout(book: dict) -> None:
    if book["available"] <= 0:
        raise ValueError("没有库存了")
    book["available"] -= 1
```

用起来也没问题：

```python
checkout(book)
print(book["available"])   # 1
```

可是项目一大，麻烦就来了。

---

## 0.2 过程式写法会在哪里失控

### 问题一：规则散落在各处

今天你在 `checkout` 里检查库存：

```python
if book["available"] <= 0:
    raise ValueError("没有库存了")
```

明天另一个函数 `reserve` 也需要检查，于是复制一遍。后天有人在某个脚本里直接写：

```python
book["available"] -= 1
```

库存就变成负数了。**数据谁都能改，规则就守不住。**

### 问题二：任何字典都长得像书

```python
checkout({"title": "随便什么", "available": 3})
```

这个字典没有 `isbn`、没有 `author`，但 `checkout` 不关心，只要里面有 `available` 就能跑。错误被拖到很远的地方才暴露。

### 问题三：行为和数据的对应关系靠人脑记

项目里有 `book`、`member`、`loan` 三种字典，每个字典有哪些键、哪些函数能操作它，全靠文档和记忆。新人接手时，第一件事是满仓库搜索 `book["`。

### 问题四：改一个字段，牵一发动全身

某天你想把 `available` 改名成 `stock`，所有读写它的函数都要改。因为数据是「裸」的，没有任何地方能统一管理它。

---

## 0.3 面向对象的核心想法

面向对象做的事情很简单：

> **把「数据」和「操作这些数据的规则」放进同一个东西里，然后让外部通过明确的接口来使用它。**

还是那本书，换一种写法：

```python
class Book:
    def __init__(self, isbn: str, title: str, available: int) -> None:
        self.isbn = isbn
        self.title = title
        self.available = available

    def checkout(self) -> None:
        if self.available <= 0:
            raise ValueError("没有库存了")
        self.available -= 1
```

现在：

- 数据（`isbn`、`title`、`available`）在对象里
- 规则（不能借负数）也在对象里
- 外部只需要说 `book.checkout()`，不需要知道内部怎么减
- 想改字段名，只改类内部，调用方不受影响

这就是最基本的心智转变：**从「传数据给函数」变成「让对象自己做事」。**

---

## 0.4 类、实例、对象，到底是什么关系

三个词经常混着说，先分清：

| 概念 | 含义 | 类比 |
| :--- | :--- | :--- |
| 类（class） | 一类事物的模板，定义有哪些属性、能做什么 | 饼干模具 |
| 实例（instance） | 根据模板创建出来的具体东西 | 用模具压出来的一块饼干 |
| 对象（object） | Python 里一切东西的统称，实例也是对象 | 「东西」这个统称 |

```python
class Book:                     # 类：模板
    def __init__(self, title: str) -> None:
        self.title = title

b1 = Book("Python 编程")         # 实例：一本具体的书
b2 = Book("算法导论")            # 另一个实例
```

`b1` 和 `b2` 都是 `Book` 的实例。它们有相同的「结构」，但属性值各自独立：

```python
print(b1.title)   # Python 编程
print(b2.title)   # 算法导论
```

改 `b1.title` 不会影响 `b2.title`，因为它们是两个不同的对象。

---

## 0.5 `self` 不是魔法

初学者最容易被 `self` 吓到。其实它只是「当前这个对象」的引用。

```python
class Book:
    def __init__(self, title: str) -> None:
        self.title = title

    def describe(self) -> str:
        return f"《{self.title}》"
```

当你写：

```python
book = Book("Python 编程")
book.describe()
```

Python 实际做的事情接近：

```python
Book.describe(book)
```

也就是说，`book.describe()` 会自动把 `book` 作为第一个参数传给方法，这个参数就是 `self`。

所以：

- `self` 不是关键字，只是一个约定俗成的参数名
- 但**不要改**，改了别人读代码会很难受
- 实例方法第一个参数必须是 `self`（名字可以换，但不建议）

---

## 0.6 四个关键词，先混个脸熟

后面每章会展开，现在只需要知道它们各自解决什么问题：

| 关键词 | 一句话解释 | 解决的问题 | 对应章节 |
| :--- | :--- | :--- | :---: |
| 封装 | 把数据和规则包在一起，只暴露必要接口 | 外部乱改数据、规则散落 | 02 |
| 继承 | 在已有类的基础上扩展 | 复用共同代码 | 03 |
| 多态 | 同一个调用，不同对象有不同行为 | 写出不依赖具体类型的代码 | 03 |
| 组合 | 一个对象持有另一个对象 | 用简单对象搭出复杂系统 | 04 |
| 抽象 | 只关心「能做什么」，不关心「怎么做」 | 降低耦合、方便替换 | 03 / 07 |

一个很重要的提醒：

> **不要为了用而用。**
>
> 如果一个问题用几个函数就能清楚解决，就不需要硬造类。面向对象的价值在于管理复杂度，而不是让代码看起来「高级」。

---

## 0.7 用「名词 + 动词」发现对象

拿到一个需求，不要急着写 `class`。先找两类词：

- **名词**：可能变成对象或属性
- **动词**：可能变成方法

以「图书借阅系统」为例：

> 图书馆里有书和会员。会员可以借书、还书。每本书有库存。借阅有期限，逾期要能查出来。

名词：

- 图书馆 → `Library`
- 书 → `Book`
- 会员 → `Member`
- 借阅记录 → `Loan`

动词：

- 借书 → `Library.borrow()` 或 `Member.borrow()`
- 还书 → `Library.return_book()`
- 查库存 → `Book.available`
- 查逾期 → `Library.overdue_loans()`

这里有一个关键设计问题：**借书这个动作，应该放在谁身上？**

- 放 `Book`：书自己不知道会员和借期，职责太重
- 放 `Member`：会员需要知道图书馆有哪些书，职责也不对
- 放 `Library`：图书馆协调书、会员、借阅记录，最自然

这个判断会贯穿整个课程：**把职责交给最了解这件事、又不需要知道太多无关信息的对象。**

---

## 0.8 本课程的项目演进

我们不会一上来就写完整系统，而是让它逐步长大：

```text
ch01   Book
ch02   Book + 库存校验
ch03   Book -> PaperBook / EBook
ch04   Member + Loan + Library
ch05   给对象加魔术方法
ch06   用 dataclass 重构模型
ch07   自定义异常 + Protocol
ch08   完整项目
ch09   测试与重构
```

每一章都会在上一步的基础上增加一点能力。你会看到「设计」不是一次完成的，而是随着需求逐渐浮现。

---

## 0.9 准备工作

确认 Python 版本：

```bash
python --version
```

需要 **3.10 或更高**。如果你看到 `3.9.x`，部分类型写法会报错，建议升级。

进入课程目录：

```bash
cd Python/oop
```

运行第一个示例（第 01 章会详细讲）：

```bash
python -m examples.ch01_book
```

如果能看到图书信息输出，环境就没问题。

---

## 0.10 本章练习

### 练习 A：找名词和动词

读下面这段需求，列出至少 4 个名词和 4 个动词：

> 一个咖啡馆有咖啡豆和杯子。店员可以制作咖啡、给咖啡定价。顾客可以下单、付款。订单里有多杯咖啡，每杯咖啡有大小和温度。

然后回答：

1. 哪些名词适合做类？
2. 哪些名词更适合做属性？
3. 「制作咖啡」应该放在哪个对象上？为什么？

### 练习 B：把函数改成对象

把下面这段过程式代码改成一个 `Counter` 类，要求外部不能直接把计数改成负数：

```python
counter = {"value": 0}

def increment(counter: dict) -> None:
    counter["value"] += 1

def decrement(counter: dict) -> None:
    if counter["value"] <= 0:
        raise ValueError("不能小于 0")
    counter["value"] -= 1
```

提示：需要 `__init__`、`increment`、`decrement`，以及一个只读的 `value` 属性。只读属性可以用 `@property` 实现，忘记的话也没关系，第 02 章会讲。

---

## 0.11 检查点

进入下一章前，试着不看笔记回答：

1. 类和实例的区别是什么？
2. `book.describe()` 和 `Book.describe(book)` 是什么关系？
```json
book.describe()        # Python 自动传入 book
Book.describe(book)    # 手动传入 book
区别：
- book.describe 是绑定方法，已经绑定 self=book；Book.describe 是普通函数。
- 普通 Book 实例下，两者输出完全一样。
- 如果 book 是子类实例，book.describe() 会优先调用子类重写的方法；Book.describe(book) 会强制调用父类 Book 的版本。
所以日常写 book.describe()，Book.describe(book) 主要用于理解 self 的机制。
```

3. 为什么「任何字典都能传给 `checkout`」是一个问题？
4. 面向对象最重要的价值是什么？
5. 为什么「借书」更适合放在 `Library` 上，而不是 `Book` 上？

如果第 1、2 题能流畅回答，就可以继续了。第 3-5 题暂时说不清也没关系，后面的章节会反复用到。

---

[下一章：类与实例 →](./01_class_and_instance.md)