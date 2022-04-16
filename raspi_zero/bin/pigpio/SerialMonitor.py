import argparse
import time
# Adafruit-Blinkaをインストールするとpyserialもインストールされる
# Adafruitライブラリを入れていない場合は単独でインストールする (pip install pyserial)
import serial
from log import logsetting

"""
ESP気象測定モジュールのシリアル出力をモニタする
【条件】
raspi-config
 (1)シリアル通信: 有効
 (2)シリアルコンソール: 無効
【接続】 UART (Universal Asynchronous Receiver Transmitter)
[ラズパイ側]       [ESP-WROOM-02]
             pin          pin
 GPIO14(TxD) 10 <--> RXD  11
 GPIO15(RxD) 12 <--> TXD  12
【シリアルデバイス】
 OK: serial0: /dev/ttyAMA0  # Blutooth
(NG: serial1: /dev/ttyS0)
"""

logger = logsetting.create_logger("main_app")

SERIAL_DEV = "/dev/ttyAMA0"
DEFAULT_BAUD_RATE = 9600 # ESP側のレートに合わせる


def monitor(ser):
    while 1:
        line = ser.readline()        # bytes
        line = line.decode('ascii', errors='ignore')
        line = line.replace("\r\n", "")
        line.rstrip()
        logger.debug(line)
        time.sleep(1.0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--baudrate", type=int, default=9600, choices=[9600, 115200], help="Baudrate (bps).")
    args = parser.parse_args()
    logger.info(args)

    ser = serial.Serial(SERIAL_DEV, args.baudrate) #, timeout=None)
    try:
        monitor(ser)
    except KeyboardInterrupt:
        ser.close()
