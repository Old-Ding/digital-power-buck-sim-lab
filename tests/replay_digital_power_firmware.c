#include "digital_power_firmware.h"
#include "fake_digital_power_hal.h"

#include <inttypes.h>
#include <stdio.h>

static void write_new_events(FILE *file,
                             const FakeDpHalState *fake,
                             const char *phase,
                             size_t start_index)
{
    size_t index;
    for (index = start_index; index < fake->event_count; index++)
    {
        fprintf(file, "%s,%zu,%s\n", phase, index - start_index, FakeDpHal_Event(fake, index));
    }
}

static void write_state(FILE *file,
                        const char *phase,
                        const DpFirmwareContext *ctx,
                        const FakeDpHalState *fake)
{
    fprintf(file,
            "%s,%" PRIu32 ",%d,%d,%d,%d,%d,%d,%" PRIu32 ",%" PRIu32 ",%d,%d,%u,%u,%zu\n",
            phase,
            ctx->control.invocation_count,
            ctx->active_command.enable ? 1 : 0,
            ctx->pending_command.enable ? 1 : 0,
            ctx->command_pending ? 1 : 0,
            ctx->telemetry_valid ? 1 : 0,
            ctx->telemetry.adc_sample_valid ? 1 : 0,
            ctx->telemetry.pwm_enable_command ? 1 : 0,
            fake->active_compare,
            fake->pending_compare,
            fake->active_enable ? 1 : 0,
            fake->pending_enable ? 1 : 0,
            fake->communication_calls,
            fake->storage_calls,
            fake->event_count);
}

int main(int argc, char **argv)
{
    DpControlIsrConfig cfg;
    DpFirmwareContext ctx;
    DpFirmwareCommand command;
    DpFirmwareTelemetry telemetry;
    FakeDpHalState fake;
    DpFirmwareHal hal;
    FILE *event_file;
    FILE *state_file;
    size_t event_start;

    if (argc != 3)
    {
        fprintf(stderr, "usage: %s <events.csv> <states.csv>\n", argv[0]);
        return 2;
    }
    event_file = fopen(argv[1], "w");
    state_file = fopen(argv[2], "w");
    if (event_file == NULL || state_file == NULL)
    {
        fprintf(stderr, "failed to open output csv\n");
        return 2;
    }
    fprintf(event_file, "phase,event_order,event\n");
    fprintf(state_file,
            "phase,control_cycles,active_command_enable,pending_command_enable,command_pending,telemetry_valid,"
            "adc_sample_valid,pwm_enable_command,hal_active_compare,hal_pending_compare,hal_active_enable,hal_pending_enable,"
            "communication_calls,storage_calls,total_events\n");

    DpControlIsr_DefaultConfig(&cfg);
    DpFirmware_Init(&ctx, &cfg);
    FakeDpHal_Init(&fake);
    hal = FakeDpHal_Bind(&fake);

    command.enable = true;
    command.clear_fault = false;
    event_start = fake.event_count;
    DpFirmware_RequestCommand(&ctx, &hal, &command);
    write_new_events(event_file, &fake, "command_enable", event_start);
    write_state(state_file, "command_enable", &ctx, &fake);

    event_start = fake.event_count;
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    write_new_events(event_file, &fake, "startup_isr", event_start);
    write_state(state_file, "startup_isr", &ctx, &fake);

    event_start = fake.event_count;
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    write_new_events(event_file, &fake, "apply_isr", event_start);
    write_state(state_file, "apply_isr", &ctx, &fake);

    event_start = fake.event_count;
    DpFirmware_BackgroundStep(&hal);
    write_new_events(event_file, &fake, "background", event_start);
    write_state(state_file, "background", &ctx, &fake);

    event_start = fake.event_count;
    DpFirmware_ReadTelemetry(&ctx, &hal, &telemetry);
    write_new_events(event_file, &fake, "telemetry_read", event_start);
    write_state(state_file, "telemetry_read", &ctx, &fake);

    command.enable = false;
    event_start = fake.event_count;
    DpFirmware_RequestCommand(&ctx, &hal, &command);
    write_new_events(event_file, &fake, "command_disable", event_start);
    write_state(state_file, "command_disable", &ctx, &fake);

    event_start = fake.event_count;
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    write_new_events(event_file, &fake, "disable_isr", event_start);
    write_state(state_file, "disable_isr", &ctx, &fake);

    command.enable = true;
    event_start = fake.event_count;
    DpFirmware_RequestCommand(&ctx, &hal, &command);
    write_new_events(event_file, &fake, "command_restart", event_start);
    write_state(state_file, "command_restart", &ctx, &fake);

    event_start = fake.event_count;
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    write_new_events(event_file, &fake, "restart_queue_isr", event_start);
    write_state(state_file, "restart_queue_isr", &ctx, &fake);

    event_start = fake.event_count;
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    write_new_events(event_file, &fake, "restart_apply_isr", event_start);
    write_state(state_file, "restart_apply_isr", &ctx, &fake);

    fake.adc_sample.iout_code = 3598u;
    event_start = fake.event_count;
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    write_new_events(event_file, &fake, "ocp_isr", event_start);
    write_state(state_file, "ocp_isr", &ctx, &fake);

    fake.adc_sample_valid = false;
    event_start = fake.event_count;
    DpFirmware_ControlIsr(&ctx, &cfg, &hal);
    write_new_events(event_file, &fake, "adc_failure_isr", event_start);
    write_state(state_file, "adc_failure_isr", &ctx, &fake);

    fclose(event_file);
    fclose(state_file);
    printf("SUMMARY,OK,phases=12,events=%zu,control_cycles=%" PRIu32 "\n",
           fake.event_count,
           ctx.control.invocation_count);
    return 0;
}
