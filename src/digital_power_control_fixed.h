#ifndef DIGITAL_POWER_CONTROL_FIXED_H
#define DIGITAL_POWER_CONTROL_FIXED_H

#include "digital_power_control.h"

#include <stdbool.h>
#include <stdint.h>

#define DP_FIXED_FRAC_BITS 20
#define DP_FIXED_ONE ((int32_t)1048576)

typedef int32_t DpFixed;

typedef struct
{
    DpFixed vref_final;
    DpFixed soft_start_step;
    DpFixed kp;
    DpFixed ki_step;
    DpFixed duty_feedforward;
    DpFixed duty_min;
    DpFixed duty_max;
    DpFixed adc_iir_alpha;
    DpFixed ocp_threshold;
    DpFixed ovp_threshold;
    DpFixed uvlo_threshold;
    DpFixed otp_threshold;
} DpFixedControlConfig;

typedef struct
{
    bool enable;
    bool clear_fault;
    DpFixed vin;
    DpFixed vout_adc;
    DpFixed iout;
    DpFixed temperature;
} DpFixedControlInput;

typedef struct
{
    bool pwm_enable;
    DpFixed duty_cmd;
    DpFixed duty_raw;
    DpFixed vout_meas;
    DpFixed vref_cmd;
    DpFixed error;
    DpFixed p_term;
    DpFixed integrator;
    bool saturation;
    bool allow_integrate;
    DpControlState state;
    DpFaultCode latched_fault;
    DpFaultCode active_fault;
    bool arithmetic_overflow;
    uint32_t arithmetic_overflow_count;
    DpFixed peak_abs_raw;
} DpFixedControlOutput;

typedef struct
{
    DpControlState state;
    DpFaultCode latched_fault;
    DpFixed vout_filter;
    DpFixed vref_cmd;
    DpFixed integrator;
    DpFixed last_error;
    uint32_t tick_count;
    uint32_t arithmetic_overflow_count;
} DpFixedControlContext;

void DpFixedControl_DefaultConfig(DpFixedControlConfig *cfg);
void DpFixedControl_Init(DpFixedControlContext *ctx, const DpFixedControlConfig *cfg);
DpFixedControlOutput DpFixedControl_Step(DpFixedControlContext *ctx,
                                        const DpFixedControlConfig *cfg,
                                        const DpFixedControlInput *in);

#endif
