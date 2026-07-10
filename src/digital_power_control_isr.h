#ifndef DIGITAL_POWER_CONTROL_ISR_H
#define DIGITAL_POWER_CONTROL_ISR_H

#include "digital_power_adc_map.h"
#include "digital_power_pwm_map.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct
{
    DpAdcMapConfig adc;
    DpFixedControlConfig control;
    DpPwmMapConfig pwm;
} DpControlIsrConfig;

typedef struct
{
    DpFixedControlContext control;
    DpPwmMapState pwm;
    uint32_t invocation_count;
} DpControlIsrContext;

typedef struct
{
    uint32_t invocation_count;
    uint32_t active_compare_before_update;
    uint32_t active_compare_after_update;
    uint32_t pending_compare_after_control;
    DpFixed vin;
    DpFixed vout;
    DpFixed iout;
    DpFixed temperature;
    DpFixed duty_cmd;
    DpControlState state;
    DpFaultCode active_fault;
    DpFaultCode latched_fault;
    bool pwm_enable_command;
    bool active_pwm_enable;
    bool adc_input_clamped;
    bool adc_physical_clamped;
    bool arithmetic_overflow;
} DpControlIsrOutput;

void DpControlIsr_DefaultConfig(DpControlIsrConfig *cfg);
void DpControlIsr_Init(DpControlIsrContext *ctx, const DpControlIsrConfig *cfg);
void DpControlIsr_OnPwmUpdate(DpControlIsrContext *ctx,
                              const DpControlIsrConfig *cfg,
                              const DpAdcRawSample *sample,
                              DpControlIsrOutput *out);

#endif
