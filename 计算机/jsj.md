# 计算机

## 1. HBM（High Bandwidth Memory）和SRAM（Static Random-Access Memory）
```bash

两种不同类型的计算机内存。

HBM是一种高带宽内存接口，用于3D堆叠的SDRAM，具有较高的带宽和较低的功耗。
SRAM是一种静态随机访问存储器，用于高速缓存等内部存储器，具有更快的访问速度和更低的延迟，但成本更高且占用更多芯片空间。

```

## 2. MAC

```bash

MAC（Memory Access Cost，存储访问开销）是指在计算机系统中，访问内存或存储器所需的时间和资源开销。它是衡量计算机程序或算法性能的重要指标之一。 MAC的值取决于多个因素，包括内存层次结构、缓存命中率、内存带宽、存储器延迟等。较低的MAC值表示访问内存的开销较小，而较高的MAC值表示访问内存的开销较大。

```


1. 需要使用sdaa_kernel_pilot_hermes这个skill，完成/root/code/teco-agent-skills/teco-ops/op_learning/reshape_and_cache/fp16-cache-write/learning_task.md这个任务，利用humanize-kernel-agent-loop进行优化，目标进行10次优化思路，找到最好的
    reshape_and_cache算子的路径如下：/root/node_modules/opencode-linux-loong64/bin/projects/tmp2/teco-ops-juzhenjisuan/teco/ual/kernel/reshape_and_cache在这个目录下面


2. 使用 teco-kernel-optimizer 优化 teco-ops 中的 flash_attn_varlen_func。
先跑 baseline，记录正确性和性能，再进行多轮候选实现、benchmark、champion 选择和消融归因。
每轮只保留通过 correctness 的候选，并在最终总结中说明最佳版本、性能变化、验证命令和剩余风险。
    flash_attn_varlen_func算子的路径如下：/root/node_modules/opencode-linux-loong64/bin/projects/tmp2/teco-ops-juzhenjisuan/teco/ual/kernel/flash_attention在这个目录下面

评估说明：

对每个算子的评估都要完整的分别使用下面的流程

cd /root/node_modules/opencode-linux-loong64/bin/projects/temp/teco-ops-juzhenjisuan
bash build.sh --build teco

cd test
source env.sh
sh build.sh -arch teco

在执行下面的命令前，你要去检查一下，zoo/teco/{算子名}/test_case/ 这个目录下面有没有目录，有的话进行删除
./build/demo --gid=0 --perf_repeat=50 --warm_repeat=3 --gtest_repeat=1 --case_path=zoo/teco/{算子名}/test_case/{case}.prototxt 

补充：
{算子名}：分别是上面两个算子的名字
{case}.prototxt ：这个根据目录下面的.prototxt文件来对应填写。第一个算子评估zoo/teco/reshape_and_cache/test_case/目录下的0，1，2三个测例。对于第二个算子，只评估zoo/teco/flash_attn_varlen_func/test_case/目录下的1，3，5号prototxt测例。


## 3. 

