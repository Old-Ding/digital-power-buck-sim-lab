#include "config.h"
#include "power_control.h"

static float update_soft_start_reference(float current_reference)
{
    const float next_reference = current_reference + POWER_SOFT_START_STEP_V;
    return next_reference > POWER_VOUT_TARGET_V ? POWER_VOUT_TARGET_V : next_reference;
}

void power_control_init(PowerControl *control)
{
    pi_controller_init(&control->voltage_loop, POWER_PI_KP, POWER_PI_KI, POWER_DUTY_MIN, POWER_DUTY_MAX);
    power_state_machine_init(&control->state_machine);

    control->telemetry.vin_v = 0.0f;
    control->telemetry.vout_v = 0.0f;
    control->telemetry.iout_a = 0.0f;
    control->telemetry.temperature_c = 25.0f;
    control->telemetry.vref_v = 0.0f;
    control->telemetry.duty = 0.0f;
    control->telemetry.pi_integrator = 0.0f;
    control->telemetry.state = POWER_STATE_INIT;
    control->telemetry.fault_code = POWER_FAULT_NONE;
}

float power_control_step(PowerControl *control, PowerCommand command, PowerMeasurements measurements)
{
    const PowerFaultCode detected_fault = protection_check(&measurements);
    power_state_machine_step(&control->state_machine, command, detected_fault);

    control->telemetry.vin_v = measurements.vin_v;
    control->telemetry.vout_v = measurements.vout_v;
    control->telemetry.iout_a = measurements.iout_a;
    control->telemetry.temperature_c = measurements.temperature_c;
    control->telemetry.state = control->state_machine.state;
    control->telemetry.fault_code = control->state_machine.latched_fault;

    switch (control->state_machine.state) {
    case POWER_STATE_SOFT_START:
        control->telemetry.vref_v = update_soft_start_reference(control->telemetry.vref_v);
        control->telemetry.duty = pi_controller_step(&control->voltage_loop, control->telemetry.vref_v, measurements.vout_v);
        break;

    case POWER_STATE_RUN:
        control->telemetry.vref_v = POWER_VOUT_TARGET_V;
        control->telemetry.duty = pi_controller_step(&control->voltage_loop, control->telemetry.vref_v, measurements.vout_v);
        break;

    case POWER_STATE_IDLE:
    case POWER_STATE_FAULT_LATCH:
    case POWER_STATE_RECOVERY:
    case POWER_STATE_INIT:
    default:
        /*
         * 非运行态统一关断 PWM，并复位积分器。
         * 这是状态层对执行器的唯一关断出口，避免各保护项到处直接改 duty。
         */
        control->telemetry.vref_v = 0.0f;
        control->telemetry.duty = 0.0f;
        pi_controller_reset(&control->voltage_loop);
        break;
    }

    control->telemetry.pi_integrator = control->voltage_loop.integrator;
    return control->telemetry.duty;
}
