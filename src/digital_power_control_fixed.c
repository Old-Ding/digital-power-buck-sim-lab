#include "digital_power_control_fixed.h"

#include <limits.h>

#define DP_FIXED_HALF ((int64_t)DP_FIXED_ONE / 2)

static DpFixed dp_fixed_saturate(int64_t value, bool *overflow)
{
    if (value > INT32_MAX)
    {
        *overflow = true;
        return INT32_MAX;
    }
    if (value < INT32_MIN)
    {
        *overflow = true;
        return INT32_MIN;
    }
    return (DpFixed)value;
}

static DpFixed dp_fixed_add(DpFixed left, DpFixed right, bool *overflow)
{
    return dp_fixed_saturate((int64_t)left + (int64_t)right, overflow);
}

static DpFixed dp_fixed_sub(DpFixed left, DpFixed right, bool *overflow)
{
    return dp_fixed_saturate((int64_t)left - (int64_t)right, overflow);
}

static DpFixed dp_fixed_mul(DpFixed left, DpFixed right, bool *overflow)
{
    int64_t product = (int64_t)left * (int64_t)right;

    // 统一在定点算术层做对称四舍五入，避免各控制模块各自处理舍入。
    product += product >= 0 ? DP_FIXED_HALF : -DP_FIXED_HALF;
    return dp_fixed_saturate(product / DP_FIXED_ONE, overflow);
}

static DpFixed dp_fixed_div(DpFixed numerator_value,
                            DpFixed denominator_value,
                            bool *overflow)
{
    int64_t numerator;
    int64_t denominator;
    int64_t half_denominator;

    if (denominator_value == 0)
    {
        *overflow = true;
        return numerator_value >= 0 ? INT32_MAX : INT32_MIN;
    }

    numerator = (int64_t)numerator_value * DP_FIXED_ONE;
    denominator = (int64_t)denominator_value;
    half_denominator = denominator >= 0 ? denominator / 2 : -denominator / 2;
    numerator += numerator >= 0 ? half_denominator : -half_denominator;
    return dp_fixed_saturate(numerator / denominator, overflow);
}

static DpFixed dp_fixed_clamp(DpFixed value, DpFixed low, DpFixed high)
{
    if (value < low)
    {
        return low;
    }
    if (value > high)
    {
        return high;
    }
    return value;
}

static DpFixed dp_fixed_abs_raw(DpFixed value)
{
    if (value == INT32_MIN)
    {
        return INT32_MAX;
    }
    return value < 0 ? -value : value;
}

static void dp_fixed_update_peak(DpFixed *peak, DpFixed value)
{
    const DpFixed magnitude = dp_fixed_abs_raw(value);
    if (magnitude > *peak)
    {
        *peak = magnitude;
    }
}

static DpFaultCode dp_fixed_detect_fault(const DpFixedControlConfig *cfg,
                                         const DpFixedControlInput *in,
                                         DpFixed vout_meas)
{
    if (in->iout >= cfg->ocp_threshold)
    {
        return DP_FAULT_OCP;
    }
    if (vout_meas >= cfg->ovp_threshold)
    {
        return DP_FAULT_OVP;
    }
    if (in->vin <= cfg->uvlo_threshold)
    {
        return DP_FAULT_UVLO;
    }
    if (in->temperature >= cfg->otp_threshold)
    {
        return DP_FAULT_OTP;
    }
    return DP_FAULT_NONE;
}

