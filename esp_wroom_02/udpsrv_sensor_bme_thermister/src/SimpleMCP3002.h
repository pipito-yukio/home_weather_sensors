#ifndef __SimpleMCP3002_h__
#define __SimpleMCP3002_h__
#include <Arduino.h>
#include <SPI.h>

union ReadData {
    uint16_t value;
    struct {
        uint8_t lowByte;
        uint8_t highByte;
    };
};

class SimpleMCP3002 {
public:
    // static const variables
    static const uint16_t RESOLUTION = 1024;
    static const int8_t INVALID_READ = -1; // Valid read: 0 - 1023
    // Constructor
    SimpleMCP3002(float vRef);
    // Destructor
    ~SimpleMCP3002(){};
    // Startup initialize
    void begin();
    // Public method
    uint16_t analogRead(uint8_t ch);
    // Utility method
    float getVolt(uint16_t adcVal);
    // DEBUG Use
    ReadData getReadData() { return mData; };

private:
    // member variable
    uint8_t mCsPin;
    float mVRef;
    SPISettings mSettings;
    // DEBUG Use
    ReadData mData;
};

#endif // __SimpleMCP3002_h__
