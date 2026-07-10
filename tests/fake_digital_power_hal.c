#include "fake_digital_power_hal.h"

#include <stdio.h>
#include <string.h>

static void fake_log(FakeDpHalState *state, const char *event)
{
    if (state->event_count >= FAKE_DP_HAL_MAX_EVENTS)
    {
        return;
    }
    snprintf(state->events[state->event_count],
             FAKE_DP_HAL_EVENT_NAME_CAPACITY,
             "%s",
             event);
    state->event_count++;
}

static void fake_pwm_update_event(void *user_context)
{
    FakeDpHalState *state = (FakeDpHalState *)user_context;
    fake_log(state, "pwm_update");
    state->active_compare = state->pending_compare;
    state->active_enable = state->pending_enable;
}

static bool fake_read_adc_sample(void *user_context, DpAdcRawSample *sample)
{
    FakeDpHalState *state = (FakeDpHalState *)user_context;
    fake_log(state, "adc_read");
    if (state->adc_sample_valid)
    {
        *sample = state->adc_sample;
    }
    return state->adc_sample_valid;
}

static void fake_write_pwm_preload(void *user_context, uint32_t compare, bool enable)
{
    FakeDpHalState *state = (FakeDpHalState *)user_context;
    fake_log(state, "pwm_write");
    state->pending_compare = compare;
    state->pending_enable = enable;
}

static void fake_disable_pwm_immediate(void *user_context)
{
    FakeDpHalState *state = (FakeDpHalState *)user_context;
    fake_log(state, "pwm_disable");
    state->active_enable = false;
}

static uint32_t fake_enter_critical(void *user_context)
{
    FakeDpHalState *state = (FakeDpHalState *)user_context;
    fake_log(state, "critical_enter");
    state->critical_depth++;
    return state->critical_depth;
}

static void fake_exit_critical(void *user_context, uint32_t key)
{
    FakeDpHalState *state = (FakeDpHalState *)user_context;
    (void)key;
    fake_log(state, "critical_exit");
    if (state->critical_depth > 0u)
    {
        state->critical_depth--;
    }
}

static void fake_service_communication(void *user_context)
{
    FakeDpHalState *state = (FakeDpHalState *)user_context;
    fake_log(state, "communication");
    state->communication_calls++;
}

static void fake_service_storage(void *user_context)
{
    FakeDpHalState *state = (FakeDpHalState *)user_context;
    fake_log(state, "storage");
    state->storage_calls++;
}

static const DpFirmwareHalOps FAKE_OPS = {
    fake_pwm_update_event,
    fake_read_adc_sample,
    fake_write_pwm_preload,
    fake_disable_pwm_immediate,
    fake_enter_critical,
    fake_exit_critical,
    fake_service_communication,
    fake_service_storage,
};

void FakeDpHal_Init(FakeDpHalState *state)
{
    memset(state, 0, sizeof(*state));
    state->adc_sample.vin_code = 3237u;
    state->adc_sample.vout_code = 3039u;
    state->adc_sample.iout_code = 2606u;
    state->adc_sample.temperature_code = 1179u;
    state->adc_sample_valid = true;
}

DpFirmwareHal FakeDpHal_Bind(FakeDpHalState *state)
{
    DpFirmwareHal hal;
    hal.ops = &FAKE_OPS;
    hal.user_context = state;
    return hal;
}

void FakeDpHal_ClearEvents(FakeDpHalState *state)
{
    state->event_count = 0u;
}

const char *FakeDpHal_Event(const FakeDpHalState *state, size_t index)
{
    if (index >= state->event_count)
    {
        return "";
    }
    return state->events[index];
}
