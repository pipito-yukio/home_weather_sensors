## 7セグ4桁(コロン付き)LED HT16K33モジュールに時刻を出力する
---

Amazonで購入した 中国製【0.56インチ LEDディスプレイモジュール 4桁 7セグメント HT16K33 I2C Arduino用】がこれ。  
Arduino用となっていますが**ラズベリーパイでも部品を追加することで利用可能になります。**

<div>
<img src="images/7seg4DigitVk16k33Module.jpg">
</div>
<br/>

ラズベリーパイでは下記のように**i2cバス用電圧レベル変換モジュール**をLEDモジュールの間に挟む必要があります。

<div>
<img src="images/7seg4DigitVk16k33ModuleForRaspi.jpg">
</div>
<br/>

擬似的に時刻を表示するスクリプトを実行
<div>
<img src="images/PrintTimeTo7seg4DigitVk16k33.jpg">
</div>
<br/>

コンソールから **i2cデバイス(番号=1)** と **i2cアドレス(0x70)** を確認

<div>
<img src="images/i2cDev_i2cdetect.jpg">
</div>
<br/>

参考にした**Adafruitのドキュメント(データシート)**
<https://www.marutsu.co.jp/contents/shop/marutsu/ds/adafruit-led-backpack.pdf>  
70ページの回路図を参考に**コロンをどのメモリに出力するかを整理した一覧表**

<div>
<img src="images/Vt16k33_table.jpg">
</div>
<br/>

擬似的に時刻を１分毎に表示し続けるスクリプトサンプルはこちら  
※**CTL+C でLEDが消灯してプログラムが終了する**

サンプルソースの簡単な説明
```
(1) 定数定義
  (1-1) i2cバス番号定数: /dev/i2c-1   # 「1」ハイフン後ろの数字 
  (1-2) メモリ空間上の桁数
  (1-3) 時刻文字列の文字に対応するバイトデータの辞書
  (1-4) DIG1〜DIG4の出力アドレスのコメント ※上記一覧のRAM構造(表)の右側部分
  (1-5) 開始メモリアドレス(DIG1)

(2) 関数定義
  (2-1) メモリのデータをログに出力する
    ※1. DEBUG用途
    ※2. 出力結果が期待通りにならない時、メモリの値をみることで原因があるかの助けになります
  (2-2) メモリをクリアする
  (2-3) モジュールのクリーンアップ
    ※この処理をわすれると電源を切らない限り

(3) システム時刻データ生成
  (3-1) 時刻文字列を格納するリストを5個分生成
  (3-2) システム日付を生成し時刻だけを取り出す ※必ず5桁になる
  　[生成例]
      from datetime import datetime 
      print(datetime.today().strftime("%H:%M"))
      "19:20"
  　[出力データリスト] "19:20" の場合のデータ
      datas = [0x06, 0x67, 0x02, 0x5b, 0x3f]

(4) データをメモリに出力: LEDに該当する数字とコロンが表示される
  (4-1) メモリの位置を先頭に設定する
  (4-2) 変数にデータを代入
  (4-3) メモリ位置にデータを書き込む
  (4-4) メモリ位置を 0x02 分進める
```


[PrintTimeWith4DigitLED.py]

```python
import argparse
import time
from datetime import datetime
import pigpio
from log import logsetting

"""
コロン付き4桁7セグLEDに時刻を表示
"""

logger = logsetting.create_logger("main_app")

BUS_NUM = 1                                                              # (1-1)
DIGIT = 5                                                                # (1-2)
# 表示文字定義: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':']
SEG_CHAR_MAP = {                                                         # (1-3)
    '0': 0x3f, '1': 0x06, '2': 0x5b, '3': 0x4f, '4': 0x66,
    '5': 0x6d, '6': 0x7d, '7': 0x07, '8': 0x7f, '9': 0x67,
    ':': 0x02
}

# [LED1] DIG1:COM0(0x00),DIG2:COM1(0x02),COLON:COM2(0x04),DIG3:COM3(0x06),DIG4:COM4(0x08) #(1-4)
REG_LED1 = 0x00  #(1-5)


def init(pi, slave_addr, bus_number=BUS_NUM):
    global i2c_handle
    # /dev/i2c-1
    i2c_handle = pi.i2c_open(bus_number, slave_addr)
    logger.info("i2c-handle: {}".format(i2c_handle))
    # 初期設定 ※コマンドのみ
    # System setup: Turn on System oscillator(発振器) [0x20 + 1(on)]
    pi.i2c_write_byte(i2c_handle, 0x21)
    # Display setup: Display on [0x80 + 1(on)]
    pi.i2c_write_byte(i2c_handle, 0x81)
    # Brightness: [0xe0 + f{1,1,1,1}]
    pi.i2c_write_byte(i2c_handle, 0xe4)        # ここの値を変えると明るさを変更できます


def read_memory():                             # (2-1)
    for m_addr in range(0x0f + 1):
        r_data = pi.i2c_read_byte_data(i2c_handle, m_addr)
        if debug_once:
            logger.debug("r_data[{:#04x}]: {:#04x}".format(m_addr, r_data))


def clear_memory():                            # (2-2)
    for m_addr in range(0x0f + 1):
        pi.i2c_write_byte_data(i2c_handle, m_addr, 0x00)


def cleanup():                                 # (2-3)
    # Poweroffでもメモリーの値は残っている
    clear_memory()
    # Display setup: Display off
    pi.i2c_write_byte(i2c_handle, 0x80)
    # System setup: Turn on System oscillator off
    pi.i2c_write_byte(i2c_handle, 0x20)
    pi.i2c_close(i2c_handle)


def make_time():                                   # (3)
    datas = [0] * DIGIT                            # (3-1)
    str_time = datetime.today().strftime("%H:%M")  # (3-2)
    i = 0
    for t in str_time:
        datas[i] = SEG_CHAR_MAP[t]                 # (3-3)
        i += 1
    return datas


def print_time():                                  (4)
    datas = make_time()
    reg = REG_LED1                                  # (4-1)
    for i in range(len(datas)):
        val = datas[i]                               # (4-2)
        pi.i2c_write_byte_data(i2c_handle, reg, val) # (4-3)
        reg += 0x02                                  # (4-4)


if __name__ == '__main__':
    global debug_once, i2c_slave_addr, pi
    pi = pigpio.pi()
    if not pi.connected:
        logger.warning("pigpiod not stated!")
        exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument("--i2c-address", type=str, default="0x70",
                        help="HT16K33 i2c address.")
    args = parser.parse_args()
    logger.info(args)
    i2c_slave_addr = int(args.i2c_address, 0)
    init(pi, i2c_slave_addr, BUS_NUM)

    try:
        debug_cnt, debug_once = 0, True
        while True:
            print_time()
            read_memory()
            debug_cnt += 1
            debug_once = (debug_cnt < 2)
            time.sleep(60)                      # ６０秒スリープ

    except KeyboardInterrupt:
        pass
    except Exception as err:
        raise err
    finally:
        cleanup()
    logger.info("Finished!")
```
