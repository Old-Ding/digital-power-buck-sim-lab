#ifndef DIGITAL_POWER_PWM_MAP_H
#define DIGITAL_POWER_PWM_MAP_H

#include "digital_power_control_fixed.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct
{
    uint32_t timer_clock_hz;
    uint32_t switching_frequency_hz;
    uint32_t period_counts;
    uint32_t auto_reload;
    uint32_t deadtime_counts;
    DpFixed duty_min;
    DpFixed duty_max;
} DpPwmMapConfig;

typedef struct
{
    uint32_t active_compare;
    uint32_t pending_compare;
    bool active_enable;
    bool pending_enable;
    bool update_pending;
} DpPwmMapState;

typedef struct
{
    DpFixed requested_duty;
    DpFixed clamped_duty;
    uint32_t pending_compare;
    bool duty_clamped;
    bool arithmetic_overflow;
} DpPwmQueueResult;

void DpPwmMap_DefaultConfig(DpPwmMapConfig *cfg);
void DpPwmMap_Init(DpPwmMapState *state);
DpPwmQueueResult DpPwmMap_Queue(DpPwmMapState *state,
                                const DpPwmMapConfig *cfg,
                                DpFixed duty,
                                bool pwm_enable);
void DpPwmMap_ApplyUpdateEvent(DpPwmMapState *state);
DpFixed DpPwmMap_CompareToDuty(const DpPwmMapConfig *cfg, uint32_t compare);

#endif
