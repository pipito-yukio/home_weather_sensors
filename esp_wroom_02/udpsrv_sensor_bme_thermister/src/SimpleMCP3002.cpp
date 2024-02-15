#include "SimpleMCP3002.h"

// Constructor
SimpleMCP3002::SimpleMCP3002(float vRef) :
    mCsPin(PIN_SPI_SS),
    mVRef(vRef),
    mSettings(SPISettings(1000000, MSBFIRST, SPI_MODE0)/*Clock Frequency: 100kHz */) {
}

void SimpleMCP3002::begin(void) {
    pinMode(mCsPin, OUTPUT);
    digitalWrite(mCsPin, HIGH);
    SPI.begin();
}

uint16_t SimpleMCP3002::analogRead(uint8_t ch) {
    SPI.beginTransaction(mSettings);
    digitalWrite(mCsPin, LOW);
    byte _highByte = SPI.transfer(0b01101000 | (ch << 4));
    byte _lowByte = SPI.transfer(0x00);
    digitalWrite(mCsPin, HIGH);
    SPI.endTransaction();
    // Read analog value.
    mData.highByte = _highByte & 0x03;
    mData.lowByte = _lowByte;
    // MCP3002: 0 - 1023
    if (mData.value >= 0 && mData.value < RESOLUTION) {
        return mData.value;
    }

    return SimpleMCP3002::INVALID_READ;
}

float SimpleMCP3002::getVolt(uint16_t adcVal) {
    return adcVal * mVRef / RESOLUTION;
}
