import math

#Well we are trying to learn the code and do something, here and there was AI code no doubt as we were not skilled enough to be honest 
# ELC25023 and ELC25001 S LALITH ADITHYA ; ADITHYA M


BUFFER_SIZE = 50       # 1 second of data at 50Hz
GRAVITY = 9.81         # The Earth Constant bro

# These are some random values to track the ACTIVITY OF THE SAME
STATE_WAITING = 0
STATE_RESTING = 1
STATE_WALKING = 2
STATE_CYCLING = 3
STATE_RUNNING = 4

# SpO2 status codes so we know if the blood oxygen reading is trustworthy or ruined by shaking
SPO2_WAITING = -1.0
SPO2_MOTION_ERROR = -2.0

# We know how python is it just lags and is seriosly super slow; C++ is goated but though its founder quoted its liked getting shot in the knee


# I have learnt about memory overflows and allocation during run time and python being python, to be honest
# I would never prefer python to be in Critical code like SPACE, HPM'S, RADARS, MEDICAL INSTRUMENTS, Python is an interpreter based language and throws error here and there

# Here im just passing this value and telling bro to sample 50 times in a second

ax_buf = [0.0] * BUFFER_SIZE
ay_buf = [0.0] * BUFFER_SIZE
az_buf = [0.0] * BUFFER_SIZE

gx_buf = [0.0] * BUFFER_SIZE
gy_buf = [0.0] * BUFFER_SIZE
gz_buf = [0.0] * BUFFER_SIZE

# Pre-allocating Red and IR (Infrared) LED buffers for pulse oximeter (MAX30102 style sensor)
# Still zero .append() bro, keeping that RAM locked down tight
red_buf = [0.0] * BUFFER_SIZE
ir_buf = [0.0] * BUFFER_SIZE

# YOu will see what this code does in a moment
write_index = 0
samples_collected = 0

# Keeping track of the last good blood oxygen reading in case the user starts sprinting
last_valid_spo2 = 98.0


def add_sensor_data(ax, ay, az, gx, gy, gz, red_led, ir_led):
    """WE are adding a few new values the accelemeter , the gyroscope values obvioulsy bro there are 3 axes + Red & IR LED for SpO2"""
    global write_index, samples_collected

    # 1. Safety check: we make sure sensor didn't send broken values fam (including LEDs now)
    if ax is None or math.isnan(ax) or math.isnan(gx) or math.isnan(red_led) or math.isnan(ir_led):
        return False  # Tell the main loop something is wrong

    # 2. Overwrite the oldest slot in memory (No .append() used!) <- append is not used because it is slow and also creates new obj which is bad for memory
    ax_buf[write_index] = float(ax)
    ay_buf[write_index] = float(ay)
    az_buf[write_index] = float(az)
    gx_buf[write_index] = float(gx)
    gy_buf[write_index] = float(gy)
    gz_buf[write_index] = float(gz)
    
    # Storing light intensity reflected from blood vessels
    red_buf[write_index] = float(red_led)
    ir_buf[write_index] = float(ir_led)

    # 3. Move pointer forward, wrap back to 0 when it hits 50; this is an equivalent of program counter movin to address +4 you know bro
    write_index = write_index + 1
    if write_index >= BUFFER_SIZE:
        write_index = 0

    if samples_collected < BUFFER_SIZE:
        samples_collected = samples_collected + 1

    return True


def check_activity():
    """Figures out what the person is doing using basic math loops. Heard of if else bro?"""


    # Don't guess until our 50-slot memory buffer is full
    if samples_collected < BUFFER_SIZE:
        return STATE_WAITING

    # STEP 1: Combine X, Y, Z into total movement ---
    # I remember inverse square in a quake 3 game, its so peak you should google it ; reciprocal of sq root of 32 bit fp number its so peak bro
    # (Used 3D vector magnitude sqrt(x^2 + y^2 + z^2) so it still works even if
    # the user tilts their wrist or rotates the sensor upside down)
    accel_total = 0.0
    gyro_total = 0.0
    
    # We store magnitudes temporarily in local variables to keep memory flat
    accel_list = [0.0] * BUFFER_SIZE

    for i in range(BUFFER_SIZE):
        a_mag = math.sqrt(ax_buf[i]**2 + ay_buf[i]**2 + az_buf[i]**2)
        g_mag = math.sqrt(gx_buf[i]**2 + gy_buf[i]**2 + gz_buf[i]**2)
        
        accel_list[i] = a_mag
        accel_total = accel_total + a_mag
        gyro_total = gyro_total + g_mag

    accel_avg = accel_total / BUFFER_SIZE
    gyro_avg = gyro_total / BUFFER_SIZE

    # STEP 2: Calculate how "shaky" the movement is (Variance)

    # (Calculating statistical variance by hand here so I don't have to import numpy,
    # which takes up way too much memory and boots too slowly); well i dont want python to say, "you dont have numpy install it" in run time so use C or Rust guys its goated;
    
    shake_score = 0.0
    for i in range(BUFFER_SIZE):
        diff = accel_list[i] - accel_avg
        shake_score = shake_score + (diff * diff)
    
    shake_score = shake_score / BUFFER_SIZE

    # STEP 3: Simple If/Else Decision Tree
    # Single exit variable 
    result = STATE_RESTING

    if shake_score < 0.2:
        # Barely moving at all
        result = STATE_RESTING
    elif shake_score < 2.5 and gyro_avg > 1.2:
        # Smooth rotation (pedaling) without heavy footsteps hitting the ground
        result = STATE_CYCLING
    elif shake_score < 2.5:
        # Moderate footstep impacts
        result = STATE_WALKING
    else:
        # Heavy, rapid shaking = running
        result = STATE_RUNNING

    return result


