ATen（A Tensor library）是 PyTorch 的 C++ 张量计算核心库：它定义了 at::Tensor 和所有算子的签名与入口函数，是 torch.xxx 真正的底层实现所在。


| 层 | 存在的意义 |
|---|---|
| `torch.nn` | 让用户写模型更方便，无需关心底层实现 |
| `torch._C` | 让 Python 能够调用 C++，兼顾性能与生态 |
| ATen | 统一所有算子的规格，实现一份代码、多后端支持 |
| Dispatcher | 解耦“算子是什么”和“谁来算”，支持 CPU/CUDA/SDAA 等后端切换 |
| 厂商库 | 将 GEMM、卷积等算子优化到极致，避免重复造轮子 |
| `torch_ext.cpp` | 将自定义 Kernel 安全地接入 Python，负责类型转换等工作 |
| SDAA Runtime | 提供控制硬件的执行通道，负责显存管理、Kernel 发射与同步 |
| 硬件 | 真正执行并行计算 |


# 算子的测试
.prototxt测例的结构：