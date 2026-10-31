from pathlib import Path
import logging
import pandas as pd

logger = logging.getLogger(__name__)

WORK_PATH=Path("./data copy")
Archive_PATH=Path("./Archive")
CACHE_SIZE=100

def dataArchive(file_path):

    df=pd.read_csv(file_path)
    if len(df)<=CACHE_SIZE:
        return


    df_appdix=df.iloc[CACHE_SIZE:]

    target_path=Archive_PATH / file_path.relative_to(WORK_PATH)
    target_path.parent.mkdir(parents=True,exist_ok=True)

    if not target_path.exists():
        df_archived=df_appdix
    else:
        df_archived=pd.concat([df_appdix,pd.read_csv(target_path)]).drop_duplicates().sort_values('stamp', ascending=False)

    df_cache=df.iloc[:CACHE_SIZE]

    df_archived.to_csv(target_path,index=False)
    df_cache.to_csv(file_path,index=False)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    if not WORK_PATH.is_dir():
        logger.error("缓存源目录不存在或不是目录：%s", WORK_PATH)
        return

    files = list(WORK_PATH.rglob("*.csv"))
    if not files:
        logger.warning("缓存源目录中没有 CSV 文件：%s", WORK_PATH)
        return

    failed = 0
    for file_path in files:
        try:
            dataArchive(file_path)
        except Exception:
            failed += 1
            logger.exception("归档失败，继续处理其他文件：%s", file_path)

    logger.info("处理完成：共 %d 个文件，成功 %d 个，失败 %d 个", len(files), len(files) - failed, failed)

if __name__ == "__main__":
    main()
