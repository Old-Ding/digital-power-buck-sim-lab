#include "digital_power_control.h"

static float dp_clamp(float value, float low, float high)
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

static DpFaultCode dp_detect_fault(const DpControlConfig *cfg,
                                   const DpControlInput *in,
                                   float vout_meas_v)
{
    if (in->iout_a >= cfg->ocp_threshold_a)
    {
        return DP_FAULT_OCP;
    }
    if (vout_meas_v >= cfg->ovp_threshold_v)
    {
        return DP_FAULT_OVP;
    }
    if (in->vin_v <= cfg->uvlo_threshold_v)
    {
        return DP_FAULT_UVLO;
    }
    if (in->temperature_c >= cfg->otp_threshold_c)
    {
        return DP_FAULT_OTP;
    }
    return DP_FAULT_NONE;
}

static bool dp_fault_absent(DpFaultCode fault)
{
    return fault == DP_FAULT_NONE;
}

static void dp_update_state(DpControlContext *ctx,
                            const DpControlConfig *cfg,
                            const DpControlInput *in,
                            DpFaultCode active_fault)
{
    if (!dp_fault_absent(active_fault))
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
            ctx->vref_cmd_v = 0.0f;
            ctx->integrator = 0.0f;
        }
        return;
    }

    if (!in->enable)
    {
        ctx->state = DP_STATE_IDLE;
        ctx->vref_cmd_v = 0.0f;
        ctx->integrator = 0.0f;
        return;
    }

    if (ctx->state == DP_STATE_IDLE)
    {
        ctx->state = DP_STATE_SOFT_START;
    }

    if (ctx->state == DP_STATE_SOFT_START && ctx->vref_cmd_v >= cfg->vref_final_v)
    {
        ctx->state = DP_STATE_RUN;
    }
}

void DpControl_DefaultConfig(DpControlConfig *cfg)
{
    cfg->ts_ctrl_s = 5.0e-6f;
    cfg->vref_final_v = 12.0f;
    cfg->soft_start_ramp_v_per_s = 300.0f;
    cfg->kp = 0.05f;
    cfg->ki = 80.0f;
    cfg->duty_feedforward = 0.5f;
    cfg->duty_min = 0.0f;
    cfg->duty_max = 0.65f;
    cfg->adc_iir_alpha = 1.0f;
    cfg->ocp_threshold_a = 6.5f;
    cfg->ovp_threshold_v = 13.2f;
    cfg->uvlo_threshold_v = 18.0f;
    cfg->otp_threshold_c = 100.0f;
}

void DpControl_Init(DpControlContext *ctx, const DpControlConfig *cfg)
{
    ctx->state = DP_STATE_IDLE;
    ctx->latched_fault = DP_FAULT_NONE;
    ctx->vout_filter_v = cfg->vref_final_v;
    ctx->vref_cmd_v = 0.0f;
    ctx->integrator = 0.0f;
    ctx->last_error_v = 0.0f;
    ctx->tick_count = 0u;
}

DpControlOutput DpControl_Step(DpControlContext *ctx,
                               const DpControlConfig *cfg,
                               const DpControlInput *in)
{
    DpControlOutput out;
    const float alpha = dp_clamp(cfg->adc_iir_alpha, 0.0f, 1.0f);

    ctx->tick_count++;

    ctx->vout_filter_v = alpha * in->vout_adc_v + (1.0f - alpha) * ctx->vout_filter_v;

    out.active_fault = dp_detect_fault(cfg, in, ctx->vout_filter_v);
    dp_update_state(ctx, cfg, in, out.active_fault);

    if (ctx->state == DP_STATE_SOFT_START)
    {
        ctx->vref_cmd_v += cfg->soft_start_ramp_v_per_s * cfg->ts_ctrl_s;
        ctx->vref_cmd_v = dp_clamp(ctx->vref_cmd_v, 0.0f, cfg->vref_final_v);
    }
    else if (ctx->state == DP_STATE_RUN)
    {
        ctx->vref_cmd_v = cfg->vref_final_v;
    }

    out.vout_meas_v = ctx->vout_filter_v;
    out.vref_cmd_v = ctx->vref_cmd_v;
    out.error_v = ctx->vref_cmd_v - ctx->vout_filter_v;
    out.p_term = cfg->kp * out.error_v;

    const float feedforward_scale = (cfg->vref_final_v > 0.0f) ? (ctx->vref_cmd_v / cfg->vref_final_v) : 0.0f;
    const float duty_feedforward_cmd = cfg->duty_feedforward * dp_clamp(feedforward_scale, 0.0f, 1.0f);

    // 软启动期间前馈 duty 跟随参考值爬坡，避免低参考值阶段直接给满 12V 稳态 duty。
    out.duty_raw = duty_feedforward_cmd + out.p_term + ctx->integrator;
    out.saturation = (out.duty_raw > cfg->duty_max) || (out.duty_raw < cfg->duty_min);

    // 积分器是唯一保存长期误差记忆的职责层，限幅时只允许它朝退出饱和方向移动。
    out.allow_integrate = !out.saturation ||
                          ((out.duty_raw > cfg->duty_max) && (out.error_v < 0.0f)) ||
                          ((out.duty_raw < cfg->duty_min) && (out.error_v > 0.0f));

    if (ctx->state == DP_STATE_RUN && out.allow_integrate)
    {
        ctx->integrator += cfg->ki * cfg->ts_ctrl_s * out.error_v;
    }

    out.duty_raw = duty_feedforward_cmd + out.p_term + ctx->integrator;
    out.duty_cmd = dp_clamp(out.duty_raw, cfg->duty_min, cfg->duty_max);
    out.saturation = (out.duty_cmd != out.duty_raw);

    // PWM 统一出口只看状态机结果，避免多个层级重复关断 duty。
    out.pwm_enable = (ctx->state == DP_STATE_SOFT_START || ctx->state == DP_STATE_RUN) &&
                     (ctx->latched_fault == DP_FAULT_NONE);
    if (!out.pwm_enable)
    {
        out.duty_cmd = 0.0f;
    }

    ctx->last_error_v = out.error_v;

    out.integrator = ctx->integrator;
    out.state = ctx->state;
    out.latched_fault = ctx->latched_fault;

    return out;
}
