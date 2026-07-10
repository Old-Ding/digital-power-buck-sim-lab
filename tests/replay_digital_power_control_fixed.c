#include "digital_power_control.h"
#include "digital_power_control_fixed.h"

#include <inttypes.h>
#include <limits.h>
#include <math.h>
#include <stdio.h>

#define LINE_CAPACITY 2048

static DpFixed fixed_from_double(double value, bool *overflow)
{
    const double scaled = value * (double)DP_FIXED_ONE;

    if (scaled > (double)INT32_MAX)
    {
        *overflow = true;
        return INT32_MAX;
    }
    if (scaled < (double)INT32_MIN)
    {
        *overflow = true;
        return INT32_MIN;
    }
    return (DpFixed)(scaled >= 0.0 ? floor(scaled + 0.5) : ceil(scaled - 0.5));
}

static double fixed_to_double(DpFixed value)
{
    return (double)value / (double)DP_FIXED_ONE;
}

int main(int argc, char **argv)
{
    FILE *input_file;
    FILE *output_file;
    char line[LINE_CAPACITY];
    unsigned long row_count = 0u;
    unsigned long input_overflow_count = 0u;
    DpControlConfig float_cfg;
    DpControlContext float_ctx;
    DpFixedControlConfig fixed_cfg;
    DpFixedControlContext fixed_ctx;

    if (argc != 3)
    {
        fprintf(stderr, "usage: %s <input.csv> <output.csv>\n", argv[0]);
        return 2;
    }

    input_file = fopen(argv[1], "r");
    if (input_file == NULL)
    {
        perror("open input csv");
        return 2;
    }

    output_file = fopen(argv[2], "w");
    if (output_file == NULL)
    {
        perror("open output csv");
        fclose(input_file);
        return 2;
    }

    DpControl_DefaultConfig(&float_cfg);
    DpControl_Init(&float_ctx, &float_cfg);
    DpFixedControl_DefaultConfig(&fixed_cfg);
    DpFixedControl_Init(&fixed_ctx, &fixed_cfg);

    if (fgets(line, sizeof(line), input_file) == NULL)
    {
        fprintf(stderr, "input csv has no header\n");
        fclose(input_file);
        fclose(output_file);
        return 2;
    }

    fprintf(output_file,
            "case,tick,time_s,"
            "float_pwm_enable,fixed_pwm_enable,"
            "float_duty_cmd,fixed_duty_cmd,fixed_duty_cmd_raw,"
            "float_duty_raw,fixed_duty_raw,"
            "float_vout_meas_v,fixed_vout_meas_v,"
            "float_vref_cmd_v,fixed_vref_cmd_v,fixed_vref_cmd_raw,"
            "float_error_v,fixed_error_v,"
            "float_p_term,fixed_p_term,"
            "float_integrator,fixed_integrator,fixed_integrator_raw,"
            "float_saturation,fixed_saturation,"
            "float_allow_integrate,fixed_allow_integrate,"
            "float_state,fixed_state,"
            "float_latched_fault,fixed_latched_fault,"
            "float_active_fault,fixed_active_fault,"
            "fixed_arithmetic_overflow,fixed_overflow_count,input_conversion_overflow,fixed_peak_abs_raw\n");

    while (fgets(line, sizeof(line), input_file) != NULL)
    {
        char case_id[64];
        unsigned long tick;
        double time_s;
        int reset_context;
        int init_state;
        int init_latched_fault;
        float init_vout_filter_v;
        float init_vref_cmd_v;
        float init_integrator;
        float init_last_error_v;
        unsigned long init_tick_count;
        int enable;
        int clear_fault;
        float vin_v;
        float vout_adc_v;
        float iout_a;
        float temperature_c;
        DpControlInput float_in;
        DpControlOutput float_out;
        DpFixedControlInput fixed_in;
        DpFixedControlOutput fixed_out;
        bool conversion_overflow = false;
        int matched;

        matched = sscanf(line,
                         "%63[^,],%lu,%lf,%d,%d,%d,%f,%f,%f,%f,%lu,%d,%d,%f,%f,%f,%f",
                         case_id,
                         &tick,
                         &time_s,
                         &reset_context,
                         &init_state,
                         &init_latched_fault,
                         &init_vout_filter_v,
                         &init_vref_cmd_v,
                         &init_integrator,
                         &init_last_error_v,
                         &init_tick_count,
                         &enable,
                         &clear_fault,
                         &vin_v,
                         &vout_adc_v,
                         &iout_a,
                         &temperature_c);

        if (matched != 17)
        {
            fprintf(stderr, "parse error at data row %lu: matched=%d\n", row_count + 1u, matched);
            fclose(input_file);
            fclose(output_file);
            return 2;
        }

        if (reset_context != 0)
        {
            DpControl_Init(&float_ctx, &float_cfg);
            float_ctx.state = (DpControlState)init_state;
            float_ctx.latched_fault = (DpFaultCode)init_latched_fault;
            float_ctx.vout_filter_v = init_vout_filter_v;
            float_ctx.vref_cmd_v = init_vref_cmd_v;
            float_ctx.integrator = init_integrator;
            float_ctx.last_error_v = init_last_error_v;
            float_ctx.tick_count = (uint32_t)init_tick_count;

            DpFixedControl_Init(&fixed_ctx, &fixed_cfg);
            fixed_ctx.state = (DpControlState)init_state;
            fixed_ctx.latched_fault = (DpFaultCode)init_latched_fault;
            fixed_ctx.vout_filter = fixed_from_double(init_vout_filter_v, &conversion_overflow);
            fixed_ctx.vref_cmd = fixed_from_double(init_vref_cmd_v, &conversion_overflow);
            fixed_ctx.integrator = fixed_from_double(init_integrator, &conversion_overflow);
            fixed_ctx.last_error = fixed_from_double(init_last_error_v, &conversion_overflow);
            fixed_ctx.tick_count = (uint32_t)init_tick_count;
        }

        float_in.enable = enable != 0;
        float_in.clear_fault = clear_fault != 0;
        float_in.vin_v = vin_v;
        float_in.vout_adc_v = vout_adc_v;
        float_in.iout_a = iout_a;
        float_in.temperature_c = temperature_c;

        fixed_in.enable = float_in.enable;
        fixed_in.clear_fault = float_in.clear_fault;
        fixed_in.vin = fixed_from_double(vin_v, &conversion_overflow);
        fixed_in.vout_adc = fixed_from_double(vout_adc_v, &conversion_overflow);
        fixed_in.iout = fixed_from_double(iout_a, &conversion_overflow);
        fixed_in.temperature = fixed_from_double(temperature_c, &conversion_overflow);

        float_out = DpControl_Step(&float_ctx, &float_cfg, &float_in);
        fixed_out = DpFixedControl_Step(&fixed_ctx, &fixed_cfg, &fixed_in);

        if (conversion_overflow)
        {
            input_overflow_count++;
        }

        fprintf(output_file,
                "%s,%lu,%.12g,"
                "%d,%d,"
                "%.9g,%.12g,%" PRId32 ","
                "%.9g,%.12g,"
                "%.9g,%.12g,"
                "%.9g,%.12g,%" PRId32 ","
                "%.9g,%.12g,"
                "%.9g,%.12g,"
                "%.9g,%.12g,%" PRId32 ","
                "%d,%d,"
                "%d,%d,"
                "%d,%d,"
                "%d,%d,"
                "%d,%d,"
                "%d,%" PRIu32 ",%d,%" PRId32 "\n",
                case_id,
                tick,
                time_s,
                float_out.pwm_enable ? 1 : 0,
                fixed_out.pwm_enable ? 1 : 0,
                float_out.duty_cmd,
                fixed_to_double(fixed_out.duty_cmd),
                fixed_out.duty_cmd,
                float_out.duty_raw,
                fixed_to_double(fixed_out.duty_raw),
                float_out.vout_meas_v,
                fixed_to_double(fixed_out.vout_meas),
                float_out.vref_cmd_v,
                fixed_to_double(fixed_out.vref_cmd),
                fixed_out.vref_cmd,
                float_out.error_v,
                fixed_to_double(fixed_out.error),
                float_out.p_term,
                fixed_to_double(fixed_out.p_term),
                float_out.integrator,
                fixed_to_double(fixed_out.integrator),
                fixed_out.integrator,
                float_out.saturation ? 1 : 0,
                fixed_out.saturation ? 1 : 0,
                float_out.allow_integrate ? 1 : 0,
                fixed_out.allow_integrate ? 1 : 0,
                (int)float_out.state,
                (int)fixed_out.state,
                (int)float_out.latched_fault,
                (int)fixed_out.latched_fault,
                (int)float_out.active_fault,
                (int)fixed_out.active_fault,
                fixed_out.arithmetic_overflow ? 1 : 0,
                fixed_out.arithmetic_overflow_count,
                conversion_overflow ? 1 : 0,
                fixed_out.peak_abs_raw);
        row_count++;
    }

    fclose(input_file);
    fclose(output_file);
    printf("SUMMARY,OK,rows=%lu,input_overflow=%lu,fixed_overflow=%" PRIu32 "\n",
           row_count,
           input_overflow_count,
           fixed_ctx.arithmetic_overflow_count);
    return 0;
}
