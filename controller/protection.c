#include "config.h"
#include "protection.h"

PowerFaultCode protection_check(const PowerMeasurements *measurements)
{
    /*
     * 故障优先级集中在保护层，状态机只消费结果。
     * 这样后续调整阈值或优先级时，不需要在多个状态分支里找重复判断。
     */
    if (measurements->iout_a > POWER_OCP_THRESHOLD_A) {
        return POWER_FAULT_OCP;
    }
    if (measurements->vout_v > POWER_OVP_THRESHOLD_V) {
        return POWER_FAULT_OVP;
    }
    if (measurements->vin_v < POWER_UVLO_THRESHOLD_V) {
        return POWER_FAULT_UVLO;
    }
    if (measurements->temperature_c > POWER_OTP_THRESHOLD_C) {
        return POWER_FAULT_OTP;
    }

    return POWER_FAULT_NONE;
}
