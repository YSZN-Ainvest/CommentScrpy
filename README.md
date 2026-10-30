# 沪深 300 成分维护与股评抓取

本项目使用 Python 维护股票名单，并串行抓取雪球和东方财富股吧的股票讨论数据。每个平台、每只股票分别保存一个 CSV 文件，后续运行根据本地最新时间戳进行增量更新，适合持续积累用于文本分析的数据。

***首次运行耗时较长，修改settings.py中的最大搜索次数***
```python
MAX_SEARCH_xueqiu = 50 # 改为1
MAX_SEARCH_dfcf = 100  # 改为1
```
***完成一轮预热后改回参数并重新运行***


股评抓取入口是 [`run.py`](run.py)，成分名单更新入口是 [`index_comp.py`](index_comp.py)。全部运行配置集中在 `config/`，目前不提供命令行参数、环境变量配置或平台开关。

## 目录

- [功能与数据来源](#功能与数据来源)
- [项目结构](#项目结构)
- [安装与快速开始](#安装与快速开始)
- [通过 curlconverter 获取 Cookie 字典](#通过-curlconverter-获取-cookie-字典)
- [配置说明](#配置说明)
- [抓取流程与增量规则](#抓取流程与增量规则)
- [更新成分名单](#更新成分名单)
- [CSV 格式与数据读取](#csv-格式与数据读取)
- [单只股票与函数调用](#单只股票与函数调用)
- [日志与常见问题](#日志与常见问题)
- [离线测试](#离线测试)

## 功能与数据来源

| 功能 | 当前实现 |
| --- | --- |
| 雪球讨论抓取 | 请求股票讨论接口，读取 `created_at` 和 `description` |
| 东方财富股吧抓取 | 解析列表页面中的 `article_list`，读取 `post_last_time` 和 `post_title` |
| 增量更新 | 以已有 CSV 首行时间戳为检查点，只保存严格晚于检查点的记录 |
| 新数据去重 | 按 `(stamp, text)` 组合去重，保留同一时间但内容不同的记录 |
| 连续轮询 | 按名单顺序，对每只股票依次抓取雪球、东方财富，整轮结束后继续下一轮 |
| 等待与重试 | 股票之间及平台内部后续请求尝试之间随机等待；请求失败后重试当前页 |
| 成分名单维护 | 从东方财富成分接口获取并校验 300 只股票，再与旧名单取并集 |
| 运行日志 | 股评日志同时输出到终端和项目根目录的 `run.log` |

两个平台的 `text` 含义不同：雪球保存接口返回的描述，东方财富保存帖子标题，不包含帖子正文、作者、回复列表等字段。项目不做文本清洗、情感分析或行情下载；雪球描述中的 HTML 等内容也会原样保留。

## 项目结构

```text
Scrpy_merged/
├── run.py                  # 两平台持续抓取入口及公共增量函数
├── index_comp.py           # 手动更新成分名单
├── HS300                   # 待抓取股票名单，每行一个代码
├── config/
│   ├── __init__.py          # 统一导出配置
│   ├── settings.py          # 路径、请求信息、次数上限、等待区间
│   └── cookies.py           # COOKIES_xueqiu 与 COOKIES_dfcf 字典
├── data/
│   ├── xueqiu/             # 雪球 CSV
│   └── dfcf/               # 东方财富 CSV
├── tests/
│   └── test_offline.py      # 模拟响应的离线测试
├── pyproject.toml          # Python 要求与依赖
├── uv.lock                 # uv 依赖锁定文件
└── README.md
```

`run.log` 在启动股评主循环时创建，数据目录由更新函数按需创建。默认路径基于项目位置计算，不依赖进程的当前工作目录；以下命令仍统一在项目根目录执行。

## 安装与快速开始

### 1. 安装依赖

需要 Python **3.11 或以上**。项目依赖为 `pandas>=3.0.6` 和 `requests>=2.34.2`，具体声明见 [`pyproject.toml`](pyproject.toml)。

已安装 uv 时执行：

```bash
uv sync --locked
```

也可以使用 Python 自带的虚拟环境，以下为 Linux / macOS 命令：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'pandas>=3.0.6' 'requests>=2.34.2'
```

后者按版本下限安装，不使用 `uv.lock` 锁定版本。

### 2. 检查 Cookie 配置

打开 `config/cookies.py`，确认定义了下面两个变量，并根据下一节填入自己浏览器请求中的 Cookie。若文件缺失，直接创建它；不依赖 Cookie 示例文件。

```python
# 以下为空配置结构，不代表已经获得有效登录状态。
COOKIES_xueqiu = {}
COOKIES_dfcf = {}
```

| 变量 | 使用位置 |
| --- | --- |
| `COOKIES_xueqiu` | `run.py` 中的雪球讨论接口请求 |
| `COOKIES_dfcf` | `index_comp.py` 中的东方财富成分接口请求 |

东方财富**股吧列表抓取**当前只发送请求头，不使用 `COOKIES_dfcf`。两个配置变量都需要存在，因为配置模块会统一导入它们。

### 3. 检查股票名单

`HS300` 是无表头的 UTF-8 文本文件，例如：

```text
SH600000
SH600519
SZ000001
```

代码使用大写 `SH` / `SZ` 加六位数字。保留前导零，不要写成股票名称或只有六位数字。空行会被忽略；不要加入注释行，也不要重复添加代码，主循环不负责校验或去重。

可直接使用已有名单，也可先手动更新：

```bash
uv run python index_comp.py
```

### 4. 启动抓取

```bash
uv run python run.py
```

使用已激活且装好依赖的环境时：

```bash
python run.py
```

脚本持续运行，按 **Ctrl+C** 停止。启动后会先随机等待 40–60 秒，再处理第一只股票。抓完一轮会继续下一轮，不会自动退出。

配置和股票名单在启动时加载，修改后需要重启。主循环固定处理两个平台；只抓某个平台或只更新一次，可使用后文的函数调用示例。

## 通过 curlconverter 获取 Cookie 字典

[curlconverter](https://curlconverter.com/) 可以把浏览器复制的 cURL 请求转换成 Python `requests` 代码，从中取得 Python 字典形式的 `cookies`。操作方式参考其官网的浏览器请求复制说明。

### 1. 在浏览器中找到目标请求

使用 Chrome 或 Edge 打开目标网站，必要时先登录，按 **F12** 打开开发者工具，进入 **Network（网络）**，再刷新页面或切换讨论分页，让浏览器重新发送请求。

按配置用途查找对应请求：

| 要填写的配置 | 页面与请求定位方式 |
| --- | --- |
| `COOKIES_xueqiu` | 打开雪球股票讨论页，在网络请求中查找 `status.json`，核对是否为配置中的 `/query/v1/symbol/search/status.json` |
| `COOKIES_dfcf` | 打开东方财富沪深 300 成分列表，在网络请求中查找 `clist/get`，核对目标主机 `push2.eastmoney.com` 及成分筛选参数 |

这些路径来自项目当前配置。若网页实际请求已经改变，应以浏览器中成功返回目标数据的请求为依据，同时检查 `config/settings.py` 是否需要适配。

选择请求后查看 **Headers（标头）→ Request Headers（请求标头）**，确认有 `Cookie`。不要把响应中的 `Set-Cookie` 当作请求 Cookie，也不要选图片、统计上报或其他域名的请求。

### 2. 复制 cURL 并转换为 Python

右键目标请求，选择 **Copy → Copy as cURL**；若提供多种格式，选择 **Copy as cURL (bash)**。打开 [curlconverter](https://curlconverter.com/)，粘贴完整命令，选择 **Python / requests** 输出，找到生成代码中的 `cookies = {...}`。

下面用虚构 Cookie 演示格式，不能直接作为登录凭据使用：

```bash
curl 'https://example.com/api' \
  -H 'Cookie: session_id=YOUR_SESSION_VALUE; device_id=YOUR_DEVICE_VALUE'
```

对应的 Cookie 字典形式为：

```python
cookies = {
    'session_id': 'YOUR_SESSION_VALUE',
    'device_id': 'YOUR_DEVICE_VALUE',
}
```

### 3. 填入项目配置

只复制生成的 `cookies` 字典，将变量名改为项目要求的名字。例如，雪球请求转换结果填入：

```python
COOKIES_xueqiu = {
    'session_id': 'YOUR_SESSION_VALUE',
    'device_id': 'YOUR_DEVICE_VALUE',
}
```

这里的键名同样只是演示。实际使用时应保留转换结果中的真实 Cookie 名称和值，不要替换成示例键名。东方财富成分接口的转换结果填入 `COOKIES_dfcf`，并保留文件中的另一个字典。

不需要把转换器生成的 `import requests`、`response = requests.get(...)` 或整段脚本复制到 `cookies.py`；项目已有请求逻辑。若需要更新请求头，应放到 `settings.py` 中对应的 `HEADERS_xueqiu` 或 `HEADERS_index`。

保存后重启抓取进程，使配置重新加载。

### 4. 转换时的常见问题

| 现象 | 检查方法 |
| --- | --- |
| 没有生成 `cookies` 字典 | 检查复制的 cURL 是否包含 `-b` / `--cookie` 或 `Cookie:`；没有 Cookie 的请求无法转换出登录凭据 |
| 网络面板看不到目标请求 | 先打开 Network 再刷新，清除过滤条件，并核对页面是否实际加载了对应列表 |
| 复制内容是 PowerShell 命令，转换失败 | 重新选择 cURL 的 bash 格式，而不是 PowerShell 或 cmd 格式 |
| 修改后仍使用旧 Cookie | 重启 Python 进程；配置不会自动热更新 |
| 请求仍返回登录页、验证页或解析错误 | 检查浏览器请求本身是否成功、Cookie 是否过期、请求头和响应结构是否匹配；转换格式成功不保证接口可用 |

Cookie 可能包含登录凭据，复制出的完整 cURL 也包含这些值，请勿发布到 README、截图或公开问题记录。**当前仓库的 `config/cookies.py` 已被 Git 跟踪，`.gitignore` 没有排除它或 `data/`**，因此修改凭据后提交前需要检查暂存内容；仅追加忽略规则不会取消已有跟踪。

## 配置说明

修改 [`config/settings.py`](config/settings.py) 后重启脚本。

| 配置 | 默认值 | 作用 |
| --- | --- | --- |
| `BASE_PATH` | 项目根目录 | 默认文件路径的基准，也是日志目录 |
| `DATA_PATH_xueqiu` | `BASE_PATH / "data" / "xueqiu"` | 雪球 CSV 目录 |
| `DATA_PATH_dfcf` | `BASE_PATH / "data" / "dfcf"` | 东方财富 CSV 目录 |
| `HS300_PATH` | `BASE_PATH / "HS300"` | 待抓取名单路径 |
| `MAX_SEARCH_xueqiu` | `50` | 每只股票每次雪球更新的总请求尝试上限 |
| `MAX_SEARCH_dfcf` | `100` | 每只股票每次东方财富更新的总请求尝试上限 |
| `RAND_WAGE` | `(40, 60)` | 随机等待秒数的整数闭区间 |
| `URL_xueqiu` / `HEADERS_xueqiu` / `PARAMS_xueqiu` | 见配置文件 | 雪球接口、请求头和查询参数；默认每页请求 20 条 |
| `URL_dfcf` / `HEADERS_dfcf` | 见配置文件 | 股吧列表 URL 模板和请求头 |
| `URL_index` / `HEADERS_index` / `PARAMS_index` | 见配置文件 | 成分接口配置；默认每页 20 条 |

自定义路径时继续使用 `pathlib.Path` 对象，例如：

```python
DATA_PATH_xueqiu = Path("/your/storage/xueqiu")
DATA_PATH_dfcf = Path("/your/storage/dfcf")
HS300_PATH = BASE_PATH / "my_stocks.txt"
```

### 请求次数与等待时间

`MAX_SEARCH_*` 表示**总请求尝试次数**，失败重试也占用额度，不是成功页数、评论条数或整个进程的请求上限。请设置为正整数；当前实现即使传入零或负数，也会尝试一次请求。

`RAND_WAGE` 应满足 `0 <= 下界 <= 上界`，且两端为整数。代码会将实际区间调整为：

```python
(max(40, 下界), max(60, 上界, 下界))
```

所以 `(5, 10)` 实际按 `(40, 60)` 等待，`(80, 100)` 则保留较长等待。

主循环在**每只股票开始前**等待一次，然后依次调用两个平台；切换平台不会额外等待。单个平台内部需要继续翻页或重试时也会等待，到达停止条件后不再额外等待。

成分下载使用独立规则：分页之间和失败重试之间固定等待 **1 秒**，最多 **100 页**、每页最多 **3 次尝试**、每次请求超时 **20 秒**。后三项直接写在 `index_comp.py` 中，不受 `RAND_WAGE` 或 `MAX_SEARCH_*` 影响。

## 抓取流程与增量规则

每只股票、每个平台执行以下流程：

1. 读取对应 CSV。不存在或只有表头时，检查点为 `0`；已有数据时，取**首行**的 `stamp` 为检查点。
2. 从第 1 页抓取。页面非空时先加入结果，尚未触及检查点则继续下一页；失败后重试当前页。
3. 遇到空页、某页末条时间戳小于等于检查点，或达到总尝试上限时停止。
4. 对本次结果按 `(stamp, text)` 去重，按时间戳降序排列，仅保留 `stamp > 检查点` 的记录。
5. 将新增数据放在旧数据之前，覆盖写回同一 CSV。

这些规则有几个使用上的前提：

- **本地 CSV 必须从新到旧排列。** 检查点不是计算全表最大值，而是直接取首行。
- **分页停止依赖返回顺序。** 如果接口返回顺序异常，页末时间可能导致提前停止。
- **相同时间戳的新文本不会跨检查点补入。** 即使文本不同，只要 `stamp` 等于检查点，也会被过滤。
- **达到上限不保证补齐历史。** 首次抓取或长时间停机后，如果未抓到旧边界就保存最新数据，下一轮会使用新的检查点，不能自动补回中间遗漏的数据。
- **已有数据不会重新去重或排序。** 去重和排序只作用于本次抓到的数据。

已落盘的数据可用于重启后的增量抓取，但没有独立的页码断点。中断发生在当前股票保存前时，尚在内存中的结果不会保存；文件采用直接覆盖写入，也没有文件锁或原子替换，因此不要同时运行多个进程更新同一目录。

## 更新成分名单

手动执行：

```bash
uv run python index_comp.py
```

脚本通过东方财富接口分页获取代码，检查总数一致性、六位代码、市场标识、重复代码和最终数量。只有完整获得 **300 只**时才返回结果，抓取校验失败时不会继续合并名单。

成功后会打印本次成分数、相对旧名单的“新增”和“移除”。保存行为为：

```text
保存名单 = 旧名单 ∪ 本次成分名单
```

**“移除”只是显示哪些旧代码不在本次成分中，不会把它们从文件删除。** 只有存在新增代码时才重写名单，保存时排序；因此文件实际表示累计追踪名单，未来可能超过 300 只。

如果只想追踪当前成分，需要另行调整名单维护逻辑或手工维护 `HS300`。主抓取脚本不会自动调用成分更新，也不会在运行中重新读取名单；更新完成后需重启 `run.py`。

## CSV 格式与数据读取

输出路径示例：

```text
data/xueqiu/SH600000.csv
data/dfcf/SH600000.csv
```

文件包含两列，以下数据仅为格式示例：

```csv
stamp,text
1790000001000,较新的讨论文本
1790000000000,较早的讨论文本
```

| 字段 | 含义 |
| --- | --- |
| `stamp` | 毫秒时间戳，保存时作为 DataFrame 索引 |
| `text` | 雪球 `description` 或东方财富 `post_title` |

雪球直接使用 `created_at`。东方财富把 `post_last_time` 按 `%Y-%m-%d %H:%M:%S` 解析，使用运行机器的**本地时区**转换为秒，再乘以 1000；该字段是列表的最后时间，不应直接当作帖子的原始发布时间。应确保机器时区与源时间含义一致，迁移环境时尤其要核对。

读取并转为北京时间显示：

```python
import pandas as pd
from config import DATA_PATH_xueqiu

file = DATA_PATH_xueqiu / "SH600000.csv"
df = pd.read_csv(file)
df["time"] = pd.to_datetime(df["stamp"], unit="ms", utc=True).dt.tz_convert("Asia/Shanghai")
print(df[["time", "text"]].head(10))
```

显示时转换时区不会修复抓取时用错误本地时区生成的时间戳。文本可能含逗号、引号或换行，请使用 CSV 解析器读取，不要直接按逗号拆分。

若迁移旧项目的数据，应先停止抓取并备份，将雪球 CSV 放到 `data/xueqiu/`、东方财富 CSV 放到 `data/dfcf/`，保持文件名、列名和降序排列。两个平台的文件不要混放；已有目标文件时应先检查内容，避免覆盖有效历史数据。

## 单只股票与函数调用

以下代码可在项目根目录的 Python 会话中执行（`uv run python`），或保存为根目录下的独立脚本执行。导入 `run` 和 `index_comp` 本身不会发起网络请求，调用抓取函数才会请求网站。

### 只更新一次雪球数据

```python
import logging
from config import DATA_PATH_xueqiu
from run import Updates, Load_Comment_xueqiu

logging.basicConfig(level=logging.INFO)
Updates(
    "SH600000",
    max_search=3,
    Load_Comment=Load_Comment_xueqiu,
    DATA_PATH=DATA_PATH_xueqiu,
)
```

### 只更新一次东方财富数据

```python
import logging
from config import DATA_PATH_dfcf
from run import Updates, Load_Comment_dfcf

logging.basicConfig(level=logging.INFO)
Updates(
    "SH600000",
    max_search=3,
    Load_Comment=Load_Comment_dfcf,
    DATA_PATH=DATA_PATH_dfcf,
)
```

平台函数和输出目录应配套传入。`Updates` 默认使用雪球函数、雪球目录和 **3 次**总请求尝试上限；主循环才显式传入配置中的 50 / 100。示例里的 3 次适合检查运行结果，但不保证补齐历史。

### 读取一页，不写入 CSV

```python
from run import Load_Comment_xueqiu

comments = Load_Comment_xueqiu("SH600000", page_num=1)
print(comments[:3])  # [(毫秒时间戳, 文本), ...]
```

单页函数没有自动等待和重试，异常会直接抛出；连续调用时需要自行安排间隔。直接调用 `Updates` 的首个请求也没有主循环中的换股等待，但其后续翻页、重试仍遵循最低等待区间。

### 主要函数

| 函数 | 用途 / 返回值 |
| --- | --- |
| `Check_Point(stock_name, file, source="雪球")` | 返回 `(检查点, 已有 DataFrame)` |
| `Load_Page_xueqiu(stock_name, page_num)` | 返回原始 HTTP 响应，不检查状态码 |
| `Load_Comment_xueqiu(stock_name, page_num=1)` | 返回一页 `(stamp, text)` 列表 |
| `Load_Comment_dfcf(stock_name, page_num=1)` | 返回一页 `(stamp, text)` 列表 |
| `Load_New_Comments(...)` | 按页抓取并返回累计列表，不负责写文件或最终去重过滤 |
| `Updates(...)` | 完成检查点读取、抓取、过滤、保存，无显式返回值 |
| `str_to_stamp(time_str)` | 将本地时间字符串转为**秒**时间戳 |
| `index_comp.get_hs300_codes()` | 返回本次校验成功的 300 个排序代码，不修改名单文件 |

公共抓取函数支持 `source` 日志标签。传入自定义加载函数时可显式指定 `source="东方财富"`，避免无法根据内置函数身份判断平台名称。

## 日志与常见问题

运行 `run.py` 时，日志包含时间、级别和 `[平台][股票代码]`，记录本地检查点、分页停止原因、异常重试、尝试上限和准备保存的新增数量。`run.log` 默认追加写入，没有自动轮转。

在另一个终端查看最新日志：

```bash
tail -f run.log
```

独立调用函数时不会自动创建主循环的日志文件，可像上面的示例一样使用 `logging.basicConfig` 配置输出。成分更新脚本主要通过终端打印结果。

| 问题 | 原因与处理 |
| --- | --- |
| 找不到 `test.py`，无法启动 | 当前入口是 `run.py`，请使用 `uv run python run.py` |
| 启动后暂时没有抓取日志 | 第一只股票前也会等待 40–60 秒；后续翻页、重试还会继续等待 |
| 提示 `No module named 'config.cookies'` 或缺少 Cookie 变量 | 创建 `config/cookies.py`，定义两个所需字典 |
| `HS300` 不存在或名单为空 | 检查 `HS300_PATH`；准备有效名单或运行成分更新脚本 |
| 雪球 JSON 解析失败或找不到 `list` | 响应可能是登录页、验证页或接口错误；核对 Cookie、请求头和实际响应 |
| 东方财富解析时出现索引错误或缺少字段 | 页面可能不含预期的 `article_list`；核对页面响应与当前解析规则 |
| 日志显示达到总尝试上限 | 可能数据量大，也可能反复请求失败；先看之前的错误，再判断是否调整上限 |
| 新增条数为 0 | 可能没有更新、记录被检查点过滤，或所有请求都失败；需结合前面的日志判断 |
| CSV 为空或无法读取 | 只有 `stamp,text` 表头是受支持的空档案；零字节或损坏文件需要先备份并修复 |
| 一轮处理很慢 | 抓取完全串行；300 只股票仅外层等待就需约 200–300 分钟，翻页、重试和网络耗时另计 |
| 长时间卡在某个请求 | 两个平台的股评请求目前没有显式 `timeout`，可能阻塞后续处理；成分接口才设置了 20 秒超时 |
| 更新名单或配置后运行行为没变 | 停止并重启抓取进程 |

一次平台更新异常会被主循环记录，随后继续另一平台或下一只股票；这并不表示本次更新成功。抓取过程中的网站响应与 Cookie 有效性需要在实际运行环境中验证。

## 离线测试

测试文件为 [`tests/test_offline.py`](tests/test_offline.py)，使用模拟 HTTP 响应，并拦截真实 HTTP 请求和 socket 连接。测试内容包括解析、分页与重试、等待时间、增量去重、平台隔离、日志以及成分分页和名单合并。

标准执行命令：

```bash
uv run python -m unittest discover -s tests -v
```

**当前已知问题：** 测试的 `setUp()` 仍通过 `load('merged_crawler', 'test.py')` 加载旧入口，实际文件已改为 `run.py`。因此当前直接执行会使 9 项测试均在准备阶段报 `FileNotFoundError`；需要将测试加载路径改为 `run.py` 后再验证。这是测试入口未同步的问题，不能据此判断抓取功能通过或失败。

离线测试即使通过，也不能证明线上接口结构和 Cookie 仍然有效。
