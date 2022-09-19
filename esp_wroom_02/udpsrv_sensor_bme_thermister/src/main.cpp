/*
   UDP Weather sensor Server with BME280 and Thermister for esp-wroom-02
*/
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include "SimpleMCP3002.h"

// Deep sleap time
const int32_t SLEEP_T = 600 * 1000000; // micro second, 600 sec (10 minute)

// Wi-Fi section
const char *SSID = "tlecomxg-abcdef";
const char *PASS = "12345filemee";
const IPAddress IP_DEVICE = IPAddress(192, 168, 0, 31);
const IPAddress IP_GATEWAY = IPAddress(192, 168, 0, 1);
const IPAddress IP_NETMASK = IPAddress(255, 255, 255, 0);
// UDP section
const char *SENDTO = "192.168.0.255"; // BroadCast
const char *DEVICE = "esp8266_1,";
const uint16_t PORT = 2222;

// MCP3002: channel=0,1
const uint8_t ADC_SAMPLES = 10;
const uint8_t CHANNEL_THERM = 0;
// Thermister section
const float THERM_B = 3435.0;
const float THERM_R0 = 10000.0;
const float THERM_R1 = 10000.0; // Divide register 10k
const float THERM_VREF = 3.3;
const float THERM_READ_INVALID = -9999.0;

SimpleMCP3002 adc(THERM_VREF);
Adafruit_BME280 bme;

/*
a.配列渡し
  ※関数の中で配列の要素数を知るすべがないため要素数を引数に指定する必要がある
   void debugSerialOut(ReadData *datas, int len)
   void debugSerialOut(ReadData datas[10], int len)
   void debugSerialOut(ReadData datas[], int len)
b.配列を参照渡し
  ※配列の[]の中に要素数を指定する必要がある
*/
void debugSerialOut(ReadData (&datas)[ADC_SAMPLES]) {
  int len = sizeof(datas) / sizeof(datas[0]);
  Serial.print("ReadData: [");
  for (int i = 0; i < len; i++) {
    ReadData rd = datas[i];
    char chrbuf[5];
    Serial.print("[0x");
    sprintf(chrbuf, "%x", rd.highByte);
    Serial.print(chrbuf);
    Serial.print(",0x");
    sprintf(chrbuf, "%x", rd.lowByte);
    Serial.print("]");
    if (i < ADC_SAMPLES) {
      Serial.print(",");
    }
  }
  Serial.print("]");
}

float getSamplingAdcValue(uint8_t ch, SimpleMCP3002 &mcp) {
  int adcSamples[ADC_SAMPLES];
#if defined(DEBUG)
  ReadData datas[ADC_SAMPLES];
#endif
  int i;
  Serial.print("CH<");
  Serial.print(ch);
  Serial.print(">: [");
  for (i = 0; i < ADC_SAMPLES; i++) {
    adcSamples[i] = mcp.analogRead(ch);
#if defined(DEBUG)
    datas[i] = mcp.getReadData();
#endif
    Serial.print(adcSamples[i]);
    if (i < (ADC_SAMPLES - 1)) {
      Serial.print(",");
    }
    delay(10);
  }
  Serial.print("], mean adc: ");
  uint16_t adcTotal = 0;
  for (i = 0; i < ADC_SAMPLES; i++) {
    adcTotal += adcSamples[i];
  }
  uint16_t meanAdc = round(1.0 * adcTotal / ADC_SAMPLES);
  Serial.println(meanAdc);
#if defined(DEBUG)
  debugSerialOut(datas)
#endif
  return meanAdc;
}

float getThermTemp() {
  double rx, xa, temp;
  uint16_t adcVal = getSamplingAdcValue(CHANNEL_THERM, adc);
  float outVolt = adc.getVolt(adcVal);
  Serial.print("Therm.outVolt: ");
  Serial.print(outVolt, 3);
  Serial.println(" V ");
  if (adcVal == 0 || outVolt < 0.01) {
    Serial.println("Thermister read invalid!");
    return THERM_READ_INVALID;
  }

  rx = THERM_R1 * ((THERM_VREF - outVolt) / outVolt);
  xa = log(rx / THERM_R0) / THERM_B;
  temp = (1 / (xa + 0.00335)) - 273.15;
  Serial.print("rx: ");
  Serial.print(rx);
  Serial.print(", xa: ");
  Serial.println(xa, 6);
  return (float)temp;
}

void measureSensors() {
  // Measure Thermister (Outdoor temparature)
  float thermTemp = getThermTemp();
  Serial.print("Therm Temp:");
  Serial.println(thermTemp, 1);
  // Wait BME280
  delay(50);

  // Measure BME280 senser (Room)
  float bmeTemp = bme.readTemperature();
  float humid = bme.readHumidity();             // %
  float pressure = bme.readPressure() / 100.0F; // hPa
  Serial.print("BME Temp:");
  Serial.println(bmeTemp, 1);

  // UDP Broadcast
  WiFiUDP udp;
  udp.begin(PORT);
  delay(100);
  udp.beginPacket(SENDTO, PORT);
  udp.print(DEVICE);
  if (thermTemp != THERM_READ_INVALID) {
    udp.print(thermTemp, 1);
  } else {
    udp.print(NAN);
  }
  udp.print(",");
  udp.print(bmeTemp, 1);
  udp.print(",");
  udp.print(humid, 1);
  udp.print(",");
  udp.print(pressure, 1);
  udp.endPacket();
  Serial.println("UDP End Packet.");
}

void setup() {
  unsigned long starttime = millis();
  Serial.begin(9600);
  Serial.println("Start.");

  adc.begin();
  bool status;
  status = bme.begin(0x76);
  if (!status) {
    Serial.println("Could not find a valid BME280 sensor!");
    while (1)
      ;
  }

  WiFi.mode(WIFI_STA);                            // Wi-Fi Station
  WiFi.config(IP_DEVICE, IP_GATEWAY, IP_NETMASK);
  WiFi.begin(SSID, PASS);
  while (WiFi.waitForConnectResult() != WL_CONNECTED) {
    Serial.println("Connection Failed! Rebooting...");
    delay(5000);
    ESP.restart();
  }

  Serial.println(WiFi.localIP());

  // Wait MCP3002
  delay(50);
  Serial.print("Setup complete: ");
  Serial.print((millis() - starttime) / 1000);
  Serial.println(" milli sec");

  // Mesure Sensors
  measureSensors();
  delay(200); // UDP sending wait

  // Calc Deep sleep time
  uint64_t sleeptime = SLEEP_T - (millis() - starttime) * 1000;
  Serial.print("Deep sleep time: ");
  Serial.print(sleeptime / 1000);
  Serial.println(" milli sec");
  ESP.deepSleep(sleeptime, WAKE_RF_DEFAULT);
  while (1) {
    delay(100); // 100ms Deep sleep wait
  }
}

void loop() {
}
