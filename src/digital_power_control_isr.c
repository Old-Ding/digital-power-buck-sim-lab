#include "digital_power_control_isr.h"

void DpControlIsr_DefaultConfig(DpControlIsrConfig *cfg)
{
    DpAdcMap_DefaultConfig(&cfg->adc);
    DpFixedControl_DefaultConfig(&cfg->control);
    DpPwmMap_DefaultConfig(&cfg->pwm);
}

void DpControlIsr_Init(DpControlIsrContext *ctx, const DpControlIsrConfig *cfg)
{
    DpFixedControl_Init(&ctx->control, &cfg->control);
    DpPwmMap_Init(&ctx->pwm);
    ctx->invocation_count = 0u;
}

void DpControlIsr_OnPwmUpdate(DpControlIsrContext *ctx,
                              const DpControlIsrConfig *cfg,
                              const DpAdcRawSample *sample,
                              DpControlIsrOutput *out)
{
    DpAdcMapResult adc_result;
    DpFixedControlOutput control_result;
    DpPwmQueueResult pwm_result;

    ctx->invocation_count++;
    out->invocation_count = ctx->invocation_count;

    // 更新事件先让上一周期排队的比较值生效，本周期计算只准备下一周期输出。
    out->active_compare_before_update = ctx->pwm.active_compare;
    DpPwmMap_ApplyUpdateEvent(&ctx->pwm);
    out->active_compare_after_update = ctx->pwm.active_compare;

    adc_result = DpAdcMap_Convert(&cfg->adc, sample);
    control_result = DpFixedControl_Step(&ctx->control,
                                         &cfg->control,
                                         &adc_result.controller_input);
    pwm_result = DpPwmMap_Queue(&ctx->pwm,
                                &cfg->pwm,
                                control_result.duty_cmd,
                                control_result.pwm_enable);

    out->pending_compare_after_control = pwm_result.pending_compare;
    out->vin = adc_result.controller_input.vin;
    out->vout = adc_result.controller_input.vout_adc;
    out->iout = adc_result.controller_input.iout;
    out->temperature = adc_result.controller_input.temperature;
    out->duty_cmd = control_result.duty_cmd;
    out->state = control_result.state;
    out->active_fault = control_result.active_fault;
    out->latched_fault = control_result.latched_fault;
    out->pwm_enable_command = control_result.pwm_enable;
    out->active_pwm_enable = ctx->pwm.active_enable;
    out->adc_input_clamped = adc_result.input_code_clamped;
    out->adc_physical_clamped = adc_result.physical_value_clamped;
    out->arithmetic_overflow = adc_result.arithmetic_overflow ||
                               control_result.arithmetic_overflow ||
                               pwm_result.arithmetic_overflow;
}
