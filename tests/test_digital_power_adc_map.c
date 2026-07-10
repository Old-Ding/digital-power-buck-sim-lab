#include "digital_power_adc_map.h"

#include <stdio.h>

static int failures = 0;

static DpFixed fixed_abs(DpFixed value)
{
    return value < 0 ? -value : value;
}

static void expect_true(const char *name, bool condition)
{
    if (condition)
    {
        printf("PASS,%s\n", name);
        return;
    }
    printf("FAIL,%s\n", name);
    failures++;
}

static void test_nominal_operating_point(void)
{
    DpAdcMapConfig cfg;
    DpAdcRawSample sample;
    DpAdcMapResult result;

    DpAdcMap_DefaultConfig(&cfg);
    sample.vin_code = 3237u;
    sample.vout_code = 3039u;
    sample.iout_code = 2606u;
    sample.temperature_code = 1179u;
    sample.enable = true;
    sample.clear_fault = false;
    result = DpAdcMap_Convert(&cfg, &sample);

    expect_true("nominal_24v_12v_5a_45c",
                fixed_abs(result.controller_input.vin - 24 * DP_FIXED_ONE) <= 8389 &&
                    fixed_abs(result.controller_input.vout_adc - 12 * DP_FIXED_ONE) <= 4195 &&
                    fixed_abs(result.controller_input.iout - 5 * DP_FIXED_ONE) <= 3146 &&
                    fixed_abs(result.controller_input.temperature - 45 * DP_FIXED_ONE) <= 104858 &&
                    !result.arithmetic_overflow);
}

static void test_code_clamp(void)
{
    DpAdcMapConfig cfg;
    DpAdcRawSample sample = {5000u, 5000u, 5000u, 5000u, true, false};
    DpAdcMapResult result;

    DpAdcMap_DefaultConfig(&cfg);
    result = DpAdcMap_Convert(&cfg, &sample);
    expect_true("adc_code_above_full_scale_is_clamped",
                result.input_code_clamped &&
                    result.controller_input.vin > 30 * DP_FIXED_ONE &&
                    result.controller_input.iout == cfg.current_max &&
                    result.controller_input.temperature == cfg.temperature_max);
}

static void test_sensor_physical_clamp(void)
{
    DpAdcMapConfig cfg;
    DpAdcRawSample sample = {0u, 0u, 0u, 0u, true, false};
    DpAdcMapResult result;

    DpAdcMap_DefaultConfig(&cfg);
    result = DpAdcMap_Convert(&cfg, &sample);
    expect_true("sensor_values_respect_physical_limits",
                result.physical_value_clamped &&
                    result.controller_input.iout == cfg.current_min &&
                    result.controller_input.temperature == cfg.temperature_min);
}

int main(void)
{
    test_nominal_operating_point();
    test_code_clamp();
    test_sensor_physical_clamp();

    printf("SUMMARY,%s,failures=%d\n", failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
