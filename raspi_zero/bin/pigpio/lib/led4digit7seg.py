import logging
from enum import Enum
from .ht16k33 import HT16K33, BUS_NUM

"""
LEDドライバモジュール(HT16K33)を使った4桁7セグメントLED表示ライブラリ for pigpio
最大4個まで出力
[部品]
 4桁7セグLED x 1〜4個
 16x8マトリクスLEDドライバモジュール(HT16K33) x 1個
   アノード側16 x カソード側8 出力可能なドライバ
   1.カソードコモンLEDの場合、最大4個の4桁7セグLEDを点灯可能。
    ※アノード側の16端子まで出力可能
   2.アノードコモンLEDの場合、最大2個の4桁7セグLEDを点灯可能。
    ※カソード側には8端子までしか出力できない
 I2Cバス用双方向電圧レベル変換モジュール(PCA9306) x 1個 
   ※ I2Cバスの電圧は3.3Vだが、HT16K33は5Vが必要なために変換が必要
  抵抗(330Ω) x 8個(A,B,C,D,E,F,G,DP)
 [接続]
 -------------  [PCA9306]  ------ [HT16K33]
 3.3V        -> VREF1 : VREF2(5V)
 5V                       ↑       -> VDD(5V)  
 GPIO3 [SCL] -> SCL1  : SCL2      -> SCL 
 GPIO2 [SDA] -> SDA1  : SDA2      -> SDA
 GND         ->       : GND       -> GND             
カソードコモンの場合               
 -----------  HT16K33  -----------  4桁7セグLED ---
 [1個目のLED]
              A0(ROW0) -> 330Ω ->  A  [11]
              A1(ROW1) -> 330Ω ->  B  [7]
              A2(ROW2) -> 330Ω ->  C  [4]
              A3(ROW3) -> 330Ω ->  D  [2]
              A4(ROW4) -> 330Ω ->  E  [1]
              A5(ROW5) -> 330Ω ->  F  [10]
              A6(ROW6) -> 330Ω ->  G  [5]
              A7(ROW7) -> 330Ω -> DP  [3]
              C0(COM0)          -> DIG1 [12]
              C1(COM1)          -> DIG2 [9]
              C2(COM2)          -> DIG3 [8]
              C3(COM3)          -> DIG4 [6]
 [2個目のLED] ROWを1個目のLEDと並列接続とする
              A0(ROW0) - A7(ROW7) ※1個目と同じ 
              C4(COM4)          -> DIG1 [12]
              C5(COM5)          -> DIG2 [9]
              C6(COM6)          -> DIG3 [8]
              C7(COM6)          -> DIG4 [6]
 [3個目のLED]
              A8(ROW8)  -> 330Ω ->  A  [11]
              A9(ROW9)  -> 330Ω ->  B  [7]
             A10(ROW10) -> 330Ω ->  C  [4]
             A11(ROW11) -> 330Ω ->  D  [2]
             A12(ROW12) -> 330Ω ->  E  [1]
             A13(ROW13) -> 330Ω ->  F  [10]
             A14(ROW14) -> 330Ω ->  G  [5]
             A15(ROW15) -> 330Ω -> DP  [3]
              C0(COM0) - C3(COM3)   ※1個目のLEDと並列接続とする
 [4個目のLED]  ROWを3個目のLEDと並列接続とする
              A8(ROW8) - A15(ROW15) ※3個目と同じ
              C4(COM4) - C7(COM7)   ※2個目のLEDと並列接続とする
■アノードコモンの場合(WayinTop Raspberry Pi用センサーキット) 
 [1個目のLED]
              C0(COM0) -> 330Ω ->  DP [3]
              C1(COM1) -> 330Ω ->  G  [5]
              C2(COM2) -> 330Ω ->  F  [10]
              C3(COM3) -> 330Ω ->  D  [2]
              C4(COM4) -> 330Ω ->  E  [1]
              C5(COM5) -> 330Ω ->  C  [4]
              C6(COM6) -> 330Ω ->  B  [7]
              C7(COM7) -> 330Ω ->  A  [11]
              A11(ROW11) -> DIG1 [12]
              A10(ROW10) -> DIG2 [9]
              A9(ROW9)   -> DIG3 [8]
              A8(ROW8)   -> DIG4 [6]
 [2個目のLED] COMを1個目のLEDと並列接続とする
              C0(COM0) - C7(COM7) ※1個目と同じ
              A3(ROW3)   -> DIG1 [12] 左から1桁目
              A2(ROW2)   -> DIG2 [9]
              A1(ROW1)   -> DIG3 [8]
              A0(ROW0)   -> DIG4 [6]  左から4桁目
[解説]
  4桁7セグメントLEDピン
     A0  A5           A1
DIG1  A   F DIG2 DIG3 B
 12  11  10   9   8   7
  ●   ●   ●   ●   ●   ●
      [省略]
  ●   ●   ●   ●   ●   ●
  1   2   3   4   5   6
  E   D   DP  C   G   DIG4
  A4  A3  A7  A2  A6   
"""

