#include "digital_power_firmware.h"

#include <string.h>

static void dp_firmware_publish_telemetry(DpFirmwareContext *ctx,
                                          const DpControlIsrOutput *control_out,
                                          bool adc_sample_valid)
{
    ctx->telemetry.control_cycle = control_out->invocation_count;
    ctx->telemetry.adc_sample_valid = adc_sample_valid;
    ctx->telemetry.state = control_out->state;
    ctx->telemetry.active_fault = control_out->active_fault;
    ctx->telemetry.latched_fault = control_out->latched_fault;
    ctx->telemetry.vin = control_out->vin;
    ctx->telemetry.vout = control_out->vout;
    ctx->telemetry.iout = control_out->iout;
    ctx->telemetry.temperature = control_out->temperature;
    ctx->telemetry.duty_cmd = control_out->duty_cmd;
    ctx->telemetry.active_compare = control_out->active_compare_after_update;
    ctx->telemetry.pending_compare = control_out->pending_compare_after_control;
    ctx->telemetry.pwm_enable_command = control_out->pwm_enable_command;
    ctx->telemetry.active_pwm_enable = control_out->active_pwm_enable;
    ctx->telemetry.arithmetic_overflow = control_out->arithmetic_overflow;
    ctx->telemetry_valid = true;
}

void DpFirmware_Init(DpFirmwareContext *ctx, const DpControlIsrConfig *cfg)
{
    DpControlIsr_Init(&ctx->control, cfg);
    ctx->active_command.enable = false;
    ctx->active_command.clear_fault = false;
    ctx->pending_command = ctx->active_command;
    ctx->command_pending = false;
    memset(&ctx->telemetry, 0, sizeof(ctx->telemetry));
    ctx->telemetry_valid = false;
}

void DpFirmware_RequestCommand(DpFirmwareContext *ctx,
                               const DpFirmwareHal *hal,
                               const DpFirmwareCommand *command)
{
    const uint32_t key = hal->ops->enter_critical(hal->user_context);

    // 完整命令在短临界区内发布，ISR 不会看到一半新、一半旧的字段。
    ctx->pending_command = *command;
    ctx->command_pending = true;
    hal->ops->exit_critical(hal->user_context, key);
}

void DpFirmware_ControlIsr(DpFirmwareContext *ctx,
                           const DpControlIsrConfig *cfg,
                           const DpFirmwareHal *hal)
{
    DpAdcRawSample sample;
    DpControlIsrOutput control_out;
    bool sample_valid;

    hal->ops->pwm_update_event(hal->user_context);
    memset(&sample, 0, sizeof(sample));
    sample_valid = hal->ops->read_adc_sample(hal->user_context, &sample);

    if (ctx->command_pending)
    {
        ctx->active_command = ctx->pending_command;
        ctx->command_pending = false;
    }

    sample.enable = sample_valid && ctx->active_command.enable;
    sample.clear_fault = sample_valid && ctx->active_command.clear_fault;
    DpControlIsr_OnPwmUpdate(&ctx->control, cfg, &sample, &control_out);
    ctx->active_command.clear_fault = false;

    // 关闭动作先执行，预装载写入只负责下一次更新事件。
    if (!sample_valid || !control_out.pwm_enable_command)
    {
        hal->ops->disable_pwm_immediate(hal->user_context);
    }
    hal->ops->write_pwm_preload(hal->user_context,
                                control_out.pending_compare_after_control,
                                sample_valid && control_out.pwm_enable_command);

    dp_firmware_publish_telemetry(ctx, &control_out, sample_valid);
}

bool DpFirmware_ReadTelemetry(DpFirmwareContext *ctx,
                              const DpFirmwareHal *hal,
                              DpFirmwareTelemetry *telemetry)
{
    bool valid;
    const uint32_t key = hal->ops->enter_critical(hal->user_context);

    valid = ctx->telemetry_valid;
    if (valid)
    {
        *telemetry = ctx->telemetry;
    }
    hal->ops->exit_critical(hal->user_context, key);
    return valid;
}

void DpFirmware_BackgroundStep(const DpFirmwareHal *hal)
{
    if (hal->ops->service_communication != NULL)
    {
        hal->ops->service_communication(hal->user_context);
    }
    if (hal->ops->service_storage != NULL)
    {
        hal->ops->service_storage(hal->user_context);
    }
}
