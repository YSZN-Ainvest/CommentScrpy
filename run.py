"""合并入口：保留 Check_Point → Load_New_Comments → Updates → while/for 骨架。"""
import os
import time
import logging
import requests
import json
import re
import pandas as pd
from random import randint
from config import (BASE_PATH, DATA_PATH_xueqiu, DATA_PATH_dfcf, HS300_PATH,
                    PARAMS_xueqiu, HEADERS_xueqiu, URL_xueqiu, HEADERS_dfcf, URL_dfcf,
                    MAX_SEARCH_xueqiu, MAX_SEARCH_dfcf, RAND_WAGE, COOKIES_xueqiu)

logger = logging.getLogger(__name__)

def str_to_stamp(time_str):
    return int(time.mktime(time.strptime(time_str,"%Y-%m-%d %H:%M:%S")))


def Check_Point(stock_name, file, source="雪球"):
    """
    读取本地评论档案，返回增量抓取的时间边界和已有数据。

    参数:
        stock_name: 股票代码，用于日志标识。
        file: CSV 文件路径。

    返回:
        文件不存在或档案无数据行时，返回时间边界 0 和空 DataFrame。
        档案非空时，返回首行时间戳和已有 DataFrame。

    前提:
        CSV 第一列为毫秒时间戳，数据按时间从新到旧排列。
        空档案指包含表头但没有数据行的 CSV。

    注意:
        本函数只读取档案，不负责创建文件或目录。
    """
    if not os.path.exists(file):
        logger.info("[%s][%s] 本地档案不存在，将从第一页抓取 | 文件=%s", source, stock_name, file)
        return 0, pd.DataFrame([], columns=['stamp', 'text']).set_index('stamp')

    df = pd.read_csv(file, index_col=0)
    if len(df) == 0:
        logger.info("[%s][%s] 本地档案无数据，将从第一页抓取 | 文件=%s", source, stock_name, file)
        return 0, df

    logger.info("[%s][%s] 本地档案读取完成 | 已有=%d条 | 最新时间戳=%s", source, stock_name, len(df), df.index[0])
    return df.index[0], df


def Load_Page_xueqiu(stock_name, page_num):
    """
    请求指定股票的一页评论，返回原始 HTTP 响应。

    参数:
        stock_name: 股票代码，写入请求参数 symbol。
        page_num: 页码，发送前转换为字符串。

    实现:
        复制公共请求参数后设置股票代码和页码，
        使用配置中的 URL、Cookie 和请求头发送请求。

    注意:
        本函数不检查 HTTP 状态码，也不解析响应内容。
        请求异常交由调用方处理。
    """
    PAR_temp = PARAMS_xueqiu.copy()
    PAR_temp['symbol'] = stock_name
    PAR_temp['page'] = str(page_num)

    response = requests.get(url=URL_xueqiu, params=PAR_temp, cookies=COOKIES_xueqiu, headers=HEADERS_xueqiu)

    return response


def Load_Comment_xueqiu(stock_name: str, page_num: int = 1):
    """
    获取指定页的评论，并提取毫秒时间戳和评论内容。

    参数:
        stock_name: 股票代码。
        page_num: 页码，默认为 1。

    返回:
        由二元组组成的列表，每项为 (毫秒时间戳, 评论内容)。
        保留接口从新到旧的排列顺序，空页返回空列表。

    前提:
        响应为 JSON，包含 list 字段；
        各评论包含 created_at 和 description 字段。

    注意:
        请求、JSON 解析和字段访问异常向调用方传递。
    """
    response = Load_Page_xueqiu(stock_name, page_num)
    comment_list = json.loads(response.text)['list']

    ans = []

    for i in comment_list:
        ans.append((i['created_at'], i['description']))

    return ans


def Load_Comment_dfcf(stock_name,page_num=1):


    response = requests.get(URL_dfcf.format(stock_name=stock_name[2:], page_num=page_num), headers=HEADERS_dfcf)

    # return response

    return [(str_to_stamp(i['post_last_time'])*1000,i['post_title']) for i in json.loads(re.findall('article_list=({.*?});',response.text)[0])['re']]


