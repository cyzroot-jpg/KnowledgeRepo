# Docker


## 1. 基本使用

> Docker 的绝大部分管理命令（如 start、stop、restart、logs、exec、rm 等），容器ID和容器名称可以无条件互换使用。

**拉取镜像**
```bash
docker pull ngixn(镜像名)

```

**2. 运行容器**

```bash
docker run -d -p 8080:80 ngixn(镜像名)(如果没有就会自动的从仓库中拉取)

 - -d：detach的缩写，表示后台运行（守护模式），容器会在后台静默运行，不会把日志打印到当前的终端
 - -p 8080:80：端口映射，格式：主机端口:容器端口
 - --name ubuntu-test：给容器起名字

后台运行的容器需要doecker exec进入

> 后台运行和非后台运行：容器进程的生命周期是否绑定在当前终端上。

docker run -it (镜像名) /bin/bash

 - i：交互操作
 - t：终端
 - /bin/bash：这个是我们希望的交互式的shell，这里是/bin/bash
 - exit：退出容器

```

**3. 进入容器（后台模型启动容器）**

```bash
docker exec -it (容器ID) /bin/bash

 - -i：--interactive: 保持标准输入打开。
 - -t：--tty: 分配一个伪终端。
 - -e, --env: 设置环境变量。
 - --env-file: 从文件中读取环境变量。


```

**4. 查看容器**

```bash

docker ps
>只列出运行中的容器

- -a：显示所有的容器，包括停止的
- -q：只显示容器的ID
- -l, --latest: 显示最近创建的一个容器，包括所有状态。
```

**5. 启动/停止/删除容器**

```bash

docker start (容器名/ID) container2  container3  container...
> 可以同时启动一个或多个容器

docker stop (容器名/ID) container2  container3  container...
> 同时停止多个容器
- -t：指定等待时间停止容器

docker restart (容器名/ID) container2  container3  container...
> 同时重启多个容器
- -t：指定等待时间重启容器

docker rm (容器名/ID) container2  container3  container...
> 同时删除多个容器
- -f, --force: 强制删除正在运行的容器（使用 SIGKILL 信号）。
- -l, --link: 删除指定的连接，而不是容器本身。
```

**6. 构建自己的镜像**

```bash

Dockerfile 是一个用来构建镜像的文本文件，文本内容包含了一条条构建镜像所需的指令和说明。
通过定义一系列命令和参数，Dockerfile 指导 Docker 构建一个自定义的镜像。

步骤：
1. 新建一个名为 Dockerfile 文件
在一个空目录下，新建一个名为 Dockerfile 文件，并在文件内添加以下内容：

FROM nginx  # 指定基础镜像。意思是以官方 Nginx 镜像为“底子”，所有后续操作都在这个底子上进行。
RUN echo '这是一个本地构建的nginx镜像' > /usr/share/nginx/html/index.html # Dockerfile 的构建指令。它表示在构建镜像时（即执行 docker build 的那一刻），会新建一个临时容器，并在容器内运行后面的 Shell 命令。原本官方 Nginx 自带的 "Welcome to nginx!" 英文欢迎页，被替换成了你写的这句中文。

    ```
        FROM：定制的镜像都是基于 FROM 的镜像，这里的 nginx 就是定制需要的基础镜像。后续的操作都是基于 nginx。
        RUN：用于执行后面跟着的命令行命令。有以下俩种格式：执行 docker build 的那一刻运行
            - shell 格式：RUN <命令行命令> # <命令行命令> 等同于，在终端操作的 shell 命令。
            - exec 格式：RUN ["可执行文件", "参数1", "参数2"] # 例如：# RUN ["./test.php", "dev", "offline"] 等价于 RUN ./test.php dev offline
            > Dockerfile 的指令每执行一次都会在 docker 上新建一层。所以过多无意义的层，会造成镜像膨胀过大。以 && 符号连接命令，这样执行后，只会创建 1 层镜像。

    ```

2. 开始构建镜像

docker build -t nginx:v3 .

在 Dockerfile 文件的存放目录下，执行构建动作。通过目录下的 Dockerfile 构建一个 nginx:v3（镜像名称:镜像标签）。
最后的 . 代表本次执行的上下文路径

上下文路径，是指 docker 在构建镜像，有时候想要使用到本机的文件（比如复制），docker build 命令得知这个路径后，会将路径下的所有内容打包。

解析：由于 docker 的运行模式是 C/S。我们本机是 C，docker 引擎是 S。实际的构建过程是在 docker 引擎下完成的，所以这个时候无法用到我们本机的文件。这就需要把我们本机的指定目录下的文件一起打包提供给 docker 引擎使用。
如果未说明最后一个参数，那么默认上下文路径就是 Dockerfile 所在的位置。
注意：上下文路径下不要放无用的文件，因为会一起打包发送给 docker 引擎，如果文件过多会造成过程缓慢。
```

## 2. 其他命令

**docker cp**

```bash

docker cp 容器ID或名称:源路径(可以是容器内的路径或者是宿主机的路径) 目标路径(可以是容器内的路径或者是宿主机的路径)

docker cp 命令用于在 Docker 容器和宿主机之间复制文件或目录。
docker cp 命令支持从容器到宿主机，或从宿主机到容器的文件复制操作。
    
    注意：
    - docker cp 命令不会修改源文件或目录，它仅进行复制操作。
    - 目标路径必须是有效的路径，且宿主机或容器中应有足够的权限进行写入操作。
    - 在处理大文件或大目录时，复制操作可能需要一些时间。

```