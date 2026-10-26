## 1. 为什么计时前必须 synchronize()？
CUDA/SDAA 的 kernel 是排队异步执行的。不同步就计时，会得到「0 ms」的假象。所以 minigpt/utils.py 的 Timer 里调用了 torch.sdaa.synchronize()。

SDAA 的 kernel 是入队后立即返回的，Python 会继续往下走
synchronize() 阻塞到所有已入队任务执行完
目的有两个：① 计时覆盖真实计算，而不是只算「入队时间」；② 保证你读到的结果已经算完
