"""手动更新成分名单，保留原来的历史成分并集行为。"""
import time
import requests
from config import COOKIES_dfcf, HS300_PATH, URL_index, HEADERS_index, PARAMS_index


def get_hs300_codes():
    session = requests.Session()
    session.headers.update(HEADERS_index)

    codes = set()
    total = None

    for page in range(1, 101):
        params = PARAMS_index.copy()
        params["pn"] = page

        for attempt in range(3):
            try:
                response = session.get(URL_index, params=params, timeout=20, cookies=COOKIES_dfcf)
                response.raise_for_status()
                payload = response.json()

                if payload.get("rc") != 0 or not payload.get("data"):
                    raise ValueError(f"接口返回异常：{payload}")

                data = payload["data"]
                break
            except (requests.RequestException, ValueError):
                if attempt == 2:
                    raise
                time.sleep(1)

        page_total = data.get("total")
        if not isinstance(page_total, int) or page_total <= 0:
            raise RuntimeError("接口未返回有效的成分股总数")

        if total is None:
            total = page_total
        elif total != page_total:
            raise RuntimeError("抓取过程中成分股总数发生变化，请重新运行")

        rows = data.get("diff")
        if isinstance(rows, dict):
            rows = list(rows.values())

        if not isinstance(rows, list) or not rows:
            raise RuntimeError(f"第{page}页为空，仅抓到{len(codes)}/{total}只")

        for row in rows:
            code = str(row["f12"])
            market = row["f13"]

            if len(code) != 6 or not code.isdigit():
                raise RuntimeError(f"股票代码异常：{row}")
            if market not in (0, 1):
                raise RuntimeError(f"未知市场：{row}")

            symbol = ("SH" if market == 1 else "SZ") + code

            if symbol in codes:
                raise RuntimeError(f"分页出现重复代码：{symbol}，请重新运行")

            codes.add(symbol)

        if len(codes) > total:
            raise RuntimeError("抓取数量超过接口总数")

        if len(codes) == total:
            if total != 300:
                raise RuntimeError(f"该板块返回{total}只，预期300只")
            return sorted(codes)

        time.sleep(1)

    raise RuntimeError("超过分页上限，抓取未完成")


def main():
    codes:set[str] = get_hs300_codes()
    print(f"共 {len(codes)} 只")
    # print(codes)

    # 读取已有成分
    try:
        with open(HS300_PATH, "r", encoding="utf-8") as f:
            old_codes = {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        old_codes = set()

    # 比对差异
    current_codes = {code.strip() for code in codes if code.strip()}
    added = sorted(current_codes - old_codes)
    removed = sorted(old_codes - current_codes)

    print("新增：", added)
    print("移除：", removed)

    # 写入合并名单，保留旧成分并加入新增成分
    if added:
        with open(HS300_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(old_codes | current_codes)) + "\n")



if __name__ == "__main__":
    main()
