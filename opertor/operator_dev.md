# Operator

## 1. 算子开发流程
```bash
算子分析：主要是分析算子的数学计算逻辑、输入输出数据，并明确算子的实现流程。

算子实现：实现算子计算逻辑的核心步骤，包括：

    申请主机端内存，并搬运输入数据

    申请Global存储空间，并搬运输入数据（主机端至Global）

    申请SPM存储空间，并搬运输入数据（Global至SPM）到SPM进行计算，计算结果存储在SPM。

    搬运输出数据（SPM至Global）

    搬运输出数据（Global至主机端）

    算子测试

编译运行：开发完成的算子，编译运行后可以获得目标结果。
```

## 2. 调用过程
调用链：
```c++
tecoopsXxx(handle,...)             Interface 层：用户 C API，只组装参数
  → RUN_OP(XxxOp, args, patch, handle)
    → XxxOp::find()                UAL ops：按 data_type/algo 选 kernel 函数指针
    → XxxOp::run()                 UAL ops：RUN_KERNEL 启动
      → xxx.scpp __global__ kernel 设备端计算

5 个概念：handle(上下文/spe_num/stream)、SPE(计算核=threadIdx)、Args(运行数据) / PatchArgs(选分支)、kernel(.scpp)、RUN_OP/RUN_KERNEL(分发宏)。
```

