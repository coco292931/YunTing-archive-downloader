# YunTing-archive-downloader

云听历史节目（点播回听）下载器

## 说明

此项目是为了纪念Hit FM而生，也同样为了纪念那些离我们而去的声音

这个我从小学就开始听，陪伴我近9年的电台，在25年12月23日零时，永久沉寂了。。

不能说有多伤感，因为时代就是如此发展，电台终将会淡出人们的视野，

只是这次，恰好轮到887而已。



在这曲终人散之时，趁着云听尚存有Hit FM的回放，故写这样一个下载器，保存下来曾经的回忆

## 原理

点进云听官网的点播回听，不难发现每一个电台都有一个对应的broadcastId。虽然现在云听隐藏了Hit FM对应的入口，但是经过简单枚举，发现Hit FM对应的broadcastId为662

以最后一天的回放地址为例，
默认网址：https://www.radio.cn/pc-portal/sanji/passProgram.html?channel_name=662&program_name=undefined&date_checked=2025/12/22&title=cate#

实际有用的部分：channel_name=662&date_checked=2025/12/22 
即https://www.radio.cn/pc-portal/sanji/passProgram.html?channel_name=662&date_checked=2025/12/22

通过F12抓包，发现请求了这样一个接口：
https://ytmsout.radio.cn/web/appProgram/listByDate?date=2025-12-22&broadcastId=662 （需要携带header）

**接口鉴权（签名逻辑）**：
为了成功请求该接口，获取节目列表，除了基本的浏览器的 User-Agent，其请求头（Headers）中还必须要携带两项关键参数：timestamp（时间戳）和 sign（签名）。
其中 sign 的生成逻辑如下（该逻辑来自云听的前端 api.js 文件硬编码实现）：

1. 获取当前13位毫秒级时间戳 timestamp。
2. 将请求的 GET 参数按键名进行字母顺序排序，并拼接为形如 key1=value1&key2=value2 的字符串。
3. 将参数字符串、时间戳以及前端代码中固定的密钥（key = "f0fc4c668392f9f9a447e48584c214ee"）拼接：{参数字符串}&timestamp={timestamp}&key={key}。
4. 对上述拼接出的长字符串进行 MD5 哈希计算，并将其转换为大写，即得到 sign。

返回数据就是节目列表:

```json
{
    "code": 0,
    "message": "SUCCESS",
    "data": [
        {
            "contentType": 4,
            "id": "977147343",
            "columnId": "1432818",
            "broadcastId": "662",
            "programName": "Music Flow 音乐流",
            "des": "",
            "startTime": 1766332800000,
            "endTime": 1766354400000,
            "programDate": 1766332800000,
            "playUrlLow": "https://ytrecordbroadcast.radio.cn...m4a",
            "playUrlHigh": "https://ytrecordbroadcast.radio.cn...m4a",
            "downloadUrl": "https://ytrecordbroadcast.radio.cn...m4a",
            "playFlag": 1,
            "image": "https://ytmedia.radio.cn/...jpg",
            "imageLong": "https://ytmedia.radio.cn/...jpg",
            "enableStatus": 1,
            "columnEnableStatus": 1
        }
    ]
}
```

上面3个Time是时间戳，转换一下即可

playUrl和downloadUrl就是对应节目的音频文件，playUrlHigh是高码率版本（约191kbps），剩下两个（其实是同一个地址）是低码率版本（约48kbps）

image和imageLong是节目对应的展示图片，Long是宽度更大的长方形版本。

因此，要达到下载的目的，我们只需要抓取请求接口，之后下载对应文件就行。

## 功能与使用说明

目前提供了命令行与图形化（GUI）两套操作逻辑：

### 1. 命令行使用

```bash
# 单日下载
python downloader.py -d "25-12-22" -b 662

# 多连日下载（跨度下载），并在每天中间延迟3秒
python downloader.py -d "22-07-01 to 25-12-22" -b 662 --delay 3

# 下载低码率音频，且不下载封面图片，同时指定输出目录为 my_radio_folder
python downloader.py -d "25-12-22" -b 662 -o "my_radio_folder" --low-bitrate --no-images
```