static void dp_fixed_update_state(DpFixedControlContext *ctx,
                                  const DpFixedControlConfig *cfg,
                                  const DpFixedControlInput *in,
                                  DpFaultCode active_fault)
{
    if (active_fault != DP_FAULT_NONE)
    {
        ctx->latched_fault = active_fault;
        ctx->state = DP_STATE_FAULT;
        return;
    }

    if (ctx->state == DP_STATE_FAULT)
    {
        if (in->clear_fault)
        {
            ctx->latched_fault = DP_FAULT_NONE;
            ctx->state = in->enable ? DP_STATE_SOFT_START : DP_STATE_IDLE;
            ctx->vref_cmd = 0;
            ctx->integrator = 0;
        }
        return;
    }

    if (!in->enable)
    {
        ctx->state = DP_STATE_IDLE;
        ctx->vref_cmd = 0;
        ctx->integrator = 0;
        return;
    }

    if (ctx->state == DP_STATE_IDLE)
    {
        ctx->state = DP_STATE_SOFT_START;
    }

    if (ctx->state == DP_STATE_SOFT_START && ctx->vref_cmd >= cfg->vref_final)
    {
        ctx->state = DP_STATE_RUN;
    }
}

static DpFixed dp_fixed_collect_peak(const DpFixedControlConfig *cfg,
                                     const DpFixedControlContext *ctx,
                                     const DpFixedControlInput *in,
                                     const DpFixedControlOutput *out)
{
    DpFixed peak = 0;

    dp_fixed_update_peak(&peak, cfg->vref_final);
    dp_fixed_update_peak(&peak, cfg->soft_start_step);
    dp_fixed_update_peak(&peak, cfg->kp);
    dp_fixed_update_peak(&peak, cfg->ki_step);
    dp_fixed_update_peak(&peak, cfg->duty_feedforward);
    dp_fixed_update_peak(&peak, cfg->duty_min);
    dp_fixed_update_peak(&peak, cfg->duty_max);
    dp_fixed_update_peak(&peak, cfg->adc_iir_alpha);
    dp_fixed_update_peak(&peak, cfg->ocp_threshold);
    dp_fixed_update_peak(&peak, cfg->ovp_threshold);
    dp_fixed_update_peak(&peak, cfg->uvlo_threshold);
    dp_fixed_update_peak(&peak, cfg->otp_threshold);
    dp_fixed_update_peak(&peak, in->vin);
    dp_fixed_update_peak(&peak, in->vout_adc);
    dp_fixed_update_peak(&peak, in->iout);
    dp_fixed_update_peak(&peak, in->temperature);
    dp_fixed_update_peak(&peak, ctx->vout_filter);
    dp_fixed_update_peak(&peak, ctx->vref_cmd);
    dp_fixed_update_peak(&peak, ctx->integrator);
    dp_fixed_update_peak(&peak, ctx->last_error);
    dp_fixed_update_peak(&peak, out->duty_raw);
    dp_fixed_update_peak(&peak, out->duty_cmd);
    dp_fixed_update_peak(&peak, out->error);
    dp_fixed_update_peak(&peak, out->p_term);
    return peak;
}

void DpFixedControl_DefaultConfig(DpFixedControlConfig *cfg)
{
    // 常量由 round(real * 2^20) 得到，控制周期已并入每周期增量和积分系数。
    cfg->vref_final = 12582912;
    cfg->soft_start_step = 1573;
    cfg->kp = 52429;
    cfg->ki_step = 419;
    cfg->duty_feedforward = 524288;
    cfg->duty_min = 0;
    cfg->duty_max = 681574;
    cfg->adc_iir_alpha = DP_FIXED_ONE;
    cfg->ocp_threshold = 6815744;
    cfg->ovp_threshold = 13841203;
    cfg->uvlo_threshold = 18874368;
    cfg->otp_threshold = 104857600;
}

void DpFixedControl_Init(DpFixedControlContext *ctx, const DpFixedControlConfig *cfg)
{
    ctx->state = DP_STATE_IDLE;
    ctx->latched_fault = DP_FAULT_NONE;
    ctx->vout_filter = cfg->vref_final;
    ctx->vref_cmd = 0;
    ctx->integrator = 0;
    ctx->last_error = 0;
    ctx->tick_count = 0u;
    ctx->arithmetic_overflow_count = 0u;
}

