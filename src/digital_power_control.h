#ifndef DIGITAL_POWER_CONTROL_H
#define DIGITAL_POWER_CONTROL_H

#include <stdbool.h>
#include <stdint.h>

typedef enum
{
    DP_STATE_IDLE = 0,
    DP_STATE_SOFT_START = 1,
    DP_STATE_RUN = 2,
    DP_STATE_FAULT = 3
} DpControlState;

typedef enum
{
    DP_FAULT_NONE = 0,
    DP_FAULT_OCP = 1,
    DP_FAULT_OVP = 2,
    DP_FAULT_UVLO = 3,
    DP_FAULT_OTP = 4
} DpFaultCode;

typedef struct
{
    float ts_ctrl_s;
    float vref_final_v;
    float soft_start_ramp_v_per_s;
    float kp;
    float ki;
    float duty_feedforward;
    float duty_min;
    float duty_max;
    float adc_iir_alpha;
    float ocp_threshold_a;
    float ovp_threshold_v;
    float uvlo_threshold_v;
    float otp_threshold_c;
} DpControlConfig;

typedef struct
{
    bool enable;
    bool clear_fault;
    float vin_v;
    float vout_adc_v;
    float iout_a;
    float temperature_c;
} DpControlInput;

typedef struct
{
    bool pwm_enable;
    float duty_cmd;
    float duty_raw;
    float vout_meas_v;
    float vref_cmd_v;
    float error_v;
    float p_term;
    float integrator;
    bool saturation;
    bool allow_integrate;
    DpControlState state;
    DpFaultCode latched_fault;
    DpFaultCode active_fault;
} DpControlOutput;

typedef struct
{
    DpControlState state;
    DpFaultCode latched_fault;
    float vout_filter_v;
    float vref_cmd_v;
    float integrator;
    float last_error_v;
    uint32_t tick_count;
} DpControlContext;

void DpControl_DefaultConfig(DpControlConfig *cfg);
void DpControl_Init(DpControlContext *ctx, const DpControlConfig *cfg);
DpControlOutput DpControl_Step(DpControlContext *ctx,
                               const DpControlConfig *cfg,
                               const DpControlInput *in);

#endif