**所有支持的命令行参数：**

- `-h`, `--help` : 显示帮助信息。
- `-d DATE`, `--date DATE` : 指定单独日期 (如 `'25-12-22'`) 或日期范围 (如 `'25-11-22 to 25-12-22'`)。
- `-b BROADCAST`, `--broadcast BROADCAST` : 电台ID，默认 `662` (Hit FM)。
- `-o OUTDIR`, `--outdir OUTDIR` : 下载的基础输出目录，默认为 `downloads`。
- `--low-bitrate` : 选择下载低码率音频 (默认情况为下载高码率，带此参数则切换低码率以节省空间)。
- `--no-images` : 阻止下载节目封面图片。
- `--api-key API_KEY` : 用于API鉴权的固定密钥参数（非必要一般无需更改）。
- `--delay DELAY` : 当执行多日持续下载时，请求日期间隔的睡眠时间(秒)，默认 `1.5`。

### 2. GUI 界面操作 (推荐)

直接运行 `python gui.py` 唤出界面。
**核心特性：**

- **可视化参数调整**：在界面输入日期范围（支持单日或多日）、电台 ID，或是更改保存目录、控制防封禁请求延迟等。相关的配置会自动保存到同目录下的 `config.json` 内作为默认预设。
- **自定义下载项**：可以选择获取默认的高码率音频或是节省空间的低码率；可以选择是否连带下载音频的封面图资源。
- **防止重复与元数据映射**：图片只下载一次（以 `downloaded_images.txt` 缓存），并且按对应节目的名字被重命名，源链接信息保存在 `images_info.txt` 中。下载目录会以日期按规则分类，并在文件夹内生成当天的抓取记录报告 `YYYY-MM-DD_program_info.txt`，包含实际下载的高/低音质标识。
- **二段安全中断保护 (防烂尾机制)**：
  - 下载过程所有的文件采用 `.part` 缓存形式写入；连接意外中断或主动停用绝不产生报废无发播放的文件。
  - **暂停/恢复**：随时中断/恢复主下载线程与转换线程。
  - **软停止**：结束当前文件后自动取消随后的全部任务队列，包含转换队列的安全平滑退出。
  - **强行停止**：即便正在执行途中，立刻截断释放资源，并彻底清理残断文件与子进程。
- **配置持久化防御**：退出时系统会自动比对参数差异并防错弹窗提示，避免丢失辛苦调好的配置。所有诸如路径偏好均为干净相对路径标准（如 `"downloads"`）存放于 `config.json`，方便跨设备携带。

## 自动化后处理 (格式转换管线)

虽然 m4a 已经比较高效，但是如果全部按高码率保存节目，对储存依然是一笔不小的开销。
通过指定本地 FFmpeg（内置环境检测），图形界面原生支持了**异步多线程自动转换管线**功能：

1. **并行解耦，边下边压**：将下载和转换彻底分作两条完全独立的任务线运作，并通过动态队列衔接。当下载完成某集后，系统将其立即投喂给后处理队列进行降码/转码操作，而下载线程刻不容缓并发拉取下一集，双轨齐发，大幅度缩减耗时！双日志窗（下载与FFmpeg）能实时观测交响乐般的同步执行态。
2. **丰富的转码规格参数**：
   - 支持向 `opus`, `mp3`, `aac`, `m4a` 目标重混流并细控采样率（防 Opus 规范等报错）、固定压缩码率及调用 CPU 线程数。
   - 提供 “跳过现有 / 仅覆盖 0kb 残除 / 全量覆盖” 的3态安全覆写保护。
   - 自由设定独立输出文件夹，也可原地安全覆盖并搭配【转换成功后删除原文件】一键式瘦身。
3. **封面图自动反嵌**：能够监测源同名或源下载图片，并运用 ffmpeg 将其作为【专辑封面素材】反向无损硬写入最终的音频内部（**注：Opus 格式使用原生的 FFmpeg 无法直接嵌入图片流，如果你需要为 Opus 音频嵌入封面，可见下方进阶替代方案**）。
4. **批处理人工干预排队**：系统更支持扫描单日或全集目录寻找遗漏文件，预先生成批处理终端命令清单；用户甚至可在命令编辑区自由增删改查单条命令执行。

