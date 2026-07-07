#ifndef PROTECTION_H
#define PROTECTION_H

typedef enum {
    POWER_FAULT_NONE = 0,
    POWER_FAULT_OCP,
    POWER_FAULT_OVP,
    POWER_FAULT_UVLO,
    POWER_FAULT_OTP
} PowerFaultCode;

typedef struct {
    float vin_v;
    float vout_v;
    float iout_a;
    float temperature_c;
} PowerMeasurements;

PowerFaultCode protection_check(const PowerMeasurements *measurements);

#endif
