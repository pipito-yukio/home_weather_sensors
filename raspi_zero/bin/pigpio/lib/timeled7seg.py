import logging
from datetime import datetime
from .ht16k33 import HT16K33, BUS_NUM

"""
LEDドライバモジュール(HT16K33)を使ったコロン付き4桁7セグメントの時刻表示ライブラリ
"""


class LEDTime(HT16K33):
    DIGIT = 5
    # 表示文字定義: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':']
    SEG_CHAR_MAP = {
        '0': 0x3f, '1': 0x06, '2': 0x5b, '3': 0x4f, '4': 0x66,
        '5': 0x6d, '6': 0x7d, '7': 0x07, '8': 0x7f, '9': 0x67,
        ':': 0x02
    }

    # DIG1:COM0(0x00),DIG2:COM1(0x02),COLON:COM2(0x04),DIG3:COM3(0x06),DIG4:COM4(0x08)
    REG_START_ADDR = 0x00
    # コロン付きLEDのスタンバイ: '--:--'
    SEG_STANDBY = [0x40, 0x40, 0x02, 0x40, 0x40]
    # コロン付きLEDのエラー: 'EE:EE'
    SEG_ERRORS = [0x79, 0x79, 0x02, 0x79, 0x79]

    def __init__(self, pi, slave_addr, bus_number=BUS_NUM, brightness=None, logger=None):
        super().__init__(pi, slave_addr, bus_number, brightness=brightness, logger=logger)
        self.logger = logger
        self.debug_once = logger is not None and (logger.getEffectiveLevel() <= logging.DEBUG)

    def _make_display_time(self, unix_tmstmp: int):
        """
        UnixタイムスタンプからLED出力用のデータを生成する
        :param unix_tmstmp:
        :return:
        """
        datas = [0] * self.DIGIT
        str_time = datetime.fromtimestamp(unix_tmstmp).strftime("%H:%M")
        i = 0
        for tm in str_time:
            datas[i] = self.SEG_CHAR_MAP[tm]
            i += 1
        return datas

    def set_brightness(self, brightness):
        # 明るすぎるため調整する: 設定する明るさの1/2をマイナス
        # ※最小値は1でマイナスになることはない
        brightness -= (brightness // 2)
        super().set_brightness(brightness)

    def printTime(self, unix_tmstmp: int):
        """
        Unixタイムスタンプからの時刻を表示する
        :param unix_tmstmp: Unixタイムスタンプ
        """
        datas = self._make_display_time(unix_tmstmp)
        self.send_data(self.REG_START_ADDR, datas)

    def printError(self):
        """
        エラー表示: 'EE:EE'
        """
        self.send_data(self.REG_START_ADDR, self.SEG_ERRORS)

    def printStandby(self):
        """
        準備中表示: '--:--'
        """
        self.send_data(self.REG_START_ADDR, self.SEG_STANDBY)