DpFixedControlOutput DpFixedControl_Step(DpFixedControlContext *ctx,
                                        const DpFixedControlConfig *cfg,
                                        const DpFixedControlInput *in)
{
    DpFixedControlOutput out;
    bool overflow = false;
    DpFixed alpha;
    DpFixed one_minus_alpha;
    DpFixed feedforward_scale;
    DpFixed duty_feedforward_cmd;

    ctx->tick_count++;

    alpha = dp_fixed_clamp(cfg->adc_iir_alpha, 0, DP_FIXED_ONE);
    one_minus_alpha = dp_fixed_sub(DP_FIXED_ONE, alpha, &overflow);
    ctx->vout_filter = dp_fixed_add(dp_fixed_mul(alpha, in->vout_adc, &overflow),
                                    dp_fixed_mul(one_minus_alpha, ctx->vout_filter, &overflow),
                                    &overflow);

    out.active_fault = dp_fixed_detect_fault(cfg, in, ctx->vout_filter);
    dp_fixed_update_state(ctx, cfg, in, out.active_fault);

    if (ctx->state == DP_STATE_SOFT_START)
    {
        ctx->vref_cmd = dp_fixed_add(ctx->vref_cmd, cfg->soft_start_step, &overflow);
        ctx->vref_cmd = dp_fixed_clamp(ctx->vref_cmd, 0, cfg->vref_final);
    }
    else if (ctx->state == DP_STATE_RUN)
    {
        ctx->vref_cmd = cfg->vref_final;
    }

    out.vout_meas = ctx->vout_filter;
    out.vref_cmd = ctx->vref_cmd;
    out.error = dp_fixed_sub(ctx->vref_cmd, ctx->vout_filter, &overflow);
    out.p_term = dp_fixed_mul(cfg->kp, out.error, &overflow);

    feedforward_scale = cfg->vref_final > 0
                            ? dp_fixed_div(ctx->vref_cmd, cfg->vref_final, &overflow)
                            : 0;
    feedforward_scale = dp_fixed_clamp(feedforward_scale, 0, DP_FIXED_ONE);
    duty_feedforward_cmd = dp_fixed_mul(cfg->duty_feedforward, feedforward_scale, &overflow);

    out.duty_raw = dp_fixed_add(dp_fixed_add(duty_feedforward_cmd, out.p_term, &overflow),
                                ctx->integrator,
                                &overflow);
    out.saturation = out.duty_raw > cfg->duty_max || out.duty_raw < cfg->duty_min;
    out.allow_integrate = !out.saturation ||
                          ((out.duty_raw > cfg->duty_max) && (out.error < 0)) ||
                          ((out.duty_raw < cfg->duty_min) && (out.error > 0));

    if (ctx->state == DP_STATE_RUN && out.allow_integrate)
    {
        ctx->integrator = dp_fixed_add(ctx->integrator,
                                       dp_fixed_mul(cfg->ki_step, out.error, &overflow),
                                       &overflow);
    }

    out.duty_raw = dp_fixed_add(dp_fixed_add(duty_feedforward_cmd, out.p_term, &overflow),
                                ctx->integrator,
                                &overflow);
    out.duty_cmd = dp_fixed_clamp(out.duty_raw, cfg->duty_min, cfg->duty_max);
    out.saturation = out.duty_cmd != out.duty_raw;

    // PWM 关断仍由状态机结果统一决定，定点化不改变控制职责边界。
    out.pwm_enable = (ctx->state == DP_STATE_SOFT_START || ctx->state == DP_STATE_RUN) &&
                     (ctx->latched_fault == DP_FAULT_NONE);
    if (!out.pwm_enable)
    {
        out.duty_cmd = 0;
    }

    ctx->last_error = out.error;
    if (overflow)
    {
        ctx->arithmetic_overflow_count++;
    }

    out.integrator = ctx->integrator;
    out.state = ctx->state;
    out.latched_fault = ctx->latched_fault;
    out.arithmetic_overflow = overflow;
    out.arithmetic_overflow_count = ctx->arithmetic_overflow_count;
    out.peak_abs_raw = dp_fixed_collect_peak(cfg, ctx, in, &out);
    return out;
}
