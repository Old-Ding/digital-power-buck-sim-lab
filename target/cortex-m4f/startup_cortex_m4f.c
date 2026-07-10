#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

int main(void);
void Reset_Handler(void);
void Default_Handler(void);
void Control_IRQHandler(void);

typedef void (*InterruptHandler)(void);

__attribute__((section(".isr_vector"), used))
const InterruptHandler g_vector_table[] = {
    (InterruptHandler)&_estack,
    Reset_Handler,
    Default_Handler,
    Default_Handler,
    Default_Handler,
    Default_Handler,
    Default_Handler,
    0,
    0,
    0,
    0,
    Default_Handler,
    Default_Handler,
    0,
    Default_Handler,
    Default_Handler,
    Control_IRQHandler,
};

void Reset_Handler(void)
{
    uint32_t *source = &_sidata;
    uint32_t *destination = &_sdata;

    while (destination < &_edata)
    {
        *destination++ = *source++;
    }

    destination = &_sbss;
    while (destination < &_ebss)
    {
        *destination++ = 0u;
    }

    (void)main();
    for (;;)
    {
    }
}

void Default_Handler(void)
{
    for (;;)
    {
    }
}
