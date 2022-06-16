# Course Helper

一个Electron+Vue3作为前端，Python作为本地后端的桌面端软件。

[TOC]

<img src="https://s2.loli.net/2022/05/22/7vx6qJmUDpPR8Eu.png" alt="Electron前端" style="zoom: 75%;border-radius:25px" />



<img src="https://s2.loli.net/2022/05/27/uQopRajxcXGy9H6.png" alt="python后端" style="zoom: 75%;border-radius:25px"  />



## 开始使用

1. **下载**

   Github Release: 	[CourseHelper](https://github.com/ruchuby/Course-Helper/releases/)

   蓝奏云:					[蓝奏云外链](https://wwi.lanzoup.com/b01ji7zne )  密码:fd85

2. **安装**

   解压后双击`CourseHelper Setup.exe`，安装到任意位置

3. **使用**

   双击桌面快捷方式，启动软件

   软件启动时会尝试启动后端服务（黑框框）
   
   **启动失败**，请尝试在软件内启动后端，操作如下图
   
   <img src="https://s2.loli.net/2022/06/16/kBUvm7pHeOcsVSu.png" alt="启动后端" style="zoom: 75%;border-radius:25px" />
   
   
   
   **若仍启动失败**，请手动运行`xxx安装目录\resources\server.exe`

------



## 需求分析

为进一步深化教育改革，加快我校优质教学资源的共建共享，我校引进了清华大学教育技术研究所研发的支撑教与学的网络支撑环境的综合平台，建立了厦门大学课程中心，即[couse平台](http://course.xmu.edu.cn/)。

course平台已有十年的使用历史，由于缺少更新、维护，使用起来非常不方便。但是由于学校强制要求教师学生使用course平台，我们不得不在平台上查看、下载课件，上传作业等等。加上近年主流浏览器都已经停止对Flash的支持、course平台登录添加伪VPN验证等等问题，这个平台的变得愈发不方便。

由此，个人决定做一款PC端course助手，方便同学们使用course网站。



## 软件功能与特点

### 1. 快捷登录 ✔️

用户在保存账号密码到本地后，启动即可快速登录 Course 网站。无需输入密码、拖动滑块验证码

### 2. UI界面 ✔️

~~功能可以差点，UI必须好看~~  

### 3. 课程列表查看 ✔️

可以查看课程列表与课程基本信息

### 4. 课程资源下载 ✔️

进入某课程后，可以勾选需要下载的课程资源文件，批量下载

### 5. 作业查看 ✔️

爬取课程的作业列表，作业详情，简单高效地查看作业内容

### 6. 作业提交 🛠️

使用[wangEditor](https://www.wangeditor.com/)富文本编辑器进行作业内容编辑与提交



## 难点分析与解决

### 前后端通信 ⭐⭐⭐⭐

通信方式的选择：最早打算使用RPC等通信，但是问题很多，最后还是决定主体使用本地HTTP通信(fastapi)

虽然HTTP通信速度上不如RPC通信，但是用于本地HTTP通信，小小的速度差异还是可以接受的。



此外，本来不想使用其他通信方式的，但是碰到了技术上的难点。

某些功能需要双向通信，（后端能够主动向前端发送请求），不得不额外使用了WebSocket。

然后在使用WebSocket时又出现了新的问题，因为**WS通信不像HTTP能有每个请求的回复**，需要进一步处理。

最后通过**添加消息id**判断出每个消息所属的请求，并且使用`asyncio.Future`来**等待消息回复**，成功拿到回复。

后续可以进一步添加**超时时间**，但是目前对超时判断的需求不大。



### 登录 ⭐⭐⭐⭐⭐

存在诸多阻碍，统一身份认证和VPN验证，网站频繁的重定向，对爬虫非常非常不友好。

本来打算用`selenium`或`pyppeteer`蒙混过关。

但万幸，~~某智教育公司、某瑞达公司~~没把纯`requests`的路给堵死

**重难点：**

1. vpn滑块验证码

   获取滑块验证码的图片，PIL解析滑块图片，post通过

   

2. 统一身份认证的请求加密

   key藏在页面源码内里，简单找一找就行，但是用于加密的js代码比较麻烦。

   js源码可以取到，但是不方便直接用python调用（考虑到用户的电脑不一定装了nodejs）

   所以只能用最稳妥的前后端通信的方式，让前端把加密代码执行后返回给后端

   （~~感觉多此一举，但是谁让这是Python的大作业，Electron前端只负责展示数据~~）

   

2. 登录状态的维护

   使用同一个request.Session进行请求，维持前后的cookie等缓存

   并且再每次请求前检查登录状态，及时重新登录

   
   
   理论上虽然能保证登录状态，但是<u>偶尔Session对course网站突然无响应的情况依然存在</u>，
   
   暂时没做更进一步的登录维护，如果**出现无法连接的解决方案**：
   
   1. 退出登录，重新登录（会重置Session）
   2. 重启后端
   3. 重启前后端
   
   

### UI设计与实现 ⭐⭐⭐⭐⭐

第一次使用 `Electron + Vue3`，不得不说这俩虽然开发起来很简单，但是真的会遇到**非常多问题**。

​	**Electron 真的很多问题**

按时间顺序列举一下**从迈出第一步**到**比较流畅地开发**的这段历程：

1. 解决electron环境配置问题
2. electron的不同进程通信，简单入门
3. Vue2的学习
4. Vue2迁移到Vue3的学习
5. electron使用vue的配置
6. 简单使用electron+vue3
7. 各种组件通信
8. Vuex，Vue Router的学习和使用
9. UI组件库使用（Native UI）
10. 解决electron打包的各种问题



### 信息的爬取⭐⭐⭐

course使用**jsp构建的动态网页**，使用`正则 + lxml`提取需要的信息

总有个别页面的信息提取格外**繁琐**

比如课程资源的**文件树**（需要递归）、**作业详情**（藏在input内的纯html）



### 文件下载⭐⭐⭐⭐

因为course网站的下载速度还是非常快的，所以简单的使用了Session去请求文件然后写入磁盘。

但是，除了直接请求下载，其他都是问题。

#### 1. 下载文件名中文乱码

研究了很久才把请求头中的乱码中文重新解析为正常显示的中文



#### 2. 下载流程

**开启下载流程：**

1. 前端向后端发起请求：附加course资源文件的file_id，res_id，文件保存路径
2. 后端检验文件夹是否存在
3. 后端获取下载响应头
4. 后端解析文件名、大小信息
5. 若存在同名文件则为其添加名称后缀
6. 异步进行下载，并在下载过程中发送ws消息更新下载进度 （不阻塞下一步返回下载文件信息）
7. 返回下载文件的信息（文件保存路径，文件大小，下载请求id）



**更新下载进度流程：**

1. 计算下载进度 

2.  WS通信

3.  vuex修改数据 

4. 成功更新下载进度

   

流程看上去问题不大，但是一写就出问题。

小问题略去不提，就记录一下最主要的问题：**线程占用问题**

（以下是对问题的个人理解）

因为下载文件是使用for循环迭代响应体，设置了每次迭代的大小为1B，所以存在一个很高的**线程占用率**。而python的WebSocket库使用异步，内部可能还套了未等待协同的异步，导致每次虽然执行了 `await send_text(xxx)`，但是消息都**堆积着没发送**，直到下载完毕才一股脑发出去。

**解决方案**：在迭代满足更新条件，发送消息后，加上 `await asyncio.sleep(0.01)`，避免高占用阻塞消息发送。



#### 3. 目录结构

因为course网站的课程资源使用文件树状结构，软件需要提供下载**保留目录结构**的可选功能。

**解决方案**：**递归算法**计算每个要下载文件在文件树中的路径，从而生成相应的目录结构。



## 作业详情 ⭐⭐

course网站的作业内容是通过只读富文本框加载隐藏的input元素的value属性来展示的。

爬取到value属性的值，再通过前端js插入到指定元素即可显示作业内容

但是作业内容有一些图片、可下载文件等网络资源，前端无法直接获取（Session由后端保管）。

**解决方案**：后端转发（代理）资源

爬取到value后，正则将需要转发的资源链接替换为后端转发接口请求链接。



### 软件打包 ⭐⭐

Python，Electron的打包，那是大哥不说二哥。1.5⭐是Electron的。



## 技术栈

### Python（后端）

开发快捷，且期末大作业要求。

### Electron+Vue3（前端）

开发快速，UI美观，虽然体积偏大，但具有浏览器性质，方便本项目的一些操作。



