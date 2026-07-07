#ifndef POWER_CONTROL_H
#define POWER_CONTROL_H

#include "pi_controller.h"
#include "power_state_machine.h"
#include "protection.h"

typedef struct {
    float vin_v;
    float vout_v;
    float iout_a;
    float temperature_c;
    float vref_v;
    float duty;
    float pi_integrator;
    PowerState state;
    PowerFaultCode fault_code;
} PowerTelemetry;

typedef struct {
    PiController voltage_loop;
    PowerStateMachine state_machine;
    PowerTelemetry telemetry;
} PowerControl;

void power_control_init(PowerControl *control);
float power_control_step(PowerControl *control, PowerCommand command, PowerMeasurements measurements);

#endif
