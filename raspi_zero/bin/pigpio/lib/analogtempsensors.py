import math

"""
各種温度センサー用測定温度取得関数
  アナログIC温度センサー
  サーミスタ
"""

REGISTER_10K = 10000
_T0_25 = 25.0
_T_KELVIN = 273.15


def temperature_LM61CIZ(v_out):
    """
    LM61CIZ
    (計算式) T = 100 × Vout - 60 (V)
    :param v_out: 測定電圧 (ADコンバータ)
    :return: 測定温度 [℃]
    """
    temp = 100.0 * v_out - 60.0
    return temp


def temperature_MCP9700(v_out):
    """
    MCP9700
    (計算式) T = 100 × Vout - 50 (V)
    :param v_out: 測定電圧 (ADコンバータ)
    :return: 測定温度 [℃]
    """
    temp = 100.0 * v_out - 50.0
    return temp


def temperature_thermistor(v_out, r1, b0, t0=_T0_25, r0=REGISTER_10K, v_ref=3.3, logger=None):
    """
    サーミスタの測定温度を計算
    :param v_out: 測定電圧 (ADコンバータ)
    :param r1: サーミスタに接続した抵抗(Ω)
    :param b0: サーミスタのB定数
    :param t0: サーミスタ25℃
    :param r0: t0の時の抵抗(Ω)
    :param v_ref: 電源電圧
    :return: 測定温度 [℃]
    """
    rx = ((v_ref - v_out) / v_out) * r1
    xa = math.log(float(rx) / float(r0)) / float(b0)
    xb = 1 / (_T_KELVIN + t0)
    temp = (1 / (xa + xb)) - _T_KELVIN
    if logger is not None:
        logger.debug("rx: {:#.2f}, xa: {:#.5f}, xb: {:#.5f}, temp: {:#.2f}".format(rx, xa, xb, temp))
    return temp
