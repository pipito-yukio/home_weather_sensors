from enum import Enum

"""
ADコンバータ共通定数、関数
"""


class ADC(Enum):
    MCP3002 = 0
    MCP3208 = 4


def _create_cmd_3002(ch):
    """
    コマンドデータ生成: 2byte
     (1)最初の8bit: [x,1(*1),1(*2),0,(*3), 1(*4),x,x,x]
     (2)最後の8bit: [0,0,0,0,0,0,0,0] ※クロック生成用
        x: 何でもかまわないが 0を設定
       (*1) Start bit:1
       (*2) SIGL/DIFF: Single End=1, Differential=0
       (*3) ODD/SIGN: 0 | 1
    :param ch: アナログ入力チャネル (0 | 1)の2チャネル
    :return: 2バイトのリスト
    """
    return [(0x68 | ch << 4), 0x00]


def _create_cmd_3208(ch):
    """
    コマンドデータ生成: 3byte
     (1)最初の8bit: [0,0,0,0,0,1(*1),1(*2),D2] -> 0x06 | 0x07
     (2)次の8bit:   [D1,D0,0,0,0,0,0,0]        -> 0x00, 0x04, 0x08, 0x0c
     (3)最後の8bit: [0,0,0,0,0,0,0,0]          -> 0x00
       (*1) Start bit:1
       (*2) SIGL/DIFF: Single End=1, Differential=0
       D2[=0|1], D1[=0|1], D0[=0|1]: Channel0〜7の選択
       ch  D2 | D1 | D0
        0  0    0    0
        1  0    0    1
        2  0    1    0
        3  0    1    1
        4  1    0    0
        5  1    0    1
        6  1    1    0
        7  1    1    1
       (生成例)
          ch=5, [0x07, 0x40, 0x00]
    :param ch: アナログ入力チャネル
    :return: コマンドデータ(リスト)
    """
    return [0b00000110 + (ch >> 2), (ch & 0b011) << 6, 0]


def _analog_read_3002(r_data):
    """
    アナログ値を計算
     ※以下はDatasheetに記載あり
     (1)最初の8bit(r_data[0]): [x,x,x,x,x,0(*1),B9,B8]
     (2)最後の8bit(r_data[1]): [B7,B6,B5,B4,B3,B2,B1,B0]
    :param r_data: 2バイト
    :return: アナログ値10bit
    """
    return (r_data[0] << 8 | r_data[1]) & 0x3ff


def _analog_read_3208(r_data):
    """
    アナログ値を計算
     ※以下はDatasheetに記載あり
     (1)最初の8bit(r_data[0]): [x,x,x,x,x,x,x,x] ※読み捨て
     (2)次の8bit(r_data[1]): [x,x,x,0(*1),B11,B10,B9,B8]
     (3)最後の8bit(r_data[2]): [B7,B6,B5,B4,B3,B2,B1,B0]
       (*1) Null bit
    :param r_data: 3バイト
    :return: アナログ値12bit
    """
    return (r_data[1] & 0x0f) << 8 | r_data[2]


RESOLUTION = {ADC.MCP3002: 1023, ADC.MCP3208: 4095}  # resolution-1: 0v
CMD_FUNC = {ADC.MCP3002: _create_cmd_3002, ADC.MCP3208: _create_cmd_3208}
READ_FUNC = {ADC.MCP3002: _analog_read_3002, ADC.MCP3208: _analog_read_3208}
