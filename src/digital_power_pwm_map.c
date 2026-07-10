#include "digital_power_pwm_map.h"

#include <limits.h>

static DpFixed dp_pwm_clamp_fixed(DpFixed value, DpFixed low, DpFixed high, bool *clamped)
{
    if (value < low)
    {
        *clamped = true;
        return low;
    }
    if (value > high)
    {
        *clamped = true;
        return high;
    }
    return value;
}

static uint32_t dp_pwm_duty_to_compare(DpFixed duty,
                                       uint32_t period_counts,
                                       bool *overflow)
{
    int64_t numerator = (int64_t)duty * period_counts + DP_FIXED_ONE / 2;
    int64_t compare = numerator / DP_FIXED_ONE;

    if (compare < 0)
    {
        compare = 0;
    }
    if (compare > period_counts)
    {
        compare = period_counts;
        *overflow = true;
    }
    return (uint32_t)compare;
}

void DpPwmMap_DefaultConfig(DpPwmMapConfig *cfg)
{
    cfg->timer_clock_hz = 170000000u;
    cfg->switching_frequency_hz = 200000u;
    cfg->period_counts = 425u;
    cfg->auto_reload = 425u;
    cfg->deadtime_counts = 17u;
    cfg->duty_min = 0;
    cfg->duty_max = 681574;
}

void DpPwmMap_Init(DpPwmMapState *state)
{
    state->active_compare = 0u;
    state->pending_compare = 0u;
    state->active_enable = false;
    state->pending_enable = false;
    state->update_pending = false;
}

DpPwmQueueResult DpPwmMap_Queue(DpPwmMapState *state,
                                const DpPwmMapConfig *cfg,
                                DpFixed duty,
                                bool pwm_enable)
{
    DpPwmQueueResult result;
    bool clamped = false;
    bool overflow = false;

    result.requested_duty = duty;
    result.clamped_duty = dp_pwm_clamp_fixed(duty, cfg->duty_min, cfg->duty_max, &clamped);
    result.pending_compare = dp_pwm_duty_to_compare(result.clamped_duty,
                                                     cfg->period_counts,
                                                     &overflow);

    state->pending_compare = pwm_enable ? result.pending_compare : 0u;
    state->pending_enable = pwm_enable;
    state->update_pending = true;

    // 保护关断必须立即关闭门极；重新使能仍等待更新事件，避免周期中间开启 PWM。
    if (!pwm_enable)
    {
        state->active_enable = false;
    }

    result.duty_clamped = clamped;
    result.arithmetic_overflow = overflow;
    return result;
}

void DpPwmMap_ApplyUpdateEvent(DpPwmMapState *state)
{
    if (!state->update_pending)
    {
        return;
    }
    state->active_compare = state->pending_compare;
    state->active_enable = state->pending_enable;
    state->update_pending = false;
}

DpFixed DpPwmMap_CompareToDuty(const DpPwmMapConfig *cfg, uint32_t compare)
{
    int64_t numerator;

    if (compare > cfg->period_counts)
    {
        compare = cfg->period_counts;
    }
    numerator = (int64_t)compare * DP_FIXED_ONE + cfg->period_counts / 2u;
    if (numerator / cfg->period_counts > INT32_MAX)
    {
        return INT32_MAX;
    }
    return (DpFixed)(numerator / cfg->period_counts);
}
