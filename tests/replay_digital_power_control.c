#include "digital_power_control.h"

#include <stdio.h>
#include <stdint.h>

#define LINE_CAPACITY 2048

int main(int argc, char **argv)
{
    FILE *input_file;
    FILE *output_file;
    char line[LINE_CAPACITY];
    unsigned long row_count = 0u;
    DpControlConfig cfg;
    DpControlContext ctx;

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

    DpControl_DefaultConfig(&cfg);
    DpControl_Init(&ctx, &cfg);

    if (fgets(line, sizeof(line), input_file) == NULL)
    {
        fprintf(stderr, "input csv has no header\n");
        fclose(input_file);
        fclose(output_file);
        return 2;
    }

    fprintf(output_file,
            "case,tick,time_s,pwm_enable,duty_cmd,duty_raw,vout_meas_v,vref_cmd_v,error_v,p_term,integrator,saturation,allow_integrate,state,latched_fault,active_fault\n");

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
        DpControlInput in;
        DpControlOutput out;
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
            // 每个场景首行恢复 Python 参考实现的初始状态，避免初值差异污染实现对照。
            DpControl_Init(&ctx, &cfg);
            ctx.state = (DpControlState)init_state;
            ctx.latched_fault = (DpFaultCode)init_latched_fault;
            ctx.vout_filter_v = init_vout_filter_v;
            ctx.vref_cmd_v = init_vref_cmd_v;
            ctx.integrator = init_integrator;
            ctx.last_error_v = init_last_error_v;
            ctx.tick_count = (uint32_t)init_tick_count;
        }

        in.enable = enable != 0;
        in.clear_fault = clear_fault != 0;
        in.vin_v = vin_v;
        in.vout_adc_v = vout_adc_v;
        in.iout_a = iout_a;
        in.temperature_c = temperature_c;

        out = DpControl_Step(&ctx, &cfg, &in);

        fprintf(output_file,
                "%s,%lu,%.12g,%d,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%d,%d,%d,%d,%d\n",
                case_id,
                tick,
                time_s,
                out.pwm_enable ? 1 : 0,
                out.duty_cmd,
                out.duty_raw,
                out.vout_meas_v,
                out.vref_cmd_v,
                out.error_v,
                out.p_term,
                out.integrator,
                out.saturation ? 1 : 0,
                out.allow_integrate ? 1 : 0,
                (int)out.state,
                (int)out.latched_fault,
                (int)out.active_fault);
        row_count++;
    }

    fclose(input_file);
    fclose(output_file);
    printf("SUMMARY,OK,rows=%lu\n", row_count);
    return 0;
}
