#ifndef FAKE_DIGITAL_POWER_HAL_H
#define FAKE_DIGITAL_POWER_HAL_H

#include "digital_power_firmware.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define FAKE_DP_HAL_MAX_EVENTS 256
#define FAKE_DP_HAL_EVENT_NAME_CAPACITY 32

typedef struct
{
    DpAdcRawSample adc_sample;
    bool adc_sample_valid;
    uint32_t active_compare;
    uint32_t pending_compare;
    bool active_enable;
    bool pending_enable;
    unsigned int communication_calls;
    unsigned int storage_calls;
    unsigned int critical_depth;
    char events[FAKE_DP_HAL_MAX_EVENTS][FAKE_DP_HAL_EVENT_NAME_CAPACITY];
    size_t event_count;
} FakeDpHalState;

void FakeDpHal_Init(FakeDpHalState *state);
DpFirmwareHal FakeDpHal_Bind(FakeDpHalState *state);
void FakeDpHal_ClearEvents(FakeDpHalState *state);
const char *FakeDpHal_Event(const FakeDpHalState *state, size_t index);

#endif
