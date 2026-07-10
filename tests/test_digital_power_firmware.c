#include "digital_power_firmware.h"
#include "fake_digital_power_hal.h"

#include <stdio.h>
#include <string.h>

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

static bool events_equal(const FakeDpHalState *fake, const char *const *expected, size_t count)
{
    size_t index;
    if (fake->event_count != count)
    {
        return false;
    }
    for (index = 0u; index < count; index++)
    {
        if (strcmp(FakeDpHal_Event(fake, index), expected[index]) != 0)
        {
            return false;
        }
    }
    return true;
}

static void enable_firmware(DpFirmwareContext *ctx, const DpFirmwareHal *hal)
{
    DpFirmwareCommand command;
    command.enable = true;
    command.clear_fault = false;
    DpFirmware_RequestCommand(ctx, hal, &command);
}

static void test_isr_and_background_ownership(void)
{
    static const char *const ISR_EVENTS[] = {"pwm_update", "adc_read", "pwm_write"};
    static const char *const BACKGROUND_EVENTS[] = {"communication", "storage"};
    DpControlIsrConfig cfg;
    DpFirmwareContext ctx;
    FakeDpHalState fake;
    DpFirmwareHal hal;

    DpControlIsr_DefaultConfig(&cfg);
    DpFirmware_Init(&ctx, &cfg);
    FakeDpHal_Init(&fake);
    hal = FakeDpHal_Bind(&fake);
    enable_firmware(&ctx, &hal);

    FakeDpHal_ClearEvents(&fake);
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    expect_true("isr_calls_only_realtime_hal_operations",
                events_equal(&fake, ISR_EVENTS, sizeof(ISR_EVENTS) / sizeof(ISR_EVENTS[0])));

    FakeDpHal_ClearEvents(&fake);
    DpFirmware_BackgroundStep(&hal);
    expect_true("background_calls_only_communication_and_storage",
                events_equal(&fake, BACKGROUND_EVENTS, sizeof(BACKGROUND_EVENTS) / sizeof(BACKGROUND_EVENTS[0])));
}

static void test_ocp_disable_precedes_preload_write(void)
{
    static const char *const OCP_EVENTS[] = {"pwm_update", "adc_read", "pwm_disable", "pwm_write"};
    DpControlIsrConfig cfg;
    DpFirmwareContext ctx;
    FakeDpHalState fake;
    DpFirmwareHal hal;

    DpControlIsr_DefaultConfig(&cfg);
    DpFirmware_Init(&ctx, &cfg);
    FakeDpHal_Init(&fake);
    hal = FakeDpHal_Bind(&fake);
    enable_firmware(&ctx, &hal);
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);

    fake.adc_sample.iout_code = 3598u;
    FakeDpHal_ClearEvents(&fake);
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    expect_true("ocp_disable_precedes_preload_write",
                events_equal(&fake, OCP_EVENTS, sizeof(OCP_EVENTS) / sizeof(OCP_EVENTS[0])));
    expect_true("ocp_turns_off_fake_hardware",
                !fake.active_enable &&
                    !fake.pending_enable &&
                    ctx.telemetry.latched_fault == DP_FAULT_OCP);
}

static void test_command_commits_at_next_isr_boundary(void)
{
    DpControlIsrConfig cfg;
    DpFirmwareContext ctx;
    FakeDpHalState fake;
    DpFirmwareHal hal;
    DpFirmwareCommand command;

    DpControlIsr_DefaultConfig(&cfg);
    DpFirmware_Init(&ctx, &cfg);
    FakeDpHal_Init(&fake);
    hal = FakeDpHal_Bind(&fake);
    enable_firmware(&ctx, &hal);
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);

    command.enable = false;
    command.clear_fault = false;
    DpFirmware_RequestCommand(&ctx, &hal, &command);
    expect_true("background_command_waits_for_isr_boundary",
                ctx.active_command.enable && ctx.command_pending);
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    expect_true("command_is_atomic_at_isr_boundary",
                !ctx.active_command.enable && !ctx.command_pending && !fake.active_enable);
}

static void test_adc_failure_is_fail_safe(void)
{
    static const char *const FAILURE_EVENTS[] = {"pwm_update", "adc_read", "pwm_disable", "pwm_write"};
    DpControlIsrConfig cfg;
    DpFirmwareContext ctx;
    FakeDpHalState fake;
    DpFirmwareHal hal;

    DpControlIsr_DefaultConfig(&cfg);
    DpFirmware_Init(&ctx, &cfg);
    FakeDpHal_Init(&fake);
    hal = FakeDpHal_Bind(&fake);
    enable_firmware(&ctx, &hal);
    fake.adc_sample_valid = false;

    FakeDpHal_ClearEvents(&fake);
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    expect_true("adc_failure_uses_fail_safe_hal_order",
                events_equal(&fake, FAILURE_EVENTS, sizeof(FAILURE_EVENTS) / sizeof(FAILURE_EVENTS[0])));
    expect_true("adc_failure_is_visible_in_telemetry",
                ctx.telemetry_valid && !ctx.telemetry.adc_sample_valid && !fake.active_enable);
}

static void test_telemetry_copy_uses_short_critical_section(void)
{
    static const char *const COPY_EVENTS[] = {"critical_enter", "critical_exit"};
    DpControlIsrConfig cfg;
    DpFirmwareContext ctx;
    FakeDpHalState fake;
    DpFirmwareHal hal;
    DpFirmwareTelemetry telemetry;

    DpControlIsr_DefaultConfig(&cfg);
    DpFirmware_Init(&ctx, &cfg);
    FakeDpHal_Init(&fake);
    hal = FakeDpHal_Bind(&fake);
    enable_firmware(&ctx, &hal);
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);

    FakeDpHal_ClearEvents(&fake);
    expect_true("telemetry_is_available", DpFirmware_ReadTelemetry(&ctx, &hal, &telemetry));
    expect_true("telemetry_copy_uses_critical_section",
                events_equal(&fake, COPY_EVENTS, sizeof(COPY_EVENTS) / sizeof(COPY_EVENTS[0])) &&
                    fake.critical_depth == 0u);
}

int main(void)
{
    test_isr_and_background_ownership();
    test_ocp_disable_precedes_preload_write();
    test_command_commits_at_next_isr_boundary();
    test_adc_failure_is_fail_safe();
    test_telemetry_copy_uses_short_critical_section();
    printf("SUMMARY,%s,failures=%d\n", failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