开发一个新算子的 8 步（文件名必须=算子名）：
1. teco/interface/include/tecoops.h — 加 C API 声明（extern "C" 内）
```c++
#ifndef TECOOPS_INTERFACE_INCLUDE_TECOOPS_H_
#define TECOOPS_INTERFACE_INCLUDE_TECOOPS_H_

#include <sdaa_runtime.h>   // 拿到 sdaaStream_t 等 SDAA 运行时类型
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TECOOPS_DIM_MAX 8

typedef enum {
    TECOOPS_STATUS_SUCCESS = 0,
    TECOOPS_STATUS_NOT_INITIALIZED = 1,
    TECOOPS_STATUS_ALLOC_FAILED = 2,
    TECOOPS_STATUS_BAD_PARAM = 3,
    TECOOPS_STATUS_INTERNAL_ERROR = 4,
    TECOOPS_STATUS_INVALID_VALUE = 5,
    TECOOPS_STATUS_NOT_SUPPORTED = 6,
} tecoopsStatus_t;

typedef enum {
    TECOOPS_TENSOR_NCHW = 0, /* row major (wStride = 1, hStride = w) */
    TECOOPS_TENSOR_NHWC = 1, /* feature maps interleaved (cStride = 1) */
    TECOOPS_TENSOR_CHWN =
        2, /* each image point is vector of element of C, vector length in data type */
    TECOOPS_TENSOR_NWHC = 3,
    TECOOPS_TENSOR_NCDHW = 4,
    TECOOPS_TENSOR_NDHWC = 5,
    TECOOPS_TENSOR_CDHWN = 6,
} tecoopsTensorFormat_t;

typedef enum {
    TECOOPS_ALGO_0 = 0,
    TECOOPS_ALGO_1,
    TECOOPS_ALGO_2,
    TECOOPS_ALGO_3,
    TECOOPS_ALGO_4,
    TECOOPS_ALGO_5,
    TECOOPS_ALGO_6,
    TECOOPS_ALGO_7,
    TECOOPS_ALGO_8,
    TECOOPS_ALGO_9,
} tecoopsAlgo_t;

typedef enum {
    TECOOPS_DATA_FLOAT = 0,
    TECOOPS_DATA_HALF = 1,
    TECOOPS_DATA_INT8 = 2,
    TECOOPS_DATA_INT16 = 3,
    TECOOPS_DATA_INT32 = 4,
    TECOOPS_DATA_INT64 = 5,
    TECOOPS_DATA_UINT8 = 6,
    TECOOPS_DATA_BOOL = 7,
    TECOOPS_DATA_DOUBLE = 8,
    TECOOPS_DATA_BFLOAT16 = 9,
    TECOOPS_DATA_COMPLEX_FLOAT = 10,
} tecoopsDataType_t;

typedef struct tecoopsContext *tecoopsHandle_t;
typedef struct tecoopsTensorStruct *tecoopsTensorDescriptor_t;

tecoopsStatus_t tecoopsCreate(tecoopsHandle_t *handle);
tecoopsStatus_t tecoopsDestroy(tecoopsHandle_t handle);
tecoopsStatus_t tecoopsSetStream(tecoopsHandle_t handle, sdaaStream_t stream);
tecoopsStatus_t tecoopsGetStream(tecoopsHandle_t handle, sdaaStream_t *stream);
const char *tecoopsGetErrorString(tecoopsStatus_t status);

tecoopsStatus_t tecoopsCreateTensorDescriptor(tecoopsTensorDescriptor_t *tensorDesc);

tecoopsStatus_t tecoopsSetTensor4dDescriptor(tecoopsTensorDescriptor_t tensorDesc,
                                             tecoopsTensorFormat_t format,
                                             tecoopsDataType_t dataType,  // image data type
                                             int n,   // number of inputs (batch size)
                                             int c,   // number of input feature maps
                                             int h,   // height of input section
                                             int w);  // width of input section

tecoopsStatus_t tecoopsGetTensor4dDescriptor(const tecoopsTensorDescriptor_t tensorDesc,
                                             tecoopsDataType_t* dataType,  // image data type
                                             int* n,  // number of inputs (batch size)
                                             int* c,  // number of input feature maps
                                             int* h,  // height of input section
                                             int* w,  // width of input section
                                             int* nStride, int* cStride, int* hStride,
                                             int* wStride);

tecoopsStatus_t tecoopsSetTensorNdDescriptor(tecoopsTensorDescriptor_t tensorDesc,
                                             tecoopsDataType_t dataType, int nbDims,
                                             const int dimA[], const int strideA[]);

tecoopsStatus_t tecoopsGetTensorNdDescriptor(const tecoopsTensorDescriptor_t tensorDesc,
                                             int nbDimsRequested, tecoopsDataType_t* dataType,
                                             int* nbDims, int dimA[], int strideA[]);

tecoopsStatus_t tecoopsDestroyTensorDescriptor(tecoopsTensorDescriptor_t tensorDesc);

tecoopsStatus_t tecoopsFlattenRays(tecoopsHandle_t handle, const int* rays, uint32_t N, uint32_t M,
                                   int* res, tecoopsAlgo_t algo);

// z[i] = x[i] + y[i]
tecoopsStatus_t tecoopsVectorAdd(tecoopsHandle_t handle,
                                 const void* x, const void* y, void* z,
                                 int n, tecoopsDataType_t data_type,
                                 tecoopsAlgo_t algo);

#ifdef __cplusplus
}
#endif

#endif  // TECOOPS_INTERFACE_INCLUDE_TECOOPS_H_
```
> 代码解释
```json
一句话总结：#ifdef __cplusplus + extern "C" { ... } 是为了让同一个头文件的函数声明在 C 和 C++ 里符号名一致，从而都能链接到同一个实现。
核心逻辑：
- C++ 会做名称修饰（foo → _Z3foov），C 不会；不统一就链接不上。
- __cplusplus 只有 C++ 编译器才定义，C 编译器不定义。
- 于是用 #ifdef __cplusplus 把 extern "C" { 和配对的 } 包起来：
- C++ 编译：保留 → 声明按 C 符号导出。
- C 编译：整段跳过 → 只看到普通 C 声明。
记忆要点：
- { 和 } 必须各被一段 #ifdef 包住，保持括号配平。
- 常和头文件保护 #ifndef/#define/#endif 搭配使用。
- 作用对象是声明（头文件），让 C/C++ 混合编程能互相调用。



意思是：防止同一个头文件被重复地"展开"两次，导致里面的声明被重复定义而报错。
为什么会重复包含？
一个 .c/.cpp 文件常通过多层 #include 间接包含同一个头文件。例如：
a.h:  #include "common.h"
b.h:  #include "common.h"
main.c: #include "a.h"
        #include "b.h"
main.c 就会两次看到 common.h 的内容。
没有保护会怎样？
如果 common.h 里是定义（如 struct 定义、函数定义等），重复展开会导致编译错误（重定义）。
保护是怎么工作的？
#ifndef MYLIB_H      // 若 MYLIB_H 未定义
#define MYLIB_H      // 立即定义它（打个标记）
```

2. teco/ual/args/<op>_args.h — 定义 <Op>Args(POD 数据) + <Op>PatchArgs(data_type/algo)

```json
args.h 统一了"传给 kernel 的运行数据"（Args）和"决定选哪条实现的元信息"（PatchArgs），让上层调用、分支选择、底层 kernel 三方共享同一套接口定义，新增算子/新增 dtype 分支时只改这个头文件即可。

三层对应关系：
args/<op>_args.h   → 定义数据结构（Args + PatchArgs）
ops/<op>/          → findImpl 用 PatchArgs 选分支，用 Args 调 kernel
kernel/<op>/*.scpp → __global__ 函数按值收 Args，实际计算
```

