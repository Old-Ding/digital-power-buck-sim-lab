#include "digital_power_control_isr.h"

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#ifdef _WIN32
#include <windows.h>

static uint64_t monotonic_ns(void)
{
    LARGE_INTEGER counter;
    LARGE_INTEGER frequency;
    uint64_t seconds;
    uint64_t remainder;

    QueryPerformanceCounter(&counter);
    QueryPerformanceFrequency(&frequency);
    // 先拆整秒再换算余数，避免长时间开机后绝对计数乘 1e9 溢出。
    seconds = (uint64_t)(counter.QuadPart / frequency.QuadPart);
    remainder = (uint64_t)(counter.QuadPart % frequency.QuadPart);
    return seconds * 1000000000ULL +
           remainder * 1000000000ULL / (uint64_t)frequency.QuadPart;
}
#else
#include <time.h>

static uint64_t monotonic_ns(void)
{
    struct timespec value;
    clock_gettime(CLOCK_MONOTONIC, &value);
    return (uint64_t)value.tv_sec * 1000000000ULL + (uint64_t)value.tv_nsec;
}
#endif

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

int main(int argc, char **argv)
{
    enum
    {
        BATCHES = 200,
        ITERATIONS_PER_BATCH = 10000,
        WARMUP_ITERATIONS = 20000
    };
    DpControlIsrConfig cfg;
    DpControlIsrContext ctx;
    DpControlIsrOutput out;
    DpAdcRawSample sample = nominal_sample();
    volatile uint64_t checksum = 0u;
    FILE *file;
    int batch;
    int index;

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

    for (index = 0; index < WARMUP_ITERATIONS; index++)
    {
        sample.vout_code = (uint32_t)(3038 + (index & 1));
        DpControlIsr_OnPwmUpdate(&ctx, &cfg, &sample, &out);
        checksum += out.pending_compare_after_control;
    }

    fprintf(file, "batch,iterations,elapsed_ns,ns_per_call,checksum\n");
    for (batch = 0; batch < BATCHES; batch++)
    {
        const uint64_t start = monotonic_ns();
        uint64_t end;
        for (index = 0; index < ITERATIONS_PER_BATCH; index++)
        {
            sample.vout_code = (uint32_t)(3038 + ((batch + index) & 1));
            DpControlIsr_OnPwmUpdate(&ctx, &cfg, &sample, &out);
            checksum += out.pending_compare_after_control;
        }
        end = monotonic_ns();
        fprintf(file,
                "%d,%d,%" PRIu64 ",%.9g,%" PRIu64 "\n",
                batch,
                ITERATIONS_PER_BATCH,
                end - start,
                (double)(end - start) / ITERATIONS_PER_BATCH,
                checksum);
    }

    fclose(file);
    printf("SUMMARY,OK,batches=%d,iterations_per_batch=%d,checksum=%" PRIu64 "\n",
           BATCHES,
           ITERATIONS_PER_BATCH,
           checksum);
    return 0;
}