DIGIT = 4


def _make_digits(number):
    """
    数値を数字のリストに変換する (リストは逆順になる)
    (例) 123 ->  [3, 2, 1]
    :param number: 数値(最大4桁の整数 or マイナスの場合は3桁)
    :return: 数値を逆順にした数字のリスト
    """
    digits = []
    num, mod = number, 0
    for _ in range(DIGIT):
        num, mod = divmod(num, 10)
        digits.append(mod)
        if num == 0:
            break
    return digits


def _to_bins(val):
    """
    数値の2進数計算 ※アノードコモンのみ
    :param val:数値
    :return: 2進数のリスト
    """
    # 配列は8bit分初期化
    bins = [0] * 8
    num, mod = val, 0
    for i in range(8):
        num, mod = divmod(num, 2)
        bins[i] = mod
        if num == 0:
            break
    # ビット計算用に逆順にする
    return bins[::-1]


class LEDCommon(Enum):
    CATHODE = 0
    ANODE = 1


class LEDNumber(Enum):
    N1 = 0
    N2 = 1
    N3 = 2
    N4 = 3


class LED4digit7Seg(HT16K33):
    # 表示文字定義: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    SEG_CHAR = [0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x67]
    # ハイフン:'-'
    SEG_MINUS = 0x40
    # エラー:'EEEE'
    SEG_ERRORS = [0x79] * DIGIT
    # 測定不能:'----'
    SEG_OUTOFRANGE = [SEG_MINUS] * DIGIT
    # [LED1] DIG1:COM0(0x00),DIG2:COM1(0x02),DIG3:COM2(0x04),DIG4:COM3(0x06)
    #        ROW7(dp[3]), ROW6(g[5]), ROW5(f[10]), ROW4(e[1]), ROW3(d[2]), ROW2(c[4]), ROW1(b[7]), ROW0(a[11])
    REG_LED1 = 0x00
    # [LED2] DIG1:COM4(0x08),DIG2:COM5(0x0A),DIG3:COM6(0x0C),DIG4:COM7(0xEH)
    #        ROW7, ROW6(D6),..., ROW1, ROW0
    REG_LED2 = 0x08
    # [LED3] DIG1:COM0(0x01),DIG2:COM1(0x03),DIG3:COM2(0x05),DIG4:COM3(0x07)
    #        ROW15(dp[3]), ROW14(g[5]), ROW13(f[10]), ROW12(e[1]), ROW11(d[2]), ROW10(c[4]), ROW9(b[7]), ROW8(a[11])
    REG_LED3 = 0x01
    # [LED4] DIG1:COM4(0x09),DIG2:COM5(0x0B),DIG3:COM6(0x0D),DIG4:COM7(0xFH)
    #        ROW15, ROW14,..., ROW9, ROW8
    REG_LED4 = 0x09
    # アノードコモン
    REG_ANODE_LED1 = REG_LED1
    REG_ANODE_LED2 = REG_LED3
    # メモリ開始アドレスマップ
    STAREG_CATHODE = {LEDNumber.N1: REG_LED1, LEDNumber.N2: REG_LED2, LEDNumber.N3: REG_LED3, LEDNumber.N4: REG_LED4}
    STAREG_ANODE = {LEDNumber.N1: REG_ANODE_LED1, LEDNumber.N2: REG_ANODE_LED2}

    def __init__(self, pi, slave_addr, bus_number=BUS_NUM, common=LEDCommon.CATHODE,
                 brightness=None, logger=None):
        super().__init__(pi, slave_addr, bus_number, brightness=brightness, logger=logger)
        self.common = common
        self.logger = logger
        self.debug_once = logger is not None and (logger.getEffectiveLevel() <= logging.DEBUG)

    def _make_int_datas(self, digits):
        # カソードコモンLED用
        datas = [0] * DIGIT
        # 数値列(入力値の逆順で4桁目が先頭)を送信データの4桁目から格納する
        elem = DIGIT - 1
        for i in range(len(digits)):
            datas[elem] = self.SEG_CHAR[digits[i]]
            elem -= 1
        return datas

    def _convert_anode(self, cathode_datas):
        # カソードコモンLED用データをアノードコモンLED用に変換
        datas = [0] * 8
        for row in range(len(cathode_datas)):
            val = cathode_datas[row]
            val_bins = _to_bins(val)
            if self.debug_once:
                self.logger.debug("cathode_datas[{0}]: ({1}) - {1:#04x}".format(row, val))
                self.logger.debug("val_bins: {}".format(val_bins))
            # 8bit分: D7,D6,D5,D4, D3, D2, D1, D0
            #          0, 0, 0, 0, <<3,<<2,<<1,<<0
            for com_j in range(8):
                datas[com_j] = datas[com_j] | (val_bins[com_j] << (3 - row))
        return datas

    def _generate_int_datas(self, number):
        digits = _make_digits(number)
        if self.debug_once:
            self.logger.debug("number: {} -> digits: {}".format(number, digits))
        datas = self._make_int_datas(digits)
        if self.debug_once:
            self.logger.debug("datas: {}".format(datas))
        if self.common == LEDCommon.ANODE:
            # アノードコモンLEDに変換
            datas = self._convert_anode(datas)
        if self.debug_once:
            for i, data in enumerate(datas):
                self.logger.debug("datas[{}]: {:#04x}".format(i, data))
        return datas

    def _generate_float_datas(self, float_val):
        if self.debug_once:
            self.logger.debug("float_val: {}".format(float_val))

        t_datas = []
        # 数値が負なら先頭にマイナスのLED表現をセット
        if float_val < 0:
            t_datas.append(self.SEG_MINUS)
            # マイナス符号を除去
            float_val *= -1
        # 浮動小数点の場合は文字列に変換 ※小数点1桁で4捨5入
        s_val = str(round(1.0 * float_val, 1))
        has_dot = False
        for s in list(s_val):  # 数値文字列をリストに変換
            if s == '.':
                # ドットが出現したら前の数値に128をプラス
                t_datas[len(t_datas) - 1] += 128
                has_dot = True
                continue

            # ドット以外は数値
            t_datas.append(self.SEG_CHAR[ord(s) - 48])  # '0': 48, '1':49, ...

        # ドットの出現有無判定
        if not has_dot:
            # 出現しなかったら配列末尾の数値表現+128
            t_datas[len(t_datas) - 1] += 128
            # 小数点以下のゼロを補う
            t_datas.append(self.SEG_CHAR[0])

        if self.debug_once:
            for i in range(len(t_datas)):
                self.logger.debug("t_datas[{}]: {:#04x}".format(i, t_datas[i]))
        # 出力用4桁バッファに逆順に格納しなおす
        datas = [0] * DIGIT
        pos = DIGIT
        for i in range(len(t_datas) - 1, -1, -1):
            pos -= 1
            datas[pos] = t_datas[i]
        if self.debug_once:
            for i in range(len(datas)):
                self.logger.debug("datas[{}]: {:#04x}".format(i, datas[i]))
        return datas

    def printFloat(self, float_val, led_num=LEDNumber.N1):
        if float_val < -99.9 or float_val > 999.9:
            datas = self.SEG_OUTOFRANGE
            if self.logger is not None:
                self.logger.warning("float value is out of range: {}".format(float_val))
        else:
            datas = self._generate_float_datas(float_val)
            if self.common == LEDCommon.ANODE:
                # アノードコモン: アノードコモン用のデータに変換
                datas = self._convert_anode(datas)
        stareg = self.STAREG_CATHODE[led_num] if self.common == LEDCommon.CATHODE else self.STAREG_ANODE[led_num]
        self.send_data(stareg, datas)

    def printInt(self, int_val, led_num=LEDNumber.N1):
        if int_val < -999 or int_val > 9999:
            datas = self.SEG_OUTOFRANGE
            if self.logger is not None:
                self.logger.warning("int value is out of range: {}".format(int_val))
        else:
            datas = self._generate_int_datas(int_val)
        stareg = self.STAREG_CATHODE[led_num] if self.common == LEDCommon.CATHODE else self.STAREG_ANODE[led_num]
        self.send_data(stareg, datas)

    def printOutOfRange(self, led_num=LEDNumber.N1):
        """
        範囲外: '----'
        :param led_num: 出力先LED
        """
        stareg = self.STAREG_CATHODE[led_num] if self.common == LEDCommon.CATHODE else self.STAREG_ANODE[led_num]
        self.send_data(stareg, self.SEG_OUTOFRANGE)

    def printError(self, led_num=LEDNumber.N1):
        """
        測定値エラー: 'EEEE'
        :param led_num: 出力先LED
        """
        stareg = self.STAREG_CATHODE[led_num] if self.common == LEDCommon.CATHODE else self.STAREG_ANODE[led_num]
        self.send_data(stareg, self.SEG_ERRORS)
