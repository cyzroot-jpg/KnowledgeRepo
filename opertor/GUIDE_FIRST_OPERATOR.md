# 第一次做 SDAA 算子：全流程手把手指南

> 全程以一个最简单的算子 `vector_add`（`z[i] = x[i] + y[i]`）为例，
> 从零把它做出来、跑通 C++ 精度/性能测试、最后在 Python 里用起来。
>
> 跟着做一遍，能这个仓库开发算子的**完整套路**。

---

## 目录

0. [你将得到什么](#0-你将得到什么)
1. [先建立心智模型：5 个核心概念](#1-先建立心智模型5-个核心概念)
2. [环境准备与自检](#2-环境准备与自检)
3. [看懂工程结构：哪些自动化、哪些要手写](#3-看懂工程结构哪些自动化哪些要手写)
4. [Step 0：需求与设计](#step-0需求与设计)
5. [Step 1：Interface 层声明 C API](#step-1interface-层声明-c-api)
6. [Step 2：UAL 层定义参数结构体](#step-2ual-层定义参数结构体)
7. [Step 3：写设备端 kernel（.scpp）](#step-3写设备端-kernel-scpp)
8. [Step 4：分支选择 find](#step-4分支选择-find)
9. [Step 5：Op 类](#step-5op-类)
10. [Step 6：Interface 层实现与 RUN_OP](#step-6interface-层实现与-run_op)
11. [Step 7：测试 Executor](#step-7测试-executor)
12. [Step 8：测试用例 prototxt](#step-8测试用例-prototxt)
13. [Step 9：构建并跑通 C++ 测试](#step-9构建并跑通-c-测试)
14. [Step 10：Python 绑定](#step-10python-绑定)
15. [Step 11：Python 端使用与自测](#step-11python-端使用与自测)
16. [常见报错与排错手册](#16-常见报错与排错手册)
17. [新算子 Checklist（照抄即可）](#17-新算子-checklist照抄即可)
18. [下一步：性能优化](#18-下一步性能优化)

---

## 0. 你将得到什么

做完本指南后，你会拥有：

- 一个能正确计算的 `vector_add` 算子，覆盖 interface + ual 全部 7 个文件；
- 3 个 C++ 测试用例（n = 16 / 1024 / 1048576），输出 `ALL PASSED`；
- 一个性能数据（硬件时间、带宽）；
- 一个 Python 接口 `tecoops.vector_add`，可在真机 `sdaa` 设备上调用；
- 一套**可复制到任何新算子**的流程和排错经验。

---

## 1. 先建立心智模型：5 个核心概念

在看代码之前，先理解这 5 个词，后面就不会迷路。

| 概念 | 一句话解释 |
|---|---|
| **handle** | 算子执行的“上下文/句柄”，记录 `spe_num`（用几个计算核）、`stream`（哪个流）。用 `tecoopsCreate` 创建，全局复用即可。 |
| **SPE** | SDAA 上的计算核心（类似 CUDA 的 thread/block 概念）。kernel 里用 `threadIdx` 表示当前是第几个核，`spe_num` 是总数。 |
| **Args / PatchArgs** | 两类参数：`Args` = kernel 真正需要的数据（指针、size、spe_num）；`PatchArgs` = 用来“选分支”的参数（`data_type` + `algo`）。 |
| **kernel** | 真正跑在设备端的计算函数，写在 `.scpp` 文件里，带 `__global__`，通过 `<<<1, spe_num>>>` 启动。 |
| **RUN_OP / RUN_KERNEL** | 分发宏。`RUN_OP` 在 interface 层用（先 `find` 选分支，再 `run`）；`RUN_KERNEL` 在 ual 层用（真正启动 kernel）。 |

### 调用链（背下来）

```
tecoopsVectorAdd(handle, ...)        ← Interface 层：用户 C API
  → 组装 VectorAddArgs + VectorAddPatchArgs
  → RUN_OP(VectorAddOp, args, patch_args, handle)
      → VectorAddOp::find()          ← UAL ops：按 data_type/algo 选 kernel 函数指针
      → VectorAddOp::run()           ← UAL ops：调用选中的 kernel
          → RUN_KERNEL(kernel, stream, args)
              → tecoKernelVectorAddFloat(args)   ← UAL kernel：设备端计算
```

Python 侧再多一层：`tecoops.vector_add(...)` → `api/torch_ext.cpp` 里的 `vector_add_torch()` → 上面这条链。

---

## 2. 环境准备与自检

### 2.1 确认硬件与驱动

```bash
teco-smi
```

能看到设备（`TECO_AICARD_...`、`Health OK`）即可。拿不到设备时后续测试都会失败。

### 2.2 确认工具链

```bash
which tecocc          # SDAA C 编译器，必须存在
ls /opt/tecoai        # SDK 根目录
echo $SDAA_HOME       # 通常为 /opt/tecoai
```

### 2.3 确认 Python 侧

```bash
python3 -c "import torch, torch_sdaa; print(torch.__version__)"
```

### 2.4 准备第三方依赖并 source 环境

仓库根目录下：

```bash
cd teco-ops-yaoyaolingxian
source env.sh          # 设置 TECO_READY_TO_BUILD=ON
bash build.sh --build teco   # 会自动拉取 teco-hal 并编译算子库
```

> `build.sh` 会调用 `tools/deps.py` 下载 `thirdparty/teco-hal`。
> 若内网不可达，可从其它已有副本拷贝 `thirdparty/teco-hal` 过来（该目录已被 `.gitignore`）。

构建成功后产物在 `build/teco/lib/libteco_ops.so`。

---

## 3. 看懂工程结构：哪些自动化、哪些要手写

这是新手最容易踩坑的地方：**不是所有文件都要你手动登记**。

### 3.1 自动发现（不用手改）

- `teco/CMakeLists.txt` 用 `file(GLOB_RECURSE ...)` 收集：
  - `teco/interface/common/*.cpp`
  - `teco/interface/ops/*.cpp`
  - `teco/ual/com/*.cpp`
  - `teco/ual/ops/*/*.cpp`
  - `teco/ual/kernel/*/*.scpp`
  - → 你只要**新建文件**，下次 cmake 就会自动带上。
- 测试框架 `test/CMakeLists.txt` 调用 `test/tools/register_op.py`，
  它扫描 `test/zoo/teco/<op>/` 目录，自动生成：
  - `test/src/suite/case_list.cpp`
  - `test/src/suite/op_register.h`
  - `test/src/suite/op_register.cpp`
  - → 你只要建好 `zoo/teco/<op>/` 目录，注册代码自动生成，**不要手改这三个文件**。

### 3.2 需要手动登记的地方（只有 3 处）

1. `teco/interface/include/tecoops.h` —— 加 C API 声明（Step 1）
2. `api/torch_ext.cpp` + `api/tecoops/__init__.py` —— 加 Python 绑定（Step 10）
3. 若算子有额外标量参数：`test/test_proto/tecokernel/<op>.proto` + 在 `tecokernel.proto` 注册

### 3.3 命名铁律

- 目录名、文件名、算子名**必须一致**（`vector_add` 全用 `vector_add`）。
- 这是构建脚本索引的依据，写错就会出现“文件没被编译”“找不到 executor”等问题。

---

## Step 0：需求与设计

### 0.1 一句话写清需求

先明确 4 件事（`vector_add` 的例子）：

| 项 | 内容 |
|---|---|
| 算子名 | `vector_add` |
| 计算 | `z[i] = x[i] + y[i]` |
| 输入 | `x[N]`、`y[N]`，float32，一维连续 |
| 输出 | `z[N]`，float32 |

> 任何新算子都先写清这 4 条。功能不明确时就别动手写代码。

### 0.2 写设计文档（推荐，非强制）

在 `doc/op_docs/` 下新建 `<op>.md`，可参考 `doc/op_docs/doc_template.md`。
本指南的成品见 `doc/op_docs/vector_add.md`，里面包含：
计算原理、接口设计、参数表、类型限制、性能优化方向、分支派发表、文件结构、使用示例。

> 设计文档的好处：写代码前先把接口和分支想清楚，后面照抄实现即可。

### 0.3 先决定“分支维度”

一个算子往往要支持多 dtype / 多算法。你需要在设计阶段就想好：
- 支持哪些 `data_type`？（`vector_add` 先只做 `float32`）
- 有哪些 `algo`？（`vector_add` 先只做 `ALGO_0` 基础版）

|含义|	回答的问题|	取值|
|---|---|---|
|data_type|	数据的元素类型	“算的是 float 还是 half/int32？”	|TECOOPS_DATA_FLOAT / HALF / INT32 …
|algo|	同一算子的实现算法/优化版本	“用基础版还是优化版？”	|TECOOPS_ALGO_0 … ALGO_9|
---
`find` 函数就是按这两个维度返回 kernel 下标的。

> handle = 一个含 spe_num、spm_size、stream（以及预留的 spa_num）的执行上下文

| 字段         | 初始值       | 含义                    | 当前是否被算子用到                                           |
| ---------- | --------- | --------------------- | --------------------------------------------------- |
| `spa_num`  | `1`       | 推测为设备/分组数             | ❌ 只在创建时赋值，算子逻辑未读取                                   |
| `spe_num`  | `32`      | 参与计算的 SPE 核数          | ✅ `arg.spe_num = handle->spe_num`，kernel 据此分核       |
| `spm_size` | `256KB`   | 可供算子使用的 SPM（片上共享内存）预算 | ❌ 只在创建时赋值，目前未读取（kernel 中另有 `SPM_MAX_BYTE = 220KB`）  |
| `stream`   | `nullptr` | 执行流，kernel 在该流上启动     | ✅ `RUN_OP` 中通过 `impl.run(&args, handle->stream)` 传入 |

使用上的几个要点
- 生命周期：整个进程创建一个即可。Python 绑定里用 getGlobalHandle() 懒加载、全局复用（api/torch_ext.cpp）。
- 核数：所有算子的 arg.spe_num 都来自 handle->spe_num，改这一个值就能统一改分核数。
- stream：默认 nullptr（默认流）；需要和 torch 的流对齐时用 tecoopsSetStream。
- 目前 spa_num / spm_size 是预留字段，简单算子用不到；写复杂算子要做 SPM 规划时才会去读 spm_size。


## Step 1：Interface 层声明 C API

**文件**：`teco/interface/include/tecoops.h`

在 `tecoopsFlattenRays` 声明之后加上：

```c++
// z[i] = x[i] + y[i]
tecoopsStatus_t tecoopsVectorAdd(tecoopsHandle_t handle, # 必写的，提供算子需要的上下文
                                 const void* x, const void* y, void* z,
                                 int n, tecoopsDataType_t data_type,
                                 tecoopsAlgo_t algo);
```

**逐项解释：**

- 返回值统一用 `tecoopsStatus_t`（`TECOOPS_STATUS_SUCCESS` / `NOT_INITIALIZED` 等）。
- 数据指针统一用 `void*`（因为接口层不关心 dtype，dtype 交给分支选择）。
- 额外带 `data_type` 和 `algo` 两个参数，供 `find` 选分支用。
- 若算子需要标量（如 `alpha`），在这里再加一个形参即可。
- n 是 vector_add 的元素个数（向量的长度）——告诉算子这次要加多少个元素。
> 一定放在 `extern "C" { ... }` 块里（文件已有），保证 C ABI。

---

## Step 2：UAL 层定义参数结构体

**文件**：`teco/ual/args/vector_add_args.h`（新建）

```c++
#ifndef TECO_UAL_ARGS_VECTOR_ADD_ARGS_H_
#define TECO_UAL_ARGS_VECTOR_ADD_ARGS_H_

#include "ual/com/def.h"

namespace tecoops {
namespace ual {
namespace args {

// 运行参数：kernel 执行实际计算所需的数据
struct VectorAddArgs {
    int spe_num;      // 参与计算的 SPE 核数
    const void* x;    // 输入 x 首地址
    const void* y;    // 输入 y 首地址
    void* z;          // 输出 z 首地址
    int n;            // 元素个数
};

// 分支参数：用于在 UAL ops 层选择具体 kernel 实现
struct VectorAddPatchArgs {
    VectorAddArgs* atargs;
    common::UALDataType data_type;
    common::UALAlgoType algo;
};

}  // namespace args
}  // namespace ual
}  // namespace tecoops

#endif  // TECO_UAL_ARGS_VECTOR_ADD_ARGS_H_
```

**要点：**

- `VectorAddArgs` 是**从主机端传到设备端**的结构体，字段只能是 POD（指针、整数）。
  设备 kernel 直接读它。
- `atargs` 指向 `Args`，`find` 有时需要从 Args 里取信息（本算子不需要，但这是惯例）。
- `data_type`/`algo` 用 `ual/com/def.h` 里的枚举，不要用 tecoops 的枚举（那是 interface 层用的，
  中间由 `Convert` 转换）。
- include guard、namespace 层级照抄，别改。

---

## Step 3：写设备端 kernel（.scpp）

### 3.1 kernel 声明头

**文件**：`teco/ual/kernel/vector_add/vector_add.h`（新建）

```c++
#ifndef TECO_UAL_KERNEL_VECTOR_ADD_VECTOR_ADD_H_
#define TECO_UAL_KERNEL_VECTOR_ADD_VECTOR_ADD_H_

#include "ual/args/vector_add_args.h"

using tecoops::ual::args::VectorAddArgs;

__global__ void tecoKernelVectorAddFloat(VectorAddArgs arg);

#endif  // TECO_UAL_KERNEL_VECTOR_ADD_VECTOR_ADD_H_
```

### 3.2 kernel 实现

**文件**：`teco/ual/kernel/vector_add/vector_add.scpp`（新建）

```c++
#include "ual/kernel/vector_add/vector_add.h"
#include "ual/kernel/macro.h"

using namespace tecoops::ual::args;

// 极简版本：每个 SPE 处理一段连续区间，直接读写全局内存。
// z[i] = x[i] + y[i]
__global__ void tecoKernelVectorAddFloat(VectorAddArgs arg) {
    const float* x = static_cast<const float*>(arg.x);
    const float* y = static_cast<const float*>(arg.y);
    float* z = static_cast<float*>(arg.z);
    int n = arg.n;
    int spe_num = arg.spe_num;

    // 把 n 个元素按 SPE 数均分，每个 SPE 负责 [start, end)
    size_t per_spe = (static_cast<size_t>(n) + spe_num - 1) / spe_num;
    size_t start = static_cast<size_t>(threadIdx) * per_spe;
    size_t end = MIN(start + per_spe, static_cast<size_t>(n));

    for (size_t i = start; i < end; ++i) {
        z[i] = x[i] + y[i];
    }
}
```

**逐行要点（新手必读）：**

- `.scpp` 是 SDAA C 源文件，编译选项里带 `-x sdaa`，所以能用 `__global__`、`threadIdx` 等。
- `#include "ual/kernel/macro.h"` 提供 `MIN/MAX`、`SPM_MAX_BYTE` 等，并且里面有
  `using namespace sdaa;`，所以能直接写 `threadIdx`。
- kernel 参数**只能是一个 `Args` 结构体**（框架用 `kernel<<<1, spe_num>>>(arg)` 启动它）。
  这是本仓库的固定约定。
- `threadIdx` 是当前 SPE 编号，范围 `[0, spe_num)`；`spe_num` 来自 handle（默认 32）。
- **均分策略**：`per_spe = ceil(n / spe_num)`，`start = threadIdx * per_spe`。
  注意用 `size_t` 计算，避免 `n` 很大时 `int * per_spe` 溢出。
- `MIN` 用来处理最后一个 SPE 越界（tail）。
- 这个版本是**性能基线**：每核直接读全局内存，没有 SPM/DMA/SIMD。后面再优化。

> ⚠️ 编译器带 `-Werror`，任何 warning 都会被当成错误。类型转换要显式 `static_cast`。

---

## Step 4：分支选择 find

### 4.1 声明

**文件**：`teco/ual/ops/vector_add/find_vector_add.h`（新建）

```c++
#ifndef TECOOPS_UAL_OPS_VECTOR_ADD_FIND_VECTOR_ADD_H_
#define TECOOPS_UAL_OPS_VECTOR_ADD_FIND_VECTOR_ADD_H_

#include "ual/args/vector_add_args.h"

using tecoops::ual::args::VectorAddPatchArgs;

namespace tecoops {
namespace ual {
namespace ops {

// 返回 kernel 在 Algos 数组中的下标；-1 表示无匹配分支
int findVectorAddBranch(const VectorAddPatchArgs *arg);

}  // namespace ops
}  // namespace ual
}  // namespace tecoops

#endif  // TECOOPS_UAL_OPS_VECTOR_ADD_FIND_VECTOR_ADD_H_
```

### 4.2 实现

**文件**：`teco/ual/ops/vector_add/find_vector_add.cpp`（新建）

```c++
#include "ual/ops/vector_add/find_vector_add.h"
#include "ual/com/convert.hpp"

using tecoops::ual::args::VectorAddPatchArgs;

namespace tecoops {
namespace ual {
namespace ops {

int findVectorAddBranch(const VectorAddPatchArgs *arg) {
    // algo 直接作为 kernel 下标（ALGO_0 -> 0）
    int algo = common::convertAlgoToIndex(arg->algo);
    // 目前只支持 float32
    if (arg->data_type == common::UALDataType::UAL_DTYPE_FLOAT) {
        return algo;
    }
    return -1;
}

}  // namespace ops
}  // namespace ual
}  // namespace tecoops
```

**要点：**

- 返回值是 `algo` 的整数值，直接当作 kernel 数组下标。所以 `ALGO_0 → 0` 对应
  `VectorAddAlgos[0]`。
- 不支持的类型返回 `-1`，上层会报 `NOT_IMPLEMENTED`（这是设计，不是 bug）。
- 想加 half 支持时：在 Step 5 的数组里追加 `tecoKernelVectorAddHalf`，
  并在这里 `if (data_type == UAL_DTYPE_HALF) return 1;`（假设放在下标 1）。

---

## Step 5：Op 类

**文件**：`teco/ual/ops/vector_add/vector_add.hpp`（新建）

```c++
#ifndef TECOOPS_UAL_OPS_VECTOR_ADD_VECTOR_ADD_HPP_
#define TECOOPS_UAL_OPS_VECTOR_ADD_VECTOR_ADD_HPP_

#include "ual/kernel/vector_add/vector_add.h"
#include "ual/com/log.h"
#include "ual/args/vector_add_args.h"
#include "ual/com/def.h"
#include "ual/ops/base_op.hpp"
#include "ual/ops/vector_add/find_vector_add.h"

using tecoops::ual::args::VectorAddArgs;
using tecoops::ual::args::VectorAddPatchArgs;
using namespace tecoops::ual::common;

namespace tecoops {
namespace ual {
namespace ops {

struct VectorAddType {
    using ArgsType = VectorAddArgs;
    using PatchType = VectorAddPatchArgs;
    using RetType = void;
    using PImplType = void (*)(ArgsType);
};

// 各 dtype 对应的 kernel 实现入口
static VectorAddType::PImplType VectorAddAlgos[] = {
    tecoKernelVectorAddFloat,
};

static const char *VectorAddDiscription[] = {
    "tecoKernelVectorAddFloat",
};

struct VectorAddOp : public BaseOp<VectorAddOp, VectorAddType> {
 public:
    using ArgsType = typename VectorAddType::ArgsType;
    using PatchType = typename VectorAddType::PatchType;
    using RetType = typename VectorAddType::RetType;
    using PImplType = typename VectorAddType::PImplType;

    static const char *name() { return "vector_add"; }

    common::Status findImpl(const PatchType *args) {
        int index = findVectorAddBranch(args);
        if (index == -1) {
            ERROR("vector_add branch is not exit!");
            return common::Status::NOT_IMPLEMENTED;
        }
        setInstance(VectorAddAlgos[index], VectorAddDiscription[index]);
        return common::Status::SUCCESS;
    }
};

}  // namespace ops
}  // namespace ual
}  // namespace tecoops

#endif  // TECOOPS_UAL_OPS_VECTOR_ADD_VECTOR_ADD_HPP_
```

**要点：**

- `VectorAddAlgos[]` 是 **kernel 函数指针数组**，`find` 返回的下标就是它的下标。
  多个 dtype/算法就在这里并列添加。
- `VectorAddDiscription[]` 是给日志用的名字，长度要和 `Algos` 一一对应。
- `findImpl` 是框架通过 `BaseOp::find()` 回调的钩子；你只实现它。
- 不要自己实现 `find/run`，那是 `BaseOp` 提供的（`run` 内部就是 `RUN_KERNEL`）。

---

## Step 6：Interface 层实现与 RUN_OP

**文件**：`teco/interface/ops/vector_add.cpp`（新建）

```c++
#include "ual/ops/vector_add/vector_add.hpp"

#include "interface/common/convert.h"
#include "interface/common/macro.h"
#include "interface/include/builtin_type.h"
#include "interface/include/tecoops.h"
#include "ual/args/vector_add_args.h"

using tecoops::Convert;
using tecoops::ual::args::VectorAddArgs;
using tecoops::ual::args::VectorAddPatchArgs;
using tecoops::ual::ops::VectorAddOp;

tecoopsStatus_t tecoopsVectorAdd(tecoopsHandle_t handle, const void* x, const void* y, void* z,
                                 int n, tecoopsDataType_t data_type, tecoopsAlgo_t algo) {
    if (handle == nullptr) {
        return TECOOPS_STATUS_NOT_INITIALIZED;
    }

    VectorAddArgs arg;
    arg.spe_num = handle->spe_num;
    arg.x = x;
    arg.y = y;
    arg.z = z;
    arg.n = n;

    VectorAddPatchArgs patch_arg;
    patch_arg.atargs = &arg;
    patch_arg.data_type = Convert::toUALDataType(data_type);
    patch_arg.algo = Convert::toUALAlgoType(algo);

    RUN_OP(VectorAddOp, arg, patch_arg, handle);

    return TECOOPS_STATUS_SUCCESS;
}
```

**要点：**

- 函数名必须与 Step 1 头文件里的声明**完全一致**。
- `arg.spe_num = handle->spe_num`：核数从 handle 拿，不要写死。
- `data_type`/`algo` 从 tecoops 枚举转成 ual 枚举（`Convert::toUALDataType` / `toUALAlgoType`）。
- `RUN_OP` 展开后就是：构造 `VectorAddOp` → `find(&patch_arg)` → 失败抛错 → `run(&arg, handle->stream)`。
- interface 层**不做计算、不做分支判断**，只做“组装参数 + 分发”。

---

## Step 7：测试 Executor

测试框架用一个 `Executor` 子类描述“怎么跑这个算子、正确的参考结果是什么”。

### 7.1 头文件

**文件**：`test/zoo/teco/vector_add/vector_add.h`（新建）

```c++
#ifndef ZOO_TECO_VECTOR_ADD_VECTOR_ADD_H_  // NOLINT
#define ZOO_TECO_VECTOR_ADD_VECTOR_ADD_H_

#include "zoo/teco/executor.h"

namespace optest {
class VectorAddExecutor : public TecoExecutor {
 public:
    VectorAddExecutor() {}
    ~VectorAddExecutor() {}

    void paramCheck();
    void paramParse();
    void paramGeneration();
    void compute();
    void cpuCompute();
    void gpuCompute();
    int64_t getTheoryOps() override;
    int64_t getTheoryIoSize() override;
    void destroy();

 private:
    void *x_, *y_, *z_;
    uint32_t n_;
};

}  // namespace optest

#endif  // ZOO_TECO_VECTOR_ADD_VECTOR_ADD_H_
```

### 7.2 实现

**文件**：`test/zoo/teco/vector_add/vector_add.cpp`（新建）

```c++
#include <stdio.h>
#include <iostream>
#include <string>
#include <tensor.h>

#include "zoo/teco/convert.h"
#include "common/time.hpp"
#include "zoo/teco/vector_add/vector_add.h"
#include "interface/include/tecoops.h"

namespace optest {

void VectorAddExecutor::destroy() {}

void VectorAddExecutor::paramCheck() {}

void VectorAddExecutor::paramParse() {
    // x/y/z 均为 1D，元素个数相同
    n_ = parser_->inputs()[0].shape[0];
}

void VectorAddExecutor::paramGeneration() {
    x_ = dev_input[0];
    y_ = dev_input[1];
    z_ = dev_output[0];
}

void VectorAddExecutor::compute() {
#ifdef USE_TECO
    checkTECOOPS(tecoopsVectorAdd(handle_, x_, y_, z_, n_, TECOOPS_DATA_FLOAT, TECOOPS_ALGO_0));
#endif
}

int64_t VectorAddExecutor::getTheoryOps() {
    return static_cast<int64_t>(n_);
}

int64_t VectorAddExecutor::getTheoryIoSize() {
    return static_cast<int64_t>(n_) * 3 * sizeof(float);
}

void VectorAddExecutor::cpuCompute() {
    auto* x_ptr = static_cast<float*>(baseline_input[0]);
    auto* y_ptr = static_cast<float*>(baseline_input[1]);
    auto* z_ptr = static_cast<float*>(baseline_output[0]);

    for (uint32_t i = 0; i < n_; ++i) {
        z_ptr[i] = x_ptr[i] + y_ptr[i];
    }
}

void VectorAddExecutor::gpuCompute() {}

}  // namespace optest
```

**每个方法的作用：**

| 方法 | 作用 | vector_add 里怎么写 |
|---|---|---|
| `paramParse()` | 从 prototxt 解析 shape/参数 | 取第 0 个输入的 `shape[0]` 当 `n_` |
| `paramGeneration()` | 绑定设备端输入/输出指针 | `dev_input[0/1]`、`dev_output[0]` |
| `compute()` | 调用**被测算子** | `checkTECOOPS(tecoopsVectorAdd(...))` |
| `cpuCompute()` | **CPU 参考实现**（golden） | 逐元素相加，写到 `baseline_output[0]` |
| `gpuCompute()` | CUDA 对照（本仓库不用） | 留空 |
| `getTheoryOps/IoSize` | 性能报告的“理论值” | 加法 1 op/元素；IO = 3×n×4 字节 |

**关键点：**

- `handle_`、`dev_input`、`dev_output`、`baseline_input`、`baseline_output`、`parser_`
  都是基类 `TecoExecutor`/`Executor` 提供的，直接用。
- `baseline_input` 是框架按 prototxt 生成的输入数据；`cpuCompute` 把参考结果写到
  `baseline_output`，框架会自动和 `compute()` 的设备结果比对。
- `checkTECOOPS` 是 `zoo/teco/executor.h` 里的宏，检查返回值并打印错误。
- 只有 `USE_TECO` 宏下才调设备算子。

---

## Step 8：测试用例 prototxt

**文件**：`test/zoo/teco/vector_add/test_case/0.prototxt`（新建，可建多个）

```protobuf
op_name: "vector_add"

input {
  id: "x"
  shape {
    dims: 16
  }
  layout: LAYOUT_ARRAY
  dtype: DTYPE_FLOAT
  random_data {
    seed: 12345
    lower_bound: -1
    upper_bound: 1
    distribution: UNIFORM
  }
  ttype: TENSOR
}

input {
  id: "y"
  shape {
    dims: 16
  }
  layout: LAYOUT_ARRAY
  dtype: DTYPE_FLOAT
  random_data {
    seed: 54321
    lower_bound: -1
    upper_bound: 1
    distribution: UNIFORM
  }
  ttype: TENSOR
}

output {
  id: "z"
  shape {
    dims: 16
  }
  layout: LAYOUT_ARRAY
  dtype: DTYPE_FLOAT
  ttype: TENSOR
}
```

**字段解释：**

| 字段 | 含义 |
|---|---|
| `op_name` | 必须与目录名/算子名一致 |
| `input` / `output` | 声明的顺序对应 `dev_input[0/1]`、`dev_output[0]` |
| `shape.dims` | 维度。一维就写一个 `dims`；二维写多个 |
| `layout` | 一维用 `LAYOUT_ARRAY` |
| `dtype` | `DTYPE_FLOAT` 等，见 `test_proto/tensor.proto` |
| `random_data` | 框架按此生成随机输入（也可用 `prev_value` 指定固定值） |
| `ttype` | `TENSOR` |

**重要：** 框架**不会自动推断输出 shape**，输出张量必须在 prototxt 里显式声明
（`vector_add` 的输出 `z` 和输入同长，就写同样的 `dims`）。

建议至少建 3 个 case 覆盖不同规模（如 n=16 / 1024 / 1048576），
分别命名 `0.prototxt`、`1.prototxt`、`2.prototxt`，放在 `test_case/` 下。

> 何时需要额外 proto？当算子有标量参数（如 `alpha`/`beta`/`eps`）时，
> 需要 `test/test_proto/tecokernel/<op>.proto` 定义 `XxxParam`，
> 并在 `test/test_proto/tecokernel.proto` 里 import 且给 `TecokernelParam` 加字段；
> Executor 里用 `parser_->getProtoNode()->tecokernel_param().xxx_param()` 读取。
> `vector_add` 没有额外参数，所以**不需要** proto。

---

## Step 9：构建并跑通 C++ 测试

### 9.1 构建

```bash
# 仓库根目录
source env.sh
bash build.sh --build teco

# 测试目录
cd test
source env.sh
sh build.sh --arch teco
```

构建过程中 `register_op.py` 会自动把 `zoo/teco/vector_add/` 注册进去。
若没看到 vector_add 相关的 `.cpp` 被编译，检查目录名是否与算子名一致。

### 9.2 运行

```bash
# 全部算子
./build/demo --gid=0

# 只跑 vector_add 的某个用例（开发时最常用）
./build/demo --gid=0 --case_path=zoo/teco/vector_add/test_case/0.prototxt

# 带性能采集
./build/demo --gid=0 --perf_repeat=50 --warm_repeat=3 --gtest_repeat=1 \
  --case_path=zoo/teco/vector_add/test_case/2.prototxt
```

### 9.3 看结果

精度：输出结尾出现

```
[ SUMMARY  ] Total N cases of 1 op(s).
ALL PASSED.
```

性能：关注

```
[Average Hardware Time  ]: 13.145 (ms)
[Average IoBandWidth    ]: 0.95722 (GB/s)
```

`max_error: 0.00000e+00`、`error_num: 0` 表示和 CPU 参考完全一致。

**判定标准：`ALL PASSED` 才算精度通过。** 不通过时先查 `cpuCompute` 和 kernel 的索引逻辑。

---

## Step 10：Python 绑定

C++ 测试通过后，把算子暴露给 Python。

### 10.1 加包装函数

**文件**：`api/torch_ext.cpp`

先加一个 dtype 映射（torch 类型 → tecoops 类型），再写包装：

```c++
static tecoopsDataType_t toTecoopsDtype(const torch::Tensor &t) {
    switch (t.scalar_type()) {
        case torch::kFloat32:
            return TECOOPS_DATA_FLOAT;
        case torch::kFloat16:
            return TECOOPS_DATA_HALF;
        case torch::kInt32:
            return TECOOPS_DATA_INT32;
        default:
            TORCH_CHECK(false, "vector_add: unsupported dtype");
    }
}

void vector_add_torch(torch::Tensor x, torch::Tensor y, torch::Tensor z) {
    tecoopsHandle_t handle = getGlobalHandle();
    int n = static_cast<int>(x.numel());
    tecoopsVectorAdd(handle,
                     x.data_ptr(), y.data_ptr(), z.data_ptr(),
                     n, toTecoopsDtype(x),
                     TECOOPS_ALGO_0);
}
```

**要点：**

- `getGlobalHandle()` 是文件顶部的懒加载句柄，直接用，不要每个算子自己 create。
- `data_ptr()` 不带模板参数时返回 `void*`，正好对上 C API。
- `TORCH_CHECK` 在非法输入时报错，比静默错误好。
- **dtype 支持范围由 kernel 决定**：这里映射了 half/int32，但目前只有 float kernel，
  传 half 会走到 `find` 返回 -1 并报 `NOT_IMPLEMENTED`。

### 10.2 注册

同文件底部 `PYBIND11_MODULE(_torch_ext, m)` 里加一行：

```c++
m.def("vector_add", &vector_add_torch, "vector_add (SDAA)");
```

### 10.3 导出到 Python 包

**文件**：`api/tecoops/__init__.py`

```python
import torch

from ._torch_ext import flatten_rays, vector_add

__all__ = ['flatten_rays', 'vector_add']
```

### 10.4 构建

```bash
# 仓库根目录
python3 setup.py build_ext --inplace
```

该命令会：
1. 用 CMake 重新构建 `libteco_ops.so`（这次带上 torch 链接标志）；
2. 编译 `api/torch_ext.cpp` → `api/tecoops/_torch_ext.*.so`；
3. 把 `libteco_ops.so` 拷到 `api/tecoops/`。

---

## Step 11：Python 端使用与自测

### 11.1 写测试脚本

**文件**：`python_api_test/test_vector_add.py`（新建）

```python
#!/usr/bin/env python3
import torch
import torch_sdaa
import _bootstrap
import tecoops
import numpy as np


def test_vector_add(sizes=(16, 1024, 4096)):
    all_passed = True
    for n in sizes:
        x = torch.rand(n, dtype=torch.float32)
        y = torch.rand(n, dtype=torch.float32)
        ref = x + y

        x_sdaa = x.to('sdaa')
        y_sdaa = y.to('sdaa')
        z_sdaa = torch.empty(n, dtype=torch.float32, device='sdaa')

        tecoops.vector_add(x_sdaa, y_sdaa, z_sdaa)
        result = z_sdaa.cpu()

        ok = torch.allclose(ref, result, rtol=1e-5, atol=1e-5)
        print(f"  size {n:5d}: {'PASSED' if ok else 'FAILED'}")
        all_passed = all_passed and ok
    return all_passed


if __name__ == "__main__":
    if not torch.sdaa.is_available():
        print("Warning: SDAA is not available, tests may fail")
    passed = test_vector_add()
    print("All tests PASSED!" if passed else "Some tests FAILED!")
```

> `import _bootstrap` 会把仓库内 `api/` 放到 `sys.path` 最前，
> 保证用的是你刚编译的本地扩展，而不是环境里可能存在的旧 `tecoops`。

### 11.2 运行

```bash
python3 python_api_test/test_vector_add.py
```

预期：

```
  size    16: PASSED
  size  1024: PASSED
  size  4096: PASSED
All tests PASSED!
```

### 11.3 直接在 Python 里用

```python
import torch
import tecoops

n = 1024
x = torch.rand(n, dtype=torch.float32, device='sdaa')
y = torch.rand(n, dtype=torch.float32, device='sdaa')
z = torch.empty(n, dtype=torch.float32, device='sdaa')

tecoops.vector_add(x, y, z)
print(torch.allclose(z.cpu(), (x + y).cpu()))   # True
```

> 记得先 `import torch`（加载 libtorch）再 `import tecoops`。

---

## 16. 常见报错与排错手册

| 现象 | 原因 | 解决 |
|---|---|---|
| `tecoopsXxx` 未定义 / 链接错误 | 接口实现没被编译 | 检查文件名=算子名；重新 `bash build.sh --build teco`（globbing 需要重新 cmake，build.sh 会重来） |
| demo 里找不到 `vector_add` executor | `zoo/teco/vector_add/` 目录名或类名不符 | 目录名、文件名、类名 `<Op>Executor` 三者要对应；重新 `sh build.sh --arch teco` |
| `my_op branch is not exit!` / `NOT_IMPLEMENTED` | `find` 返回 -1（dtype/algo 不匹配） | 检查传入的 `data_type`；确认 `Algos[]` 下标与 `find` 返回值一致 |
| kernel 编译报 warning 变 error | CMake 带 `-Werror` | 显式 `static_cast`，消除所有 warning |
| 结果全 0 / 只对一段 | kernel 索引或 tail 逻辑错 | 检查 `start/end`、`MIN` 边界；用 n=16 的小 case 先调 |
| 精度不一致 (`error_num > 0`) | CPU 参考实现与 kernel 语义不一致 | 对照 `cpuCompute` 与 kernel 逐元素逻辑 |
| `libtorch.so: cannot open shared object file` | 跑过 `setup.py` 后 `libteco_ops.so` 被链接上 torch | 给 demo 前加 `LD_LIBRARY_PATH=<torch/lib>`，或重新 `bash build.sh --build teco` |
| Python `module 'tecoops' has no attribute 'xxx'` | 用到了环境里旧的已安装 tecoops | 确认 `_bootstrap.py` 存在并 `import _bootstrap`；或 `pip uninstall tecoops` |
| `Failed to import torch/torch_sdaa` | 未装 torch-sdaa | `pip install torch torch-sdaa` |

---

## 17. 新算子 Checklist（照抄即可）

复制下面这份清单，做新算子时逐项打勾：

```
[ ] Step 0  需求 4 要素写清；可选：doc/op_docs/<op>.md 设计文档
[ ] Step 1  teco/interface/include/tecoops.h           声明 tecoops<Op>
[ ] Step 2  teco/ual/args/<op>_args.h                  <Op>Args + <Op>PatchArgs
[ ] Step 3  teco/ual/kernel/<op>/<op>.h                kernel 声明
            teco/ual/kernel/<op>/<op>.scpp             kernel 实现（__global__）
[ ] Step 4  teco/ual/ops/<op>/find_<op>.h              find 声明
            teco/ual/ops/<op>/find_<op>.cpp            find 实现（按 dtype/algo 返回下标）
[ ] Step 5  teco/ual/ops/<op>/<op>.hpp                 Op 类 + Algos[] 数组
[ ] Step 6  teco/interface/ops/<op>.cpp                组装 Args + RUN_OP
[ ] Step 7  test/zoo/teco/<op>/<op>.h / <op>.cpp       测试 Executor + cpuCompute
[ ] Step 8  test/zoo/teco/<op>/test_case/*.prototxt    多 shape 测例（输出 shape 必写）
[ ]        （如有标量参数）test_proto/tecokernel/<op>.proto + 注册 tecokernel.proto
[ ] Step 9  bash build.sh --build teco
            cd test && source env.sh && sh build.sh --arch teco
            ./build/demo --gid=0 --case_path=zoo/teco/<op>/test_case/0.prototxt  → ALL PASSED
[ ] Step 10 api/torch_ext.cpp 加 <op>_torch + m.def；__init__.py 导出
            python3 setup.py build_ext --inplace
[ ] Step 11 python_api_test/test_<op>.py  自测通过
[ ] 文件名/目录名/算子名一致；文件带 BSD License 头；删除调试代码
[ ] （性能验收）./build/demo --perf_repeat=50 --warm_repeat=3 ...
```

---

## 18. 下一步：性能优化

`vector_add` 的基础版是**性能基线**（1M 元素约 13 ms、带宽约 0.96 GB/s），
优化空间很大。按收益从高到低：

1. **SPM + 分块**：用 `malloc`/`memcpy` 把每个 SPE 的分块数据搬到片上 SPM 再算，
   减少全局内存访问；注意单次 SPM 申请不超过 235KB。
2. **DMA 双缓冲**：`rt_dma`/异步 `memcpy`，在算第 i 块时预取第 i+1 块，隐藏访存延迟。
3. **SIMD 向量化**：用 `floatv16` 等向量类型一次算 16 个元素，提高单核吞吐。
4. **负载均衡**：调整分块粒度（当前是连续均分），减少尾部空转。

每改一版都要：
- 保持 `ALL PASSED`（正确性不能退）；
- 用 `--perf_repeat` 对比 `[Average Hardware Time]`；
- 一次只改一个机制，便于归因。

---

**恭喜！** 你已完整走完 SDAA 算子开发的 0 → 11 步。
换个算子，照着第 17 节的 Checklist 再来一遍即可。



# 加法算子 kernel的示例

## 1. 算子开发流程
```json
实现流程
步骤一：申请主机端内存并初始化输入数据
步骤二：申请Global存储空间并搬运数据（主机端至Global）
步骤三：申请SPM存储空间并搬运数据（Global至SPM）至SPM进行计算
步骤四：搬运数据（SPM至Global）
步骤五：搬运数据（Global至主机端）
步骤六：算子测试
```

/// 加法算子的实现
```c++
// 使用sdaa空间名
using namespace sdaa;
#define TOTAL_NUM (256 * 32)
#define FSIZE (TOTAL_NUM * sizeof(float))

// x，y：表示输入的Global地址，z：表示计算结果的Global地址
__global__ void kernel_add(float *x, float *y, float *z, uint32_t total_num)
{
    // 将所有数据切分为threadDim块，每块含有tile_num个数据，分给不同的SPE去计算
    uint32_t tile_num = total_num / threadDim;
    // 计算出tile_num个数据占用多少字节的数据空间
    uint32_t spm_size = tile_num * sizeof(float);
    // 在SPE为x，y，z申请SPM存储空间
    // 使用SPM存储空间可以加快数据的访问速度，提升性能
    float *spm_x = (float *)malloc(spm_size);
    float *spm_y = (float *)malloc(spm_size);
    float *spm_z = (float *)malloc(spm_size);
    // 使用输入数据x, y的首地址 + threadIdx * tile_num 偏移坐标作为搬运数据的源地址
    // 对Global存储空间的数据进行切分后，搬运到SPM存储空间
    memcpy(spm_x, (x + threadIdx * tile_num), spm_size);
    memcpy(spm_y, (y + threadIdx * tile_num), spm_size);

    // 每个计算核心SPE相隔tile_num个float数据，且循环tile_num次，进行加法计算
    for (uint32_t i = 0; i < tile_num; i++) {
        // 将SPM上所有输入数据相加，并将计算结果输出到对应的SPM存储空间
        spm_z[i] = spm_x[i] + spm_y[i];
    }
    // 用输出数据z的首地址 + threadIdx * tile_num 偏移坐标作为搬运数据的目的地址
    // 将SPM存储空间上的计算结果搬运到Global存储空间
    memcpy((z + threadIdx * tile_num), spm_z, spm_size);
}

int main() 
{
    // 设置0号SDAA计算设备，用于进行加法计算
    sdaaSetDevice(0);
    // 申请主机端输入数据和输出数据的内存空间
    float *hdata_x = (float *)malloc(FSIZE);
    float *hdata_y = (float *)malloc(FSIZE);
    float *hdata_z = (float *)malloc(FSIZE);
    // 初始化输入数据x，y的值， 初始化方式可以根据实际情况自行选择
    for (int i = 0; i < TOTAL_NUM; i++) {
        hdata_x[i] = (float)(i / TOTAL_NUM);
        hdata_y[i] = (float)sin(i / TOTAL_NUM);
    }
    // 定义设备端指针初始化为NULL
    float *dev_data_x = NULL;
    float *dev_data_y = NULL;
    float *dev_data_z = NULL;

    // 申请Global存储空间，并返回地址给之前定义的指针
    sdaaMalloc((void **)&dev_data_x, FSIZE);
    sdaaMalloc((void **)&dev_data_y, FSIZE);
    sdaaMalloc((void **)&dev_data_z, FSIZE);

    // 将主机端数据复制到Global存储空间；需要配置sdaaMemcpyHostToDevice，数据传输方向是主机端至设备端
    sdaaMemcpy(dev_data_x, hdata_x, FSIZE, sdaaMemcpyHostToDevice);
    sdaaMemcpy(dev_data_y, hdata_y, FSIZE, sdaaMemcpyHostToDevice);

    // 调用Kernel函数，将实际输入数据、输出数据的地址填入函数参数，进行计算
    kernel_add<<<1>>>(dev_data_x, dev_data_y, dev_data_z, TOTAL_NUM);
    // 进行同步，等待所有SPE运行完Kernel函数
    sdaaDeviceSynchronize();
    // 将计算完成的数据从Global搬运到主机端内存
    sdaaMemcpy(hdata_z, dev_data_z, FSIZE, sdaaMemcpyDeviceToHost);
    
    // 申请主机端的内存空间，用于存放主机端的加法计算结果
    float *golden_z = (float *)malloc(FSIZE);
    for (int i = 0; i < TOTAL_NUM; i++) {
        // 在主机端执行加法计算
        golden_z[i] = hdata_x[i] + hdata_y[i];
        // 主机端计算结果和设备端计算结果的绝对值误差如果大于5e-7，则提示精度不达标
        if(abs(golden_z[i] - hdata_z[i]) > 5e-7) {
            printf(" %dth value: %f is wrong! \n", i, hdata_z[i]);
            break;
        }
        if(i == TOTAL_NUM - 1) {
            printf(" SUCCESS! \n"); 
        }
    }

    // 数据使用完后，释放主机端内存
    free(hdata_x);
    free(hdata_y);
    free(hdata_z);
    free(golden_z);
    // 数据使用完后，释放Global存储空间
    sdaaFree(dev_data_x);
    sdaaFree(dev_data_y);
    sdaaFree(dev_data_z);

    return 0;
}
```