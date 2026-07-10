#ifndef DIGITAL_POWER_ADC_MAP_H
#define DIGITAL_POWER_ADC_MAP_H

#include "digital_power_control_fixed.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct
{
    uint32_t adc_full_scale_code;
    uint32_t adc_reference_uv;
    uint32_t vin_divider_num;
    uint32_t vin_divider_den;
    uint32_t vout_divider_num;
    uint32_t vout_divider_den;
    int32_t current_offset_uv;
    uint32_t current_gain_uv_per_a;
    int32_t temperature_offset_uv;
    uint32_t temperature_slope_uv_per_c;
    DpFixed current_min;
    DpFixed current_max;
    DpFixed temperature_min;
    DpFixed temperature_max;
} DpAdcMapConfig;

typedef struct
{
    uint32_t vin_code;
    uint32_t vout_code;
    uint32_t iout_code;
    uint32_t temperature_code;
    bool enable;
    bool clear_fault;
} DpAdcRawSample;

typedef struct
{
    DpFixedControlInput controller_input;
    bool input_code_clamped;
    bool physical_value_clamped;
    bool arithmetic_overflow;
} DpAdcMapResult;

void DpAdcMap_DefaultConfig(DpAdcMapConfig *cfg);
DpAdcMapResult DpAdcMap_Convert(const DpAdcMapConfig *cfg, const DpAdcRawSample *sample);

#endif
