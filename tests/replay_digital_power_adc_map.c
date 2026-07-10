#include "digital_power_adc_map.h"

#include <inttypes.h>
#include <stdio.h>

#define LINE_CAPACITY 2048

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

    if (fgets(line, sizeof(line), input_file) == NULL)
    {
        fprintf(stderr, "input csv has no header\n");
        fclose(input_file);
        fclose(output_file);
        return 2;
    }

    fprintf(output_file,
            "case,index,vin_true_v,vout_true_v,iout_true_a,temperature_true_c,"
            "vin_code,vout_code,iout_code,temperature_code,"
            "vin_mapped_v,vout_mapped_v,iout_mapped_a,temperature_mapped_c,"
            "vin_q20,vout_q20,iout_q20,temperature_q20,"
            "input_code_clamped,physical_value_clamped,arithmetic_overflow\n");

    while (fgets(line, sizeof(line), input_file) != NULL)
    {
        char case_id[64];
        unsigned long index;
        double vin_true_v;
        double vout_true_v;
        double iout_true_a;
        double temperature_true_c;
        unsigned long vin_code;
        unsigned long vout_code;
        unsigned long iout_code;
        unsigned long temperature_code;
        unsigned long adc_full_scale_code;
        unsigned long adc_reference_uv;
        unsigned long vin_divider_num;
        unsigned long vin_divider_den;
        unsigned long vout_divider_num;
        unsigned long vout_divider_den;
        long current_offset_uv;
        unsigned long current_gain_uv_per_a;
        long temperature_offset_uv;
        unsigned long temperature_slope_uv_per_c;
        int enable;
        int clear_fault;
        int matched;
        DpAdcMapConfig cfg;
        DpAdcRawSample sample;
        DpAdcMapResult result;

        matched = sscanf(line,
                         "%63[^,],%lu,%lf,%lf,%lf,%lf,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%ld,%lu,%ld,%lu,%d,%d",
                         case_id,
                         &index,
                         &vin_true_v,
                         &vout_true_v,
                         &iout_true_a,
                         &temperature_true_c,
                         &vin_code,
                         &vout_code,
                         &iout_code,
                         &temperature_code,
                         &adc_full_scale_code,
                         &adc_reference_uv,
                         &vin_divider_num,
                         &vin_divider_den,
                         &vout_divider_num,
                         &vout_divider_den,
                         &current_offset_uv,
                         &current_gain_uv_per_a,
                         &temperature_offset_uv,
                         &temperature_slope_uv_per_c,
                         &enable,
                         &clear_fault);
        if (matched != 22)
        {
            fprintf(stderr, "parse error at row %lu: matched=%d\n", row_count + 1u, matched);
            fclose(input_file);
            fclose(output_file);
            return 2;
        }

        DpAdcMap_DefaultConfig(&cfg);
        cfg.adc_full_scale_code = (uint32_t)adc_full_scale_code;
        cfg.adc_reference_uv = (uint32_t)adc_reference_uv;
        cfg.vin_divider_num = (uint32_t)vin_divider_num;
        cfg.vin_divider_den = (uint32_t)vin_divider_den;
        cfg.vout_divider_num = (uint32_t)vout_divider_num;
        cfg.vout_divider_den = (uint32_t)vout_divider_den;
        cfg.current_offset_uv = (int32_t)current_offset_uv;
        cfg.current_gain_uv_per_a = (uint32_t)current_gain_uv_per_a;
        cfg.temperature_offset_uv = (int32_t)temperature_offset_uv;
        cfg.temperature_slope_uv_per_c = (uint32_t)temperature_slope_uv_per_c;

        sample.vin_code = (uint32_t)vin_code;
        sample.vout_code = (uint32_t)vout_code;
        sample.iout_code = (uint32_t)iout_code;
        sample.temperature_code = (uint32_t)temperature_code;
        sample.enable = enable != 0;
        sample.clear_fault = clear_fault != 0;

        result = DpAdcMap_Convert(&cfg, &sample);
        fprintf(output_file,
                "%s,%lu,%.12g,%.12g,%.12g,%.12g,%lu,%lu,%lu,%lu,"
                "%.12g,%.12g,%.12g,%.12g,"
                "%" PRId32 ",%" PRId32 ",%" PRId32 ",%" PRId32 ",%d,%d,%d\n",
                case_id,
                index,
                vin_true_v,
                vout_true_v,
                iout_true_a,
                temperature_true_c,
                vin_code,
                vout_code,
                iout_code,
                temperature_code,
                fixed_to_double(result.controller_input.vin),
                fixed_to_double(result.controller_input.vout_adc),
                fixed_to_double(result.controller_input.iout),
                fixed_to_double(result.controller_input.temperature),
                result.controller_input.vin,
                result.controller_input.vout_adc,
                result.controller_input.iout,
                result.controller_input.temperature,
                result.input_code_clamped ? 1 : 0,
                result.physical_value_clamped ? 1 : 0,
                result.arithmetic_overflow ? 1 : 0);
        row_count++;
    }

    fclose(input_file);
    fclose(output_file);
    printf("SUMMARY,OK,rows=%lu\n", row_count);
    return 0;
}
