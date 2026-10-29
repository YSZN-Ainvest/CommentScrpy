# 沪深300成分维护与股评抓取

整理自 `Scrpy/test.py`（雪球）、`Scrpy_dfcf/test.py`（东方财富）和 `Scrpy/index_comp.py`。保留函数式结构、请求参数与 CSV 格式，原目录及历史数据不变。

## 配置统一在 config 文件夹

直接修改配置文件，然后运行脚本。不使用命令行参数，也不使用环境变量或 `config.local.json`。

| 文件 | 内容 |
| --- | --- |
| `config/settings.py` | 数据路径、请求头、URL、查询参数、请求次数上限及等待时间 |
| `config/cookies.py` | 已填入原项目当前使用的雪球及成分接口 Cookie |
| `config/cookies.example.py` | 不含凭据的 GitHub 示例 |

本机整理后的版本已经填好 Cookie，无需另建本地配置。过期后直接打开 `config/cookies.py`，将 `COOKIES_xueqiu` 字典替换成自己的雪球 Cookie，将 `COOKIES_dfcf` 替换成东方财富成分接口 Cookie，保留变量名。字典每一项对应一个 Cookie 名称和值。东方财富股评请求沿用原逻辑，不发送 Cookie。

`config/cookies.py` 被 Git 忽略，避免真实凭据进入仓库。从 GitHub 克隆后，将同目录的 `cookies.example.py` 复制为 `cookies.py`，填入自己的 Cookie 即可；所有配置仍在同一个文件夹。不要强制提交含真实 Cookie 的文件。

在 `config/settings.py` 中：

- `MAX_SEARCH_xueqiu = 50`、`MAX_SEARCH_dfcf = 100`：保留原入口各平台请求尝试次数上限。
- `RAND_WAGE = (40, 60)`：每只股票的外层循环只随机等待一次，再依次抓取雪球和东方财富；切换平台不额外等待。各源内部翻页和失败重试仍保留随机等待。低于此范围的设置仍按至少40–60秒执行；更长等待保留。
- 成分股下载分页和失败重试均等待1秒，与股评等待独立；此固定值直接保留在更新脚本中。
- `DATA_PATH_xueqiu`、`DATA_PATH_dfcf`、`HS300_PATH`：数据与名单路径，默认相对于项目根目录。
- 成分接口每页20条、最多100页、每页最多3次尝试、20秒超时保持原值。

## 安装与运行

需要 Python 3.11 或以上，进入本目录执行：

```bash
uv sync
uv run python test.py
```

第二条命令会持续抓取，按 Ctrl+C 停止。也可用已有安装 pandas 和 requests 的环境直接执行 `python test.py`。仅保留这两个实际依赖，版本下限沿用原项目。

成分股更新独立手动运行：

```bash
uv run python index_comp.py
```

不要同时启动多个抓取进程；当前没有跨进程限速和文件锁。两个脚本导入时均不会发起网络请求。

## 代码对应关系

| 函数／文件 | 用途 |
| --- | --- |
| `Load_Page_xueqiu`、`Load_Comment_xueqiu` | 原雪球请求与解析，仅加后缀 |
| `Load_Comment_dfcf`、`str_to_stamp` | 原东方财富解析及时间转换 |
| `Check_Point`、`Load_New_Comments`、`Updates` | 两平台共用的检查点、翻页和增量写回，保留原名 |
| `test.py` 的 `main()` | 保留 `while True / for stock_name` 轮询骨架 |
| `index_comp.py` 的 `get_hs300_codes` | 原成分股抓取及校验 |

平台专属配置用 `_xueqiu`／`_dfcf` 区分，成分接口配置用 `_index` 区分；公共函数的 `Load_Comment`、`DATA_PATH` 参数表示传入的平台实现与目录，不属于某个平台。

共享函数的原有参数顺序保持不变，仅在末尾追加平台选择参数。CSV 仍为 `stamp,text`，时间戳为毫秒，按时间降序。增量筛选仍只保留严格大于检查点的时间戳，东方财富时间转换仍使用本地时区。直接调用单页函数不会自动等待，连续调用需自行保持间隔。

## 名单与历史数据

`HS300` 来自原静态名单，两份原名单相同，均为300只。成分更新保留原行为：本次接口必须返回300只，但保存旧名单与新名单的并集，只增加、不删除历史成分，所以累计名单未来可能超过300只。轮询只在启动时读取名单，更新后需重启轮询。

历史股评数据未复制。延续原检查点时，在启动抓取前，将原 `Scrpy/data/` 的 CSV 复制到 `data/xueqiu/`，将原 `Scrpy_dfcf/data/` 的 CSV 复制到 `data/dfcf/`，不要混放。未迁移时从第一页开始，受请求次数上限限制，不保证补齐全部历史。日志为项目目录的 `run.log`。

## 离线验证与 GitHub

```bash
uv run python -m unittest discover -s tests -v
```

9项测试使用模拟响应并禁止真实 HTTP 和 socket 连接，覆盖解析、分页与重试、检查点、去重、平台隔离、异常后的股评等待，以及成分分页与重试的1秒等待。测试中的 sleep 只在测试进程中替换。未实际联网验证接口和 Cookie 是否仍有效。

`.gitignore` 已排除真实 Cookie、数据、日志、虚拟环境和缓存。没有复制原 notebook，未初始化或上传 GitHub 仓库。

主循环固定依次抓取雪球与东方财富，不再设置 SOURCE 开关。函数默认3次尝试、成分下载的固定分页上限／重试次数／超时直接写在使用位置，配置仅保留路径、请求信息与股评运行参数。

股评详细日志统一以 `[雪球][股票代码]` 或 `[东方财富][股票代码]` 标识来源，覆盖检查点、分页停止、失败重试、次数上限和增量保存。共享函数末尾追加可选 `source` 参数供包装函数调用时明确日志来源；正常两平台抓取自动选择对应名称。
