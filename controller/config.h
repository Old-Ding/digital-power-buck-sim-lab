#ifndef DIGITAL_POWER_CONFIG_H
#define DIGITAL_POWER_CONFIG_H

#define POWER_PWM_FREQ_HZ          (200000.0f)
#define POWER_CONTROL_FREQ_HZ       (50000.0f)
#define POWER_CONTROL_DT_SEC        (1.0f / POWER_CONTROL_FREQ_HZ)

#define POWER_VOUT_TARGET_V         (12.0f)
#define POWER_DUTY_MIN              (0.02f)
#define POWER_DUTY_MAX              (0.92f)

#define POWER_SOFT_START_TIME_SEC   (0.050f)
#define POWER_SOFT_START_STEP_V     (POWER_VOUT_TARGET_V / (POWER_SOFT_START_TIME_SEC * POWER_CONTROL_FREQ_HZ))

#define POWER_UVLO_THRESHOLD_V      (16.0f)
#define POWER_UVLO_RECOVER_V        (18.0f)
#define POWER_OVP_THRESHOLD_V       (13.2f)
#define POWER_OCP_THRESHOLD_A       (6.0f)
#define POWER_OTP_THRESHOLD_C       (95.0f)

#define POWER_PI_KP                 (0.035f)
#define POWER_PI_KI                 (0.0015f)

#endif