3. teco/ual/kernel/<op>/<op>.h + <op>.scpp — __global__ void tecoKernel<Op>Xxx(Args arg)，threadIdx/spe_num 分核
```json
args/<op>_args.h       数据结构定义（Args / PatchArgs）
kernel/<op>/<op>.h      kernel 函数声明   ← 被 ops 层 include
kernel/<op>/<op>.scpp   kernel 函数实现   ← 真正的芯片计算代码
base_op.hpp 里通过 RUN_KERNEL 宏 func_ptr<<<1, stream_id>>>(arg) 发起执行，把 Args 按值传给 device 端。所以要新增一个 dtype 或算法分支，就是：在 .scpp 里加一个 __global__ 实现 → 在 .h 里加一行声明 → 在 ops 的 Algos[] 表里挂上函数指针。
```

4. teco/ual/ops/<op>/find_<op>.h + .cpp — find<Op>Branch() 返回 kernel 数组下标，不支持返回 -1
teco/ual/ops/<o
```json
一句话：find_<op>.h/.cpp 是"查表选实现"的胶水层——把 PatchArgs 翻译成数组下标，findImpl 再用它 setInstance 绑定真正的内核；返回 -1 即报 NOT_IMPLEMENTED，避免越界访问
```

5. teco/ual/ops/<op>/<op>.hpp — struct <Op>Op : BaseOp<...>，定义 Algos[] 函数指针数组 + Description[]，实现 findImpl
```json
一句话：<op>.hpp 定义算子对象 <Op>Op，用 Algos[]/Description[] 登记本算子所有 kernel 实现，用 findImpl 实现"按 PatchArgs 选实现"，把 UAL 三层（args / find / kernel）串成可直接 find()+run() 的调用接口。
```

6. teco/interface/ops/<op>.cpp — 组装 Args/PatchArgs，调用 RUN_OP
```json

```

7. 有额外标量参数才需要：test/test_proto/tecokernel/<op>.proto 并在 tecokernel.proto 注册
```json
一句话：interface/ops/<op>.cpp 是"用户 API ↔ UAL 内部"的适配器——定义 tecoopsXxx C 接口、校验入参、把裸参数打包成 Args/PatchArgs、做好枚举转换，最后一次 RUN_OP 触发 UAL 的 find+run。新增算子时，只要这个函数签名和枚举保持稳定，下层实现随便换都不影响用户。
```

8. Python 绑定：api/torch_ext.cpp 加 <op>_torch + m.def(...)，api/tecoops/__init__.py 导出
```json
这是最顶层的 Python 绑定层，把下面那整条 C++ 调用链（interface → ual → kernel）包装成 Python 里可以 import 直接调的算子。它由两个文件配合完成：torch_ext.cpp（C++ 侧桥接）和 __init__.py（Python 侧导出）。
```


g_handle 是一个 static 全局变量（全进程唯一），getGlobalHandle() 在首次调用时才创建它（懒创建），从而把它变成一个进程级单例——保证整个进程只创建一次运行上下文、所有算子共享复用。这本质上是 C++ 中"Meyers/函数内静态变量式单例"的手写简化版。

torch::Tensor 是 libtorch（PyTorch C++ API）中代表张量的类型，等同 Python 的 torch.Tensor；它是一个轻量句柄，内部持有数据指针、shape、dtype、device 等元信息，并支持零拷贝共享。在 torch_ext.cpp 里，它就是包装函数入参的类型——从这里用 data_ptr()、numel()、scalar_type() 把张量"拆成裸参数"喂给 C 接口。



1. Python 是怎么找模块的
import tecoops 时，Python 会按顺序在 sys.path 里找名为 tecoops 的包（目录里带 __init__.py 的文件夹，或 .so）：
sys.path = [
    '',                       # 当前运行目录
    '/usr/lib/python3.12/...',# 标准库
    .../site-packages,        # ← pip 安装的第三方包都在这
    ...
]
找到第一个匹配的就导入。所以只要 tecoops 出现在某个 sys.path 目录里，就能 import，不管它源码原来在哪个工程目录。

















UAL = 算子实现层；interface = 用户 API 入口层。两者是同一个 teco/ 目录下上下叠放的两层，interface 在上（面向用户），UAL 在下（面向芯片）。是一对"适配器 ↔ 实现"关系。





