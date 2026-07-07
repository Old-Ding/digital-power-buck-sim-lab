#include "power_state_machine.h"

void power_state_machine_init(PowerStateMachine *machine)
{
    machine->state = POWER_STATE_INIT;
    machine->latched_fault = POWER_FAULT_NONE;
}

void power_state_machine_step(PowerStateMachine *machine, PowerCommand command, PowerFaultCode detected_fault)
{
    if (detected_fault != POWER_FAULT_NONE) {
        machine->state = POWER_STATE_FAULT_LATCH;
        machine->latched_fault = detected_fault;
        return;
    }

    switch (machine->state) {
    case POWER_STATE_INIT:
        machine->state = POWER_STATE_IDLE;
        break;

    case POWER_STATE_IDLE:
        if (command == POWER_CMD_ENABLE) {
            machine->state = POWER_STATE_SOFT_START;
        }
        break;

    case POWER_STATE_SOFT_START:
        machine->state = POWER_STATE_RUN;
        break;

    case POWER_STATE_RUN:
        if (command == POWER_CMD_DISABLE) {
            machine->state = POWER_STATE_IDLE;
        }
        break;

    case POWER_STATE_FAULT_LATCH:
        if (command == POWER_CMD_CLEAR_FAULT) {
            machine->state = POWER_STATE_RECOVERY;
            machine->latched_fault = POWER_FAULT_NONE;
        }
        break;

    case POWER_STATE_RECOVERY:
        machine->state = POWER_STATE_IDLE;
        break;

    default:
        machine->state = POWER_STATE_INIT;
        machine->latched_fault = POWER_FAULT_NONE;
        break;
    }
}
