#ifndef POWER_STATE_MACHINE_H
#define POWER_STATE_MACHINE_H

#include "protection.h"

typedef enum {
    POWER_STATE_INIT = 0,
    POWER_STATE_IDLE,
    POWER_STATE_SOFT_START,
    POWER_STATE_RUN,
    POWER_STATE_FAULT_LATCH,
    POWER_STATE_RECOVERY
} PowerState;

typedef enum {
    POWER_CMD_NONE = 0,
    POWER_CMD_ENABLE,
    POWER_CMD_DISABLE,
    POWER_CMD_CLEAR_FAULT
} PowerCommand;

typedef struct {
    PowerState state;
    PowerFaultCode latched_fault;
} PowerStateMachine;

void power_state_machine_init(PowerStateMachine *machine);
void power_state_machine_step(PowerStateMachine *machine, PowerCommand command, PowerFaultCode detected_fault);

#endif