def estimate_spo2(current_activity):
    """
    Calculates Blood Oxygen (SpO2 %) using Red and IR light waves,

    YOu know bro PHOTOPLETHYSOGRAPHY its goated man

    like you pass ir on skin then check volume , then you see how much percentage of light is absorbed, like deoxygenated less 
    absorbance of ir light so phototransistor knows its deoxygenated; Its called first principles innovation so peak
    also
    but uses the activity state so shaking doesn't give fake hospital alarms.
    """
    global last_valid_spo2

    if samples_collected < BUFFER_SIZE:
        return SPO2_WAITING

    # If bro is running, the sensor bounces on the skin
    # Light leaks in and ruins the math introduces a (Motion Artifact), so we don't trust the new reading
    if current_activity == STATE_RUNNING:
        return SPO2_MOTION_ERROR

    # This is a details on how a IR sensor in a watch works copied it from MR.Gemini like the explanation part
    # (Beer-Lambert law from physics: Oxygenated blood absorbs more Infrared light,
    # while deoxygenated blood absorbs more Red light. We find the AC ripple
    # divided by the DC baseline for both LEDs to get the "Ratio of Ratios" R)

    red_dc = 0.0
    ir_dc = 0.0

    for i in range(BUFFER_SIZE):
        red_dc = red_dc + red_buf[i]
        ir_dc = ir_dc + ir_buf[i]

    red_dc = red_dc / BUFFER_SIZE
    ir_dc = ir_dc / BUFFER_SIZE

    # Prevent division by zero crash (Safety first, Speed next sir!!) you know bro we dont want infinity

    if red_dc <= 0.0 or ir_dc <= 0.0:
        return SPO2_MOTION_ERROR

    # Calculate AC component (the heartbeat pulse wave) using RMS by hand
    red_ac_sum = 0.0
    ir_ac_sum = 0.0

    for i in range(BUFFER_SIZE):
        r_diff = red_buf[i] - red_dc
        ir_diff = ir_buf[i] - ir_dc
        red_ac_sum = red_ac_sum + (r_diff * r_diff)
        ir_ac_sum = ir_ac_sum + (ir_diff * ir_diff)

    red_ac = math.sqrt(red_ac_sum / BUFFER_SIZE)
    ir_ac = math.sqrt(ir_ac_sum / BUFFER_SIZE)

    if ir_ac <= 0.0:
        return SPO2_MOTION_ERROR

    # Ratio of Ratios (R)
    r_value = (red_ac / red_dc) / (ir_ac / ir_dc)

    # Standard empirical calibration formula used in pulse oximeters
    spo2 = 110.0 - (25.0 * r_value)

    # Apply tiny compensation offset if user is walking or cycling (mild motion)

    if current_activity == STATE_WALKING or current_activity == STATE_CYCLING:
        spo2 = spo2 + 0.5  # Slight correction for blood flow/sensor shift

    # Clamp values to humanly possible limits (Automotive range-check rule)
    if spo2 > 100.0:
        spo2 = 100.0
    elif spo2 < 70.0:
        spo2 = 70.0

    last_valid_spo2 = spo2
    return spo2


# QUICK TEST (Simulating a person running vs resting) Lets see if bro runs 

if __name__ == "__main__":

    # TEST 1: Feed 50 fake "running" samples into the system 
    for step in range(50):
        # Alternating high and low Z-axis values to simulate foot stomps
        fake_az = 14.0 if step % 2 == 0 else 5.0
        # Fake heartbeat pulse wave on Red & IR LEDs
        pulse = math.sin(step * 0.4) * 150.0
        fake_red = 50000.0 + (pulse * 0.5)
        fake_ir = 50000.0 + pulse
        
        ok = add_sensor_data(1.2, 0.8, fake_az, 1.5, 1.1, 0.9, fake_red, fake_ir)
        if not ok:
            print("SENSOR ERROR!")
            break

    status = check_activity()
    spo2_val = estimate_spo2(status)

    # Translate number back to English just for printing
    names = ["WAITING", "RESTING", "WALKING", "CYCLING", "RUNNING"]
    print("Test 1 -> Activity:", names[status], "| SpO2:", spo2_val, "(Blocked due to running shake!)")

    # TEST 2: Feed 50 fake "resting" samples so we can see SpO2 actually work
    for step in range(50):
        pulse = math.sin(step * 0.3) * 150.0
        fake_red = 50000.0 + (pulse * 0.48)
        fake_ir = 50000.0 + pulse
        
        # Steady 9.81 gravity = bro is chilling on the couch
        add_sensor_data(0.05, 0.02, 9.81, 0.01, 0.01, 0.01, fake_red, fake_ir)

    status = check_activity()
    spo2_val = estimate_spo2(status)
    print("Test 2 -> Activity:", names[status], "| SpO2:", round(spo2_val, 2), "%")
