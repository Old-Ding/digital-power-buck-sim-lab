#include "digital_power_control_isr.h"

#include <stdio.h>

static int failures = 0;

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

static void force_run_state(DpControlIsrContext *ctx, const DpControlIsrConfig *cfg)
{
    ctx->control.state = DP_STATE_RUN;
    ctx->control.vref_cmd = cfg->control.vref_final;
    ctx->control.integrator = 0;
}

static void test_previous_compare_applies_before_new_control(void)
{
    DpControlIsrConfig cfg;
    DpControlIsrContext ctx;
    DpControlIsrOutput first;
    DpControlIsrOutput second;
    DpAdcRawSample sample = nominal_sample();
    DpFixed preload_duty = (DpFixed)(DP_FIXED_ONE / 5);

    DpControlIsr_DefaultConfig(&cfg);
    DpControlIsr_Init(&ctx, &cfg);
    force_run_state(&ctx, &cfg);
    DpPwmMap_Queue(&ctx.pwm, &cfg.pwm, preload_duty, true);

    DpControlIsr_OnPwmUpdate(&ctx, &cfg, &sample, &first);
    expect_true("previous_compare_applies_at_isr_entry",
                first.active_compare_before_update == 0u &&
                    first.active_compare_after_update == 85u &&
                    ctx.pwm.active_compare == 85u);
    expect_true("new_compare_waits_for_next_update",
                first.pending_compare_after_control != first.active_compare_after_update &&
                    ctx.pwm.update_pending);

    DpControlIsr_OnPwmUpdate(&ctx, &cfg, &sample, &second);
    expect_true("queued_compare_has_one_cycle_latency",
                second.active_compare_after_update == first.pending_compare_after_control);
    expect_true("nominal_adc_and_arithmetic_are_clean",
                !second.adc_input_clamped &&
                    !second.adc_physical_clamped &&
                    !second.arithmetic_overflow);
}

static void test_ocp_disables_active_pwm_without_waiting(void)
{
    DpControlIsrConfig cfg;
    DpControlIsrContext ctx;
    DpControlIsrOutput normal;
    DpControlIsrOutput fault;
    DpAdcRawSample sample = nominal_sample();

    DpControlIsr_DefaultConfig(&cfg);
    DpControlIsr_Init(&ctx, &cfg);
    force_run_state(&ctx, &cfg);
    DpPwmMap_Queue(&ctx.pwm, &cfg.pwm, DP_FIXED_ONE / 2, true);
    DpControlIsr_OnPwmUpdate(&ctx, &cfg, &sample, &normal);

    sample.iout_code = 3598u;
    DpControlIsr_OnPwmUpdate(&ctx, &cfg, &sample, &fault);
    expect_true("ocp_latches_fault_and_commands_disable",
                fault.active_fault == DP_FAULT_OCP &&
                    fault.latched_fault == DP_FAULT_OCP &&
                    !fault.pwm_enable_command);
    expect_true("ocp_disable_is_immediate",
                !fault.active_pwm_enable &&
                    fault.pending_compare_after_control == 0u);
}

int main(void)
{
    test_previous_compare_applies_before_new_control();
    test_ocp_disables_active_pwm_without_waiting();
    printf("SUMMARY,%s,failures=%d\n", failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
