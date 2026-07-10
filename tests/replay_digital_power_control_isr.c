#include "digital_power_control_isr.h"

#include <inttypes.h>
#include <stdio.h>

static DpAdcRawSample nominal_sample(void)
{
    DpAdcRawSample sample;
    sample.vin_code = 3237u;
    sample.vout_code = 3039u;
    sample.iout_code = 2606u;
    sample.temperature_code = 1179u;
    sample.enable = true;
    sample.clear_fault = false;
    return sample;
}

static double fixed_to_double(DpFixed value)
{
    return (double)value / (double)DP_FIXED_ONE;
}

int main(int argc, char **argv)
{
    DpControlIsrConfig cfg;
    DpControlIsrContext ctx;
    DpControlIsrOutput out;
    DpAdcRawSample sample;
    FILE *file;
    unsigned int cycle;
    const char *scenario;

    if (argc != 2)
    {
        fprintf(stderr, "usage: %s <output.csv>\n", argv[0]);
        return 2;
    }
    file = fopen(argv[1], "w");
    if (file == NULL)
    {
        fprintf(stderr, "failed to open output csv\n");
        return 2;
    }

    DpControlIsr_DefaultConfig(&cfg);
    DpControlIsr_Init(&ctx, &cfg);
    ctx.control.state = DP_STATE_RUN;
    ctx.control.vref_cmd = cfg.control.vref_final;
    DpPwmMap_Queue(&ctx.pwm, &cfg.pwm, DP_FIXED_ONE / 5, true);

    fprintf(file,
            "cycle,scenario,invocation,active_compare_before_update,active_compare_after_update,pending_compare_after_control,"
            "active_pwm_enable,pwm_enable_command,vin_v,vout_v,iout_a,temperature_c,duty_cmd,state,active_fault,latched_fault,"
            "adc_input_clamped,adc_physical_clamped,arithmetic_overflow\n");

    for (cycle = 0u; cycle < 6u; cycle++)
    {
        sample = nominal_sample();
        scenario = "normal";
        if (cycle == 2u || cycle == 3u)
        {
            sample.iout_code = 3598u;
            scenario = "ocp";
        }
        else if (cycle == 4u)
        {
            sample.clear_fault = true;
            scenario = "clear_fault";
        }
        else if (cycle == 5u)
        {
            scenario = "restart";
        }

        DpControlIsr_OnPwmUpdate(&ctx, &cfg, &sample, &out);
        fprintf(file,
                "%u,%s,%" PRIu32 ",%" PRIu32 ",%" PRIu32 ",%" PRIu32 ",%d,%d,%.9g,%.9g,%.9g,%.9g,%.9g,%d,%d,%d,%d,%d,%d\n",
                cycle,
                scenario,
                out.invocation_count,
                out.active_compare_before_update,
                out.active_compare_after_update,
                out.pending_compare_after_control,
                out.active_pwm_enable ? 1 : 0,
                out.pwm_enable_command ? 1 : 0,
                fixed_to_double(out.vin),
                fixed_to_double(out.vout),
                fixed_to_double(out.iout),
                fixed_to_double(out.temperature),
                fixed_to_double(out.duty_cmd),
                (int)out.state,
                (int)out.active_fault,
                (int)out.latched_fault,
                out.adc_input_clamped ? 1 : 0,
                out.adc_physical_clamped ? 1 : 0,
                out.arithmetic_overflow ? 1 : 0);
    }

    fclose(file);
    printf("SUMMARY,OK,cycles=6\n");
    return 0;
}
