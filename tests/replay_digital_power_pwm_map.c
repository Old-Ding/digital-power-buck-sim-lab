#include "digital_power_pwm_map.h"

#include <inttypes.h>
#include <stdio.h>

#define LINE_CAPACITY 1024

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
    DpPwmMapState state;

    if (argc != 3)
    {
        fprintf(stderr, "usage: %s <input.csv> <output.csv>\n", argv[0]);
        return 2;
    }
    input_file = fopen(argv[1], "r");
    output_file = fopen(argv[2], "w");
    if (input_file == NULL || output_file == NULL)
    {
        fprintf(stderr, "failed to open input or output csv\n");
        return 2;
    }
    if (fgets(line, sizeof(line), input_file) == NULL)
    {
        fprintf(stderr, "input csv has no header\n");
        return 2;
    }

    DpPwmMap_Init(&state);
    fprintf(output_file,
            "case,index,reset,apply_update,requested_duty,pwm_enable,period_counts,auto_reload,deadtime_counts,duty_max_q20,"
            "requested_duty_q20,clamped_duty_q20,clamped_duty,pending_compare,active_compare_before,active_compare_after,"
            "active_enable_before,active_enable_after,duty_clamped,update_pending_after,effective_duty_after,arithmetic_overflow\n");

    while (fgets(line, sizeof(line), input_file) != NULL)
    {
        char case_id[64];
        unsigned long index;
        int reset;
        int apply_update;
        double requested_duty;
        int pwm_enable;
        unsigned long period_counts;
        unsigned long auto_reload;
        unsigned long deadtime_counts;
        long duty_max_q20;
        long requested_duty_q20;
        int matched;
        DpPwmMapConfig cfg;
        DpPwmQueueResult result;
        uint32_t active_before;
        bool enable_before;

        matched = sscanf(line, "%63[^,],%lu,%d,%d,%lf,%d,%lu,%lu,%lu,%ld,%ld",
                         case_id, &index, &reset, &apply_update, &requested_duty, &pwm_enable,
                         &period_counts, &auto_reload, &deadtime_counts, &duty_max_q20, &requested_duty_q20);
        if (matched != 11)
        {
            fprintf(stderr, "parse error at row %lu: matched=%d\n", row_count + 1u, matched);
            return 2;
        }

        if (reset != 0)
        {
            DpPwmMap_Init(&state);
        }
        DpPwmMap_DefaultConfig(&cfg);
        cfg.period_counts = (uint32_t)period_counts;
        cfg.auto_reload = (uint32_t)auto_reload;
        cfg.deadtime_counts = (uint32_t)deadtime_counts;
        cfg.duty_max = (DpFixed)duty_max_q20;

        active_before = state.active_compare;
        enable_before = state.active_enable;
        result = DpPwmMap_Queue(&state, &cfg, (DpFixed)requested_duty_q20, pwm_enable != 0);
        if (apply_update != 0)
        {
            DpPwmMap_ApplyUpdateEvent(&state);
        }

        fprintf(output_file,
                "%s,%lu,%d,%d,%.12g,%d,%lu,%lu,%lu,%ld,%" PRId32 ",%" PRId32 ",%.12g,%" PRIu32 ",%" PRIu32 ",%" PRIu32 ",%d,%d,%d,%d,%.12g,%d\n",
                case_id, index, reset, apply_update, requested_duty, pwm_enable,
                period_counts, auto_reload, deadtime_counts, duty_max_q20,
                result.requested_duty, result.clamped_duty, fixed_to_double(result.clamped_duty),
                result.pending_compare, active_before, state.active_compare,
                enable_before ? 1 : 0, state.active_enable ? 1 : 0,
                result.duty_clamped ? 1 : 0, state.update_pending ? 1 : 0,
                fixed_to_double(DpPwmMap_CompareToDuty(&cfg, state.active_compare)),
                result.arithmetic_overflow ? 1 : 0);
        row_count++;
    }

    fclose(input_file);
    fclose(output_file);
    printf("SUMMARY,OK,rows=%lu\n", row_count);
    return 0;
}
