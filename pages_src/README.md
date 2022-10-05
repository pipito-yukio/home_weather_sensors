## 気象データ表示板の電子工作あれこれソースコード
---
### 1.実行に必要なシステムライブラリ
#### 1-1.インストール: python3-venv, **pigpio**, i2c-tools  

```shell
$sudo apt install python3-venv pigpio i2c-tools
```

#### 1-2.pigpioサービスの有効化と起動

```shell
$sudo apt install python3-venv pigpio i2c-tools
$sudo systemctl enable pigpiod.service
$sudo systemctl start pigpiod.service
```

### 2. Pythonプログラムの実行環境

#### 2-1.Python仮想環境の作成

```
$ mkdir py_venv
$ cd py_venv
$ python3 -m venv py_pigpio
```

#### 2-2.Python (**pigpio**) ライブラリのインストール
 
```shell
$ . py_pigpio/bin/activate
(py_pigpio) pip install -U pip
(py_pigpio) pip install pigpio
(py_pigpio) deactivate
```

### 3.Pythonプログラム実行

(例) 50_7seg4Digit/PrintTimeWith4DigitLED.py
```shell
$ . py_pigpio/bin/activate
(py_pigpio) python PrintTimeWith4DigitLED.py
```

pigpioライブラリについては下記をURLご覧ください  
**pigpio library**  
<https://pypi.org/project/pigpio/>  
<https://abyz.me.uk/rpi/pigpio/download.html>  
<https://github.com/joan2937/pigpio>
