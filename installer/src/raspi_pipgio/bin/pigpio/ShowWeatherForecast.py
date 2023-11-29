import logging
import os
import subprocess
from urllib.parse import quote_plus
import util.file_util as FU
from log import logsetting

"""
当日の最新の天気予報をサブプロセスでOLEDに出力する
[ファイル]
  $PATH_DATAS/WeatherForecast.txt
"""

logger = logsetting.create_logger("main_app")

isLogLevelDebug = False

if __name__ == '__main__':
    isLogLevelDebug = logger.getEffectiveLevel() <= logging.DEBUG
    home_datas_dir = os.environ.get("PATH_DATAS", "/home/pi/datas")
    conf_app = FU.read_json(os.path.join(home_datas_dir, "conf_weatherforecast.json"))
    # 天気予報ファイル
    filename = conf_app["filename"]
    file_path = os.path.join(home_datas_dir, filename)
    encoded = ''
    if os.path.exists(file_path):
        today_list = FU.read_text(file_path)
        if len(today_list) > 0:
            # 先頭が最新
            latest = today_list[0]
            if isLogLevelDebug:
                logger.debug("latest: {}".format(latest))
            # 末尾の出力メッセージ
            latest = latest.split(",")
            encoded = quote_plus(latest[1])
            if isLogLevelDebug:
                logger.debug(encoded)

    script = conf_app["displayMessage"]["script"]
    if len(encoded) > 0:
        exec_status = subprocess.run([script, "--encoded-message", encoded, "--has-list"])
    else:
        # 取得データが無い場合のメッセージ
        encoded = conf_app["displayMessage"]["emptyData"]
        encoded = quote_plus(encoded)
        exec_status = subprocess.run([script, "--encoded-message", encoded])
    logger.info("Subprocess DisplayMessage terminated: {}".format(exec_status))
