import logging
import pigpio
from .mcp3000base import ADC, RESOLUTION, CMD_FUNC, READ_FUNC

"""
ADコンバータ(SPIインターフェース)
MCP3000シリーズ用制御クラス

(ライブラリ) pigpio
spi_open(spi_channel, baud, spi_flags)

The Pi has two SPI peripherals: main and auxiliary.
         MISO  MOSI  SCLK  CE0 CE1 CE2
Main SPI:   9    10    11    8   7   -
Aux SPI:   19    20    21   18  17  16

:parameters:
  spi_channel:= 0-1 (0-2 for the auxiliary SPI)
  baud       := 32K - 125M
  spi_flags  := 
    spi_flags consists of the least significant 22 bits.
    21 20 19 18 17 16 15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
     b  b  b  b  b  b  R  T  n  n  n  n  W  A u2 u1 u0 p2 p1 p0  m  m

(例)
 pi.spi_open(0, 1000000, 0)   # CE0[GPIO8(16)], 1Mbps, main SPI
 pi.spi_open(1, 1000000, 0)   # CE1[GPIO7(18)], 1Mbps, main SPI
"""

# Dataシートから持ってくる: 電源電圧=3.3Vとする
# MCP3208
# Sample rate Vdd=VRef=5V   100k sps (sample per seconds)
#   **計算**  Vdd=VRef=3.3  60k sps
#     資料    Vdd=VRef=2.7  50k sps
# MCP3002
# Sample rate Vdd=VRef=5V   200k sps
#   **計算**  Vdd=VRef=3.3  100k sps
#             Vdd=VRef=2.7  75k sps
BAUD_DEFAULT = 100000  # 100kHz


class MCP3000:
    def __init__(self, ce, baud=BAUD_DEFAULT, v_ref=3.3, adc=ADC.MCP3002, logger=None):
        self.pi = pigpio.pi()
        self.spi_handle = self.pi.spi_open(ce, baud, 0)
        self.v_ref = v_ref
        self.cmd_func = CMD_FUNC[adc]
        self.read_func = READ_FUNC[adc]
        self.resolution = RESOLUTION[adc]
        self.logger = logger
        self.debug_once = logger is not None and (logger.getEffectiveLevel() <= logging.DEBUG)
        if self.debug_once:
            self.logger.debug("spi_handle: {}".format(self.spi_handle))
            self.logger.debug("v_ref: {}V, resolution: {}".format(self.v_ref, self.resolution))
            self.logger.debug("cmd_func: {}".format(self.cmd_func))
            self.logger.debug("read_func: {}".format(self.read_func))

    def analog_read(self, ch):
        din = self.cmd_func(ch)
        if self.debug_once:
            self.logger.debug("ch: {}, din: {}".format(ch, din))
        # spi_xfer(handle, data)
        (count, r_data) = self.pi.spi_xfer(self.spi_handle, din)
        adc_value = self.read_func(r_data)
        if self.debug_once:
            self.logger.debug("count: {}".format(count))
            for i in range(count):
                self.logger.debug("r_data[{}]: {:#04x}".format(i, r_data[i]))
            self.logger.debug("adc_value: [{0}] - {0:#04x}".format(adc_value))
        return adc_value

    def _adc_to_volt(self, adc_value):
        return adc_value * self.v_ref / float(self.resolution)

    def get_volt(self, ch):
        adc_value = self.analog_read(ch)
        volt = self._adc_to_volt(adc_value)
        return volt

    def cleanup(self):
        self.pi.spi_close(self.spi_handle)
        self.pi.stop()
