#ifndef DIGITAL_POWER_FIRMWARE_H
#define DIGITAL_POWER_FIRMWARE_H

#include "digital_power_control_isr.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct
{
    void (*pwm_update_event)(void *user_context);
    bool (*read_adc_sample)(void *user_context, DpAdcRawSample *sample);
    void (*write_pwm_preload)(void *user_context, uint32_t compare, bool enable);
    void (*disable_pwm_immediate)(void *user_context);
    uint32_t (*enter_critical)(void *user_context);
    void (*exit_critical)(void *user_context, uint32_t key);
    void (*service_communication)(void *user_context);
    void (*service_storage)(void *user_context);
} DpFirmwareHalOps;

typedef struct
{
    const DpFirmwareHalOps *ops;
    void *user_context;
} DpFirmwareHal;

typedef struct
{
    bool enable;
    bool clear_fault;
} DpFirmwareCommand;

typedef struct
{
    uint32_t control_cycle;
    bool adc_sample_valid;
    DpControlState state;
    DpFaultCode active_fault;
    DpFaultCode latched_fault;
    DpFixed vin;
    DpFixed vout;
    DpFixed iout;
    DpFixed temperature;
    DpFixed duty_cmd;
    uint32_t active_compare;
    uint32_t pending_compare;
    bool pwm_enable_command;
    bool active_pwm_enable;
    bool arithmetic_overflow;
} DpFirmwareTelemetry;

typedef struct
{
    DpControlIsrContext control;
    DpFirmwareCommand active_command;
    DpFirmwareCommand pending_command;
    bool command_pending;
    DpFirmwareTelemetry telemetry;
    bool telemetry_valid;
} DpFirmwareContext;

void DpFirmware_Init(DpFirmwareContext *ctx, const DpControlIsrConfig *cfg);
void DpFirmware_RequestCommand(DpFirmwareContext *ctx,
                               const DpFirmwareHal *hal,
                               const DpFirmwareCommand *command);
void DpFirmware_ControlIsr(DpFirmwareContext *ctx,
                           const DpControlIsrConfig *cfg,
                           const DpFirmwareHal *hal);
bool DpFirmware_ReadTelemetry(DpFirmwareContext *ctx,
                              const DpFirmwareHal *hal,
                              DpFirmwareTelemetry *telemetry);
void DpFirmware_BackgroundStep(const DpFirmwareHal *hal);

#endif
