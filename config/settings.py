"""修改本文件即可设置路径、请求参数与等待时间。"""
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parents[1]
DATA_PATH_xueqiu = BASE_PATH / "data" / "xueqiu"
DATA_PATH_dfcf = BASE_PATH / "data" / "dfcf"
HS300_PATH = BASE_PATH / "HS300"
MAX_SEARCH_xueqiu = 50
MAX_SEARCH_dfcf = 100
RAND_WAGE = (40, 60)  # 股评分页与换股等待，保留至少40–60秒

URL_xueqiu = 'https://www.xueqiu.com/query/v1/symbol/search/status.json'

HEADERS_xueqiu = {'authority': 'www.xueqiu.com',
 'accept': '*/*',
 'accept-language': 'zh-CN,zh;q=0.9',
 'elastic-apm-traceparent': '00-5190c72d20344ecb9d60a6df225e7e84-31d4399316a7aec3-01',
 'referer': 'https://www.xueqiu.com/S/SZ300308',
 'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
 'sec-ch-ua-mobile': '?0',
 'sec-ch-ua-platform': '"Windows"',
 'sec-fetch-dest': 'empty',
 'sec-fetch-mode': 'cors',
 'sec-fetch-site': 'same-origin',
 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
               'Chrome/112.0.0.0 Safari/537.36',
 'x-requested-with': 'XMLHttpRequest'}

PARAMS_xueqiu = {'count': '20', 'comment': '0', 'hl': '0', 'source': 'all', 'sort': 'time', 'q': '', 'type': '11'}

HEADERS_dfcf = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
 'Accept-Language': 'zh-CN,zh;q=0.9',
 'Cache-Control': 'max-age=0',
 'Connection': 'keep-alive',
 'Sec-Fetch-Dest': 'document',
 'Sec-Fetch-Mode': 'navigate',
 'Sec-Fetch-Site': 'same-site',
 'Sec-Fetch-User': '?1',
 'Upgrade-Insecure-Requests': '1',
 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
               'Chrome/155.0.0.0 Safari/537.36',
 'sec-ch-ua': '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
 'sec-ch-ua-mobile': '?0',
 'sec-ch-ua-platform': '"Windows"'}

URL_dfcf = 'https://guba.eastmoney.com/list,{stock_name}_{page_num}.html'

URL_index = 'https://push2.eastmoney.com/api/qt/clist/get'

HEADERS_index = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}

PARAMS_index = {'pz': 20,
 'po': 0,
 'np': 1,
 'fltt': 2,
 'invt': 2,
 'fid': 'f12',
 'fs': 'b:BK0500',
 'fields': 'f12,f13,f14'}

