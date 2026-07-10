#include "digital_power_adc_map.h"

#include <limits.h>

#define DP_MICRO_UNITS_PER_UNIT 1000000LL

static uint32_t dp_adc_clamp_code(uint32_t code, uint32_t full_scale, bool *clamped)
{
    if (code > full_scale)
    {
        *clamped = true;
        return full_scale;
    }
    return code;
}

static int64_t dp_div_round_nearest(int64_t numerator, int64_t denominator)
{
    const int64_t half = denominator / 2;
    numerator += numerator >= 0 ? half : -half;
    return numerator / denominator;
}

static DpFixed dp_adc_saturate_fixed(int64_t value, bool *overflow)
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

static int64_t dp_adc_code_to_uv(uint32_t code,
                                 const DpAdcMapConfig *cfg)
{
    return dp_div_round_nearest((int64_t)code * cfg->adc_reference_uv,
                                cfg->adc_full_scale_code);
}

static DpFixed dp_adc_voltage_to_fixed(uint32_t code,
                                       uint32_t divider_num,
                                       uint32_t divider_den,
                                       const DpAdcMapConfig *cfg,
                                       bool *overflow)
{
    const int64_t adc_uv = dp_adc_code_to_uv(code, cfg);
    const int64_t numerator = adc_uv * divider_num * DP_FIXED_ONE;
    const int64_t denominator = (int64_t)divider_den * DP_MICRO_UNITS_PER_UNIT;
    return dp_adc_saturate_fixed(dp_div_round_nearest(numerator, denominator), overflow);
}

static DpFixed dp_adc_sensor_to_fixed(uint32_t code,
                                      int32_t offset_uv,
                                      uint32_t slope_uv_per_unit,
                                      const DpAdcMapConfig *cfg,
                                      bool *overflow)
{
    const int64_t adc_uv = dp_adc_code_to_uv(code, cfg);
    const int64_t numerator = (adc_uv - offset_uv) * DP_FIXED_ONE;
    return dp_adc_saturate_fixed(dp_div_round_nearest(numerator, slope_uv_per_unit), overflow);
}

static DpFixed dp_adc_clamp_physical(DpFixed value,
                                     DpFixed low,
                                     DpFixed high,
                                     bool *clamped)
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

void DpAdcMap_DefaultConfig(DpAdcMapConfig *cfg)
{
    cfg->adc_full_scale_code = 4095u;
    cfg->adc_reference_uv = 3300000u;
    cfg->vin_divider_num = 92u;
    cfg->vin_divider_den = 10u;
    cfg->vout_divider_num = 49u;
    cfg->vout_divider_den = 10u;
    cfg->current_offset_uv = 100000;
    cfg->current_gain_uv_per_a = 400000u;
    cfg->temperature_offset_uv = 500000;
    cfg->temperature_slope_uv_per_c = 10000u;
    cfg->current_min = 0;
    cfg->current_max = 8 * DP_FIXED_ONE;
    cfg->temperature_min = -40 * DP_FIXED_ONE;
    cfg->temperature_max = 150 * DP_FIXED_ONE;
}

DpAdcMapResult DpAdcMap_Convert(const DpAdcMapConfig *cfg, const DpAdcRawSample *sample)
{
    DpAdcMapResult result;
    bool code_clamped = false;
    bool physical_clamped = false;
    bool overflow = false;
    const uint32_t vin_code = dp_adc_clamp_code(sample->vin_code, cfg->adc_full_scale_code, &code_clamped);
    const uint32_t vout_code = dp_adc_clamp_code(sample->vout_code, cfg->adc_full_scale_code, &code_clamped);
    const uint32_t iout_code = dp_adc_clamp_code(sample->iout_code, cfg->adc_full_scale_code, &code_clamped);
    const uint32_t temperature_code = dp_adc_clamp_code(sample->temperature_code, cfg->adc_full_scale_code, &code_clamped);

    result.controller_input.enable = sample->enable;
    result.controller_input.clear_fault = sample->clear_fault;
    result.controller_input.vin = dp_adc_voltage_to_fixed(vin_code,
                                                          cfg->vin_divider_num,
                                                          cfg->vin_divider_den,
                                                          cfg,
                                                          &overflow);
    result.controller_input.vout_adc = dp_adc_voltage_to_fixed(vout_code,
                                                                cfg->vout_divider_num,
                                                                cfg->vout_divider_den,
                                                                cfg,
                                                                &overflow);
    result.controller_input.iout = dp_adc_sensor_to_fixed(iout_code,
                                                          cfg->current_offset_uv,
                                                          cfg->current_gain_uv_per_a,
                                                          cfg,
                                                          &overflow);
    result.controller_input.temperature = dp_adc_sensor_to_fixed(temperature_code,
                                                                  cfg->temperature_offset_uv,
                                                                  cfg->temperature_slope_uv_per_c,
                                                                  cfg,
                                                                  &overflow);

    // 传感器物理量范围只在映射层收口，控制器不重复处理 ADC 前端异常。
    result.controller_input.iout = dp_adc_clamp_physical(result.controller_input.iout,
                                                          cfg->current_min,
                                                          cfg->current_max,
                                                          &physical_clamped);
    result.controller_input.temperature = dp_adc_clamp_physical(result.controller_input.temperature,
                                                                  cfg->temperature_min,
                                                                  cfg->temperature_max,
                                                                  &physical_clamped);
    result.input_code_clamped = code_clamped;
    result.physical_value_clamped = physical_clamped;
    result.arithmetic_overflow = overflow;
    return result;
}
