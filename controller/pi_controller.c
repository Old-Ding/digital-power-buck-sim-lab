#include "pi_controller.h"

static float clamp_float(float value, float min_value, float max_value)
{
    if (value < min_value) {
        return min_value;
    }
    if (value > max_value) {
        return max_value;
    }
    return value;
}

void pi_controller_init(PiController *controller, float kp, float ki, float out_min, float out_max)
{
    controller->kp = kp;
    controller->ki = ki;
    controller->integrator = 0.0f;
    controller->out_min = out_min;
    controller->out_max = out_max;
}

void pi_controller_reset(PiController *controller)
{
    controller->integrator = 0.0f;
}

float pi_controller_step(PiController *controller, float reference, float feedback)
{
    const float error = reference - feedback;
    const float candidate_integrator = controller->integrator + controller->ki * error;
    const float raw_output = controller->kp * error + candidate_integrator;
    const float limited_output = clamp_float(raw_output, controller->out_min, controller->out_max);

    /*
     * 只在 PI 层处理积分饱和，因为这是控制器内部状态。
     * 保护阈值不在这里判断，避免控制器和保护层重复承担故障检测职责。
     */
    if (raw_output == limited_output ||
        (limited_output == controller->out_max && error < 0.0f) ||
        (limited_output == controller->out_min && error > 0.0f)) {
        controller->integrator = candidate_integrator;
    }

    return limited_output;
}
