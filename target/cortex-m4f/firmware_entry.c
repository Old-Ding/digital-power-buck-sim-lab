#include "digital_power_firmware.h"

#include <stdint.h>

typedef struct
{
    volatile uint32_t vin_code;
    volatile uint32_t vout_code;
    volatile uint32_t iout_code;
    volatile uint32_t temperature_code;
    volatile uint32_t active_compare;
    volatile uint32_t pending_compare;
    volatile bool active_enable;
    volatile bool pending_enable;
    volatile uint32_t communication_ticks;
    volatile uint32_t storage_ticks;
} CortexM4fRegisterStub;

static DpControlIsrConfig g_config;
static DpFirmwareContext g_firmware;
static CortexM4fRegisterStub g_registers = {
    3237u,
    3039u,
    2606u,
    1179u,
    0u,
    0u,
    false,
    false,
    0u,
    0u,
};

static void target_pwm_update_event(void *user_context)
{
    CortexM4fRegisterStub *registers = (CortexM4fRegisterStub *)user_context;
    registers->active_compare = registers->pending_compare;
    registers->active_enable = registers->pending_enable;
}

static bool target_read_adc_sample(void *user_context, DpAdcRawSample *sample)
{
    CortexM4fRegisterStub *registers = (CortexM4fRegisterStub *)user_context;
    sample->vin_code = registers->vin_code;
    sample->vout_code = registers->vout_code;
    sample->iout_code = registers->iout_code;
    sample->temperature_code = registers->temperature_code;
    return true;
}

static void target_write_pwm_preload(void *user_context, uint32_t compare, bool enable)
{
    CortexM4fRegisterStub *registers = (CortexM4fRegisterStub *)user_context;
    registers->pending_compare = compare;
    registers->pending_enable = enable;
}

static void target_disable_pwm_immediate(void *user_context)
{
    CortexM4fRegisterStub *registers = (CortexM4fRegisterStub *)user_context;
    registers->active_enable = false;
}

static uint32_t target_enter_critical(void *user_context)
{
    uint32_t key;
    (void)user_context;
    __asm__ volatile("mrs %0, primask" : "=r"(key));
    __asm__ volatile("cpsid i" ::: "memory");
    return key;
}

static void target_exit_critical(void *user_context, uint32_t key)
{
    (void)user_context;
    if ((key & 1u) == 0u)
    {
        __asm__ volatile("cpsie i" ::: "memory");
    }
}

static void target_service_communication(void *user_context)
{
    CortexM4fRegisterStub *registers = (CortexM4fRegisterStub *)user_context;
    registers->communication_ticks++;
}

static void target_service_storage(void *user_context)
{
    CortexM4fRegisterStub *registers = (CortexM4fRegisterStub *)user_context;
    registers->storage_ticks++;
}

static const DpFirmwareHalOps TARGET_OPS = {
    target_pwm_update_event,
    target_read_adc_sample,
    target_write_pwm_preload,
    target_disable_pwm_immediate,
    target_enter_critical,
    target_exit_critical,
    target_service_communication,
    target_service_storage,
};

static const DpFirmwareHal TARGET_HAL = {
    &TARGET_OPS,
    &g_registers,
};

void Control_IRQHandler(void)
{
    DpFirmware_ControlIsr(&g_firmware, &g_config, &TARGET_HAL);
}

int main(void)
{
    DpFirmwareCommand command;

    DpControlIsr_DefaultConfig(&g_config);
    DpFirmware_Init(&g_firmware, &g_config);
    command.enable = true;
    command.clear_fault = false;
    DpFirmware_RequestCommand(&g_firmware, &TARGET_HAL, &command);

    for (;;)
    {
        DpFirmware_BackgroundStep(&TARGET_HAL);
        __asm__ volatile("wfi");
    }
}
