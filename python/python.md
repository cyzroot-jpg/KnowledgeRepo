# Python调用C++代码
## 1. 什么是pybind11
pybind11 是一个轻量级、只包含头文件的库，用于在 C++ 和 Python 之间创建绑定。它是 C++11 标准下重写 Boost.Python 的成果，核心思想是：用现代 C++ 的模板元编程自动推导类型并生成 Python 包装代码，你只需声明"暴露什么"，不用手写引用计数和类型转换。
- 依赖：仅需 C++11 编译器 + Python 开发头文件
- 许可证：BSD
- 类型转换、异常、STL 容器、智能指针、numpy 支持大多自动完成

1. 安装
pip 安装（最快）
pip install pybind11
python -m pybind11 --includes   # 查看头文件包含路径
或通过 CMake（推荐工程化使用）
find_package(pybind11 CONFIG REQUIRED)


1. 最小示例
example.cpp:
#include <pybind11/pybind11.h>

int add(int a, int b) {
    return a + b;
}

std::string greet(const std::string& name) {
    return "Hello, " + name + "!";
}

PYBIND11_MODULE(example, m) {
    m.doc() = "pybind11 example plugin";   // 模块文档
    m.def("add", &add, "A function that adds two numbers");
    m.def("greet", &greet, "Greet someone");
}

关键点：
- 宏 PYBIND11_MODULE(模块名, 变量m) 定义入口，模块名必须与生成的 .so 文件名一致
- m.def("Python中的名字", &C++函数指针, "文档")
编译（手动）:
c++ -O3 -Wall -shared -std=c++11 -fPIC \
    $(python3 -m pybind11 --includes) \
    example.cpp -o example$(python3-config --extension-suffix)
使用:
import example
print(example.add(1, 2))       # 3
print(example.greet("World"))  # Hello, World!

3. 用 CMake 编译（推荐）
cmake_minimum_required(VERSION 3.15)
project(example)

find_package(pybind11 REQUIRED)

pybind11_add_module(example example.cpp)
pybind11_add_module 会自动处理后缀、编译选项、链接等。

4. 绑定函数的高级用法
// 默认参数
m.def("mul", &mul, py::arg("a"), py::arg("b") = 1);

// 关键字参数
m.def("fn", &fn, "doc", py::arg("x"), py::arg("y"), py::arg("z") = 0.0);

// 返回引用 / 生命周期
m.def("get_ref", &get_ref, py::return_value_policy::reference);

// lambda 直接绑定（无需独立函数）
m.def("square", [](int x) { return x * x; });

// 绑定重载函数（需显式指定类型）
m.def("over", static_cast<int(*)(int)>(&over));
m.def("over", static_cast<int(*)(int,int)>(&over));

// 异常：C++ 异常自动转成 Python 异常
// std::runtime_error -> RuntimeError, std::out_of_range -> IndexError 等
m.def("boom", []() { throw std::runtime_error("failed"); });

5. 绑定类
struct Pet {
    Pet(const std::string& name) : name_(name) {}
    void setName(const std::string& name) { name_ = name; }
    const std::string& getName() const { return name_; }
    std::string name_;
};

PYBIND11_MODULE(example, m) {
    py::class_<Pet>(m, "Pet")
        .def(py::init<const std::string&>())      // 构造函数
        .def_readwrite("name", &Pet::name_)       // 可读写属性
        .def("setName", &Pet::setName)            // 方法
        .def("getName", &Pet::getName)
        .def("__repr__", [](const Pet& p) {       // 魔术方法
            return "<Pet named '" + p.name_ + "'>";
        });
}
p = example.Pet("Milo")
p.name = "Bob"
print(p.getName())   # Bob

6. 继承与虚函数
struct Animal { virtual std::string bark() const { return "?"; } };
struct Dog : Animal { std::string bark() const override { return "woof"; } };

py::class_<Animal>(m, "Animal")
    .def(py::init<>())
    .def("bark", &Animal::bark);

// Dog 继承 Animal，并允许 Python 端重写（若需要）
py::class_<Dog, Animal>(m, "Dog")
    .def(py::init<>());

7. 自动类型转换
STL 容器（需 include 对应头文件）:
#include <pybind11/stl.h>
std::vector<int> v = {1,2,3};
m.def("list_to_vec", [](std::vector<int> v){ ... });
m.def("get_vec", []() { return std::vector<int>{1,2,3}; });
list↔vector、dict↔map、set、tuple↔pair 均自动转换。
Numpy:
#include <pybind11/numpy.h>
m.def("sum", [](py::array_t<double> arr) {
    auto r = arr.unchecked<1>();          // 无边界检查的快速访问
    double s = 0;
    for (py::ssize_t i = 0; i < r.shape(0); i++) s += r(i);
    return s;
});
零拷贝访问 numpy 内存，适合高性能数值计算。

8. 智能指针与生命周期
#include <pybind11/stl.h>
class Foo { ... };
m.def("make_foo", []() { return std::make_shared<Foo>(); });  // 自动转 Python 对象
std::shared_ptr / unique_ptr 可自动转换为 Python 的引用计数管理，避免内存泄漏。

9. 一个完整的工程示例
目录结构：
project/
├── CMakeLists.txt
├── src/math.cpp
└── python/test.py
src/math.cpp:
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;

class Calculator {
public:
    Calculator(double init = 0) : value_(init) {}
    double add(double x) { value_ += x; return value_; }
    double value() const { return value_; }
private:
    double value_;
};

PYBIND11_MODULE(mathlib, m) {
    py::class_<Calculator>(m, "Calculator")
        .def(py::init<double>(), py::arg("init") = 0)
        .def("add", &Calculator::add)
        .def_property_readonly("value", &Calculator::value);
}
CMakeLists.txt:
cmake_minimum_required(VERSION 3.15)
project(mathlib)
find_package(pybind11 REQUIRED)
pybind11_add_module(mathlib src/math.cpp)
编译与使用：
mkdir build && cd build
cmake .. -Dpybind11_DIR=$(python3 -m pybind11 --cmakedir)
make
from mathlib import Calculator
c = Calculator(10)
print(c.add(5), c.value)   # 15.0 15.0