def Load_New_Comments(stock_name, max_search=3, rand_wage=RAND_WAGE, cut=0, Load_Comment=Load_Comment_xueqiu, source=None):
    """
    从第一页开始抓取评论，直到达到停止条件。

    参数:
        stock_name: 股票代码。
        max_search: 总请求尝试次数上限，应为正整数。
        rand_wage: 相邻请求尝试间随机等待秒数的整数闭区间，
            应满足 0 <= 下界 <= 上界。
        cut: 本地已有评论的最新毫秒时间戳。

    返回:
        已成功获取的评论元组列表，可能包含重复或历史评论，
        由调用方完成去重和时间过滤。

    停止条件:
        当前页为空、当前页末条时间戳小于等于 cut，
        或请求尝试次数达到 max_search。

    实现:
        非空页面先加入累计结果，再判断时间边界。
        成功处理且未触及边界时推进页码，失败后重试当前页。
        失败尝试也占用次数额度。

    注意:
        提前停止的请求不会计入 search_time，但会立即退出循环。
        当前使用宽泛异常捕获，记录错误日志。
        max_search 小于等于零时，仍会执行一次请求尝试。
    """
    if source is None:
        source = "东方财富" if Load_Comment is Load_Comment_dfcf else "雪球"
    # 即使手动传入原来的短间隔，也不低于合并后的保守范围。
    rand_wage = (max(40, rand_wage[0]), max(60, rand_wage[1], rand_wage[0]))
    search_time = 0
    page_num = 1
    new_comments_list = []

    while True:
        record = time.strftime("%Y-%m-%d:%H:%M:%S", time.localtime())

        try:
            page_comments = Load_Comment(stock_name, page_num)
            if not page_comments:
                logger.info("[%s][%s] 第%d页无评论，停止抓取 | 累计获取=%d条", source, stock_name, page_num, len(new_comments_list))
                break

            new_comments_list += page_comments
            if page_comments[-1][0] <= cut:
                logger.info("[%s][%s] 第%d页已触及历史时间边界，停止抓取 | 页末时间戳=%s | cut=%s | 累计获取=%d条", source, stock_name, page_num, page_comments[-1][0], cut, len(new_comments_list))
                break

            page_num += 1

        except Exception:
            logger.error("[%s][%s] 第%d页抓取失败 | 本次尝试=%d/%d | 请求开始时间=%s", source, stock_name, page_num, search_time + 1, max_search, record, exc_info=True)

        search_time += 1
        if search_time >= max_search:
            logger.warning("[%s][%s] 已达到总请求尝试次数上限，停止抓取 | 已尝试=%d次 | 累计获取=%d条 | 尚未确认触及历史时间边界", source, stock_name, search_time, len(new_comments_list))
            break

        time.sleep(randint(*rand_wage))

    return new_comments_list


def Updates(stock_name, max_search=3, rand_wage=RAND_WAGE, Load_Comment=Load_Comment_xueqiu, DATA_PATH=DATA_PATH_xueqiu, source=None):
    """
    获取指定股票的增量评论，与已有档案合并并写回 CSV。

    参数:
        stock_name: 股票代码，同时用于构造 CSV 文件名。
        max_search: 抓取评论的总请求尝试次数上限。
        rand_wage: 相邻请求尝试间随机等待秒数的整数闭区间。

    流程:
        读取检查点，抓取评论，整理新增数据，
        保留时间戳严格大于检查点的记录，
        将新增数据放在已有数据之前并覆盖保存。

    前提:
        DATA_PATH 已存在，已有档案按时间从新到旧排列。
        同一股票不会被多个任务同时更新。

    返回:
        无显式返回值。

    平台选择:
        末尾追加 Load_Comment 和 DATA_PATH 参数；原有参数名称和顺序保持不变。
    """
    if source is None:
        source = "东方财富" if Load_Comment is Load_Comment_dfcf else "雪球"
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    file = DATA_PATH.joinpath(stock_name + '.csv')

    cut, df = Check_Point(stock_name, file, source)
    new_comments_list = Load_New_Comments(stock_name, max_search, rand_wage, cut, Load_Comment, source)
    new_comments_df = (
        pd.DataFrame(new_comments_list, columns=['stamp', 'text'])
        .drop_duplicates(subset=['stamp', 'text'])
        .set_index('stamp')
        .sort_index(ascending=False)
    )
    new_comments_df = new_comments_df[new_comments_df.index > cut]
    logger.info("[%s][%s] 增量数据整理完成，准备保存 | 抓取=%d条 | 去重并过滤后新增=%d条 | 原有=%d条 | 文件=%s", source, stock_name, len(new_comments_list), len(new_comments_df), len(df), file)

    up_dated_df = pd.concat([new_comments_df, df])
    up_dated_df.to_csv(file)


def main():
    rand_wage_poll = (max(40, RAND_WAGE[0]), max(60, RAND_WAGE[1], RAND_WAGE[0]))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S", handlers=[logging.StreamHandler(), logging.FileHandler(BASE_PATH / "run.log", encoding="utf-8")])
    with HS300_PATH.open(encoding="utf-8") as f:
        comp_list = [i.strip() for i in f if i.strip()]
    if not comp_list:
        raise ValueError("HS300 名单为空")

    while True:
        for stock_name in comp_list:
            # 每只股票只在外层等待一次，再依次抓取两个源。
            time.sleep(randint(*rand_wage_poll))
            try:
                Updates(stock_name, MAX_SEARCH_xueqiu, rand_wage_poll, Load_Comment_xueqiu, DATA_PATH_xueqiu)  # 原雪球最高后继1000条
            except Exception:
                logger.exception("[雪球][%s] 更新失败", stock_name)
            try:
                Updates(stock_name, MAX_SEARCH_dfcf, rand_wage_poll, Load_Comment_dfcf, DATA_PATH_dfcf)
            except Exception:
                logger.exception("[东方财富][%s] 更新失败", stock_name)


if __name__ == "__main__":
    main()
