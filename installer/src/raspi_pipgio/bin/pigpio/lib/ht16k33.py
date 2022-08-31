import logging

"""
LEDドライバモジュール(HT16K33)制御クラス for pigpio
"""

BUS_NUM = 1
BRIGHTNESS_BASE = 0xe0


class Brightness:
    HIGH = 0x0f
    MID = 0x08
    LOW = 0x04
    DIM = 0x02


class HT16K33:
    MEM_LAST = 0x0f

    def __init__(self, pi, slave_addr, bus_number=BUS_NUM, brightness=Brightness.MID, logger=None):
        self.pi = pi
        # i2c_handle = /dev/self.i2c_bus-1
        self.i2c_handle = pi.i2c_open(bus_number, slave_addr)
        self.logger = logger
        self.debug_once = logger is not None and (logger.getEffectiveLevel() <= logging.DEBUG)
        if logger is not None:
            logger.info("i2c_handle: {}".format(self.i2c_handle))
        self.opened = True
        # System setup: Turn on System oscillator(発振器) [0x20 + 1(on)]
        self.pi.i2c_write_byte(self.i2c_handle, 0x21)
        # Display setup: Display on [0x80 + 1(on)]
        self.pi.i2c_write_byte(self.i2c_handle, 0x81)
        # Brightness: [0xe0 + f{1,0,0,0}]
        self.pi.i2c_write_byte(self.i2c_handle, (BRIGHTNESS_BASE | brightness))

    def clear_memory(self):
        for m_addr in range(self.MEM_LAST + 1):
            self.pi.i2c_write_byte_data(self.i2c_handle, m_addr, 0x0)

    def debug_memory(self):
        for m_addr in range(0x0f + 1):
            r_data = self.pi.i2c_read_byte_data(self.i2c_handle, m_addr)
            if self.debug_once:
                self.logger.debug("r_data[{:#04x}]: {:#04x}".format(m_addr, r_data))

    def cleanup(self):
        # Poweroffでもメモリーの値は残っている
        self.clear_memory()
        # Display setup: Display off
        self.pi.i2c_write_byte(self.i2c_handle, 0x80)
        # System setup: Turn on System oscillator off
        self.pi.i2c_write_byte(self.i2c_handle, 0x20)
        self.pi.i2c_close(self.i2c_handle)
        self.opened = False

    # クリーンアップ途中でクローズに失敗した場合に単独で実行
    def force_close(self):
        if self.opened:
            self.pi.i2c_close(self.i2c_handle)

    def send_data(self, start_reg, datas):
        # 送信データを下位メモリから送信する
        reg = start_reg
        for i in range(len(datas)):
            val = datas[i]
            self.pi.i2c_write_byte_data(self.i2c_handle, reg, val)
            reg += 0x02

    def set_brightness(self, brightness):
        self.pi.i2c_write_byte(self.i2c_handle, (BRIGHTNESS_BASE | brightness))
