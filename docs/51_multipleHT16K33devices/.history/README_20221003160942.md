## ２つの同種 i2cデバイス (HT16K33 モジュール)を共存させる
---

既存のHT16K33モジュール(左側)に中国製【0.56インチ LEDディスプレイモジュール 4桁 7セグメント VK16K33 I2C Arduino用】を共存させるには  

上記2つのi2cデバイスは両方ともスレーブアドレスとして0x70を割り当てられているため、いずれか一方のデバイスのスレーブアドレスを変更する必要があります。

<div>
<img src="images/WeatherDataDisplayBeforeTimeModule.jpg">
</div>
<br/>

気象データ表示板に組み込んだHTK1633モジュールは秋月電子の【AE-HT16K33 16x8マトリクスドライバモジュール】。そして秋月電子からダウンロードした資料(PDF)がこれ。

赤枠で括られた３つの端子の組み合わせでハンダを盛ると**スレーブアドレスを0x71〜0x76**に変更可能となっています。

<div>
<img src="images/AE-HT16K33_i2c_address_change.jpg">
</div>
<br/>

気象データ表示板の**スレーブアドレスを変更するとすでに運用しいいる制御プログラムを修正する必要があるため避けたかった**のですが、中国製モジュールのデータシートが入手できなかったので今回は下記右側のように気象データ表示板のHT61K33モジュールのスレーブアドレスを **"0x71"** に変更することにしました。

<div>
<img src="images/MultiHT16K33Deviices.jpg">
</div>
<br/>

実際に中国製7セグ4桁LEDモジュール (コロン付き) を気象データ表示板に組み込み、データの到着時刻(測定時刻)を出力したのがこれ。  

<div>
<img src="images/WeatherDataDisplay_20220927.jpg">
</div>
<br/>

コンソールからi2cデバイスのスレーブアドレスを確認。  
同種のI2Cデバイスのスレーブアドレスが想定通りに２つ表示されています。

<div>
<img src="images/i2cdetect_multiHT16k33Devices.jpg">
</div>
<br/>


**複数のI2Cデバイスを連結する方法**については下記書籍に記載されているのでご覧になってください。

```
電子部品ごとの制御を学べる！
Ｒａｓｂｅｒｒｙ　Ｐｉ 電子工作　実践講座
改訂第２版
[ISBN978-4-8007-1242-4]

【2-5】デジタル通信方式(1) - I2C通信方式 -- 51ページ目
```

<div>
<img src="images/Book_Raspi_practice.jpg">
</div>
<br/>

制御プログラムについては下記をURLのコンテンツをご覧になってください。

<https://github.com/pipito-yukio/home_weather_sensors/tree/master/raspi_zero/README.md>
