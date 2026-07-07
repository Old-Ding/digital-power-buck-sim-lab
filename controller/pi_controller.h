#ifndef PI_CONTROLLER_H
#define PI_CONTROLLER_H

typedef struct {
    float kp;
    float ki;
    float integrator;
    float out_min;
    float out_max;
} PiController;

void pi_controller_init(PiController *controller, float kp, float ki, float out_min, float out_max);
void pi_controller_reset(PiController *controller);
float pi_controller_step(PiController *controller, float reference, float feedback);

#endif