#### 📖 进阶：如何为 Opus 封装格式嵌入封面？

目前直接通过 `FFmpeg` 转码为 Opus/Ogg 容器时，因底层容器不支持将图片作为独立视频流打包，直接写入会报错退出。如果您**必须**为 `.opus` / `.ogg` 文件附带封面，建议采用以下两种常用替代方案进行二次处理：

* **方案A：使用 Python 的 `mutagen` 库（推荐）**
  这是最纯净的办法。先通过 FFmpeg 将音频转码为您需要的 `.opus`（不在 ffmpeg 内拼接图片），接着编写一个小脚本，引入 `mutagen` 库。读取事先备好的封面图片并转化为 Base64 编码，最终作为 `METADATA_BLOCK_PICTURE` 这个特定的 Vorbis Comment 标签无损硬写到 `.opus` 之中。
* **方案B：使用官方的 `opusenc` 命令行工具**
  不再直接令 FFmpeg 压缩 opus，而是让其剥离图片纯粹导出无损的 `.wav` 临时音频流。随后调用 Xiph 官方维护的命令行工具，通过 `opusenc --picture cover.jpg input.wav output.opus`，一键令其在编码音频的同时自动妥善完成 Base64 处理封面并合成。

## 电台 ID 对照表参考

云听不同电台对应的 `broadcastName` 及 `id` 如下（部分）：

| 电台 ID   | 电台名称              |
|:------- |:----------------- |
| **639** | 中国之声              |
| **640** | 经济之声              |
| **641** | 音乐之声              |
| **642** | 经典音乐广播            |
| **643** | 台海之声              |
| **644** | 神州之声              |
| **645** | 大湾区之声             |
| **646** | 香港之声              |
| **647** | 民族之声              |
| **648** | 文艺之声              |
| **649** | 老年之声              |
| **650** | 藏语广播              |
| **651** | 维吾尔语广播            |
| **653** | 中国交通广播            |
| **654** | 中国乡村之声            |
| **655** | 哈萨克语广播            |
| **662** | Hit FM 劲曲调频       |
| **664** | 南海之声              |
| **692** | 环球资讯广播            |
| **734** | 英语资讯广播 CGTN Radio |

## 维护者快速入口（供后续修改）

为了便于后续接手，本项目可按下面的分层理解：

- `downloader.py`：负责接口签名、节目列表请求、音频/图片下载与落盘。
- `converter.py`：只负责 FFmpeg 检测和命令拼装，不直接执行子进程。
- `gui.py`：负责 UI、状态机（暂停/软停/强停）、任务调度与下载/转码串联。

核心调用链如下：

1. GUI 启动下载：`start_download_thread -> run_download -> download_by_date`。
2. 单文件下载完成后，`downloader.py` 通过 `post_process_cb` 回调通知 GUI。
3. GUI 侧生成 FFmpeg 命令并执行（自动队列或手动批处理）。

后续改动时，建议优先关注这些“联动点”：

- 若修改 `download_by_date(...)` 参数：同步调整 `gui.py` 的调用位置与 README 参数说明。
- 若修改 `build_ffmpeg_cmd(...)` 参数：同步调整 GUI 命令生成、配置读写字段。
- 若新增配置项：同步更新 GUI 变量初始化、`load_config/save_config`、`config_example.json`、README。

推荐最小自检：

- `python -m py_compile gui.py downloader.py converter.py`
- `python gui.py`
- `python downloader.py --help`

## 注意事项

云听本身似乎没有限速策略，也似乎不会封禁ip，但保险起见，使用时仍需注意流量。

转码必然会导致音质损失，加上云听本身也已经经过一层压缩，想保存留档的朋友请自行斟酌是否转换，并设定好参数，因转换导致的损失作者概不负责。

本工具仅供学习使用，请勿用作非法用途