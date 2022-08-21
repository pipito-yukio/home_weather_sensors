import argparse
import logging
import subprocess as proc
import time
import pigpio
from log import logsetting

"""
Long push switching to poweroff
[GPIO Pin]: 21
Execute on system service
  systemctl enable switch-to-poweroff.service
"""

logger = logsetting.create_logger("service_poweroff")

# Global instalce
pi = None
# Global callbacks
cb_power_off = None
# args option default
LED_BLINK_PIN = 20
POWER_OFF_PIN = 21
# Long push threashold
LONGPUSH_THRESHOLD = 5 * 1000000 # 5 seconds
# Global variable
prev_tick = 0
shutdown_flag = False
isLogLevelDebug = False


def power_off():
    logger.info("sudo poweroff")
    cleanup()
    """
    User pi "sudo" is not valid
    ret = proc.run(["sudo", "/usr/sbin/poweroff"], shell=True)
    [console] bellow prompt
    usage: sudo -h | -K | -k | -V
    ...
    INFO SwitchToPoweroff.py(33)[power_off] Poweroff status: 
         CompletedProcess(args=['sudo', '-u pi', '/usr/sbin/shutdown', '-h now'], returncode=1)
   """
    # Service Exec user is root
    # sudo /home/pi/bin/switch_to_poweroff.sh
    ret = proc.run(["/usr/sbin/poweroff"], shell=True)
    logger.info("Poweroff status: {}".format(ret))


def change_switch(gpio_pin, level, tick):
    global prev_tick, shutdown_flag
    if isLogLevelDebug:
        logger.debug("pin: {}, level: {}, tick: {}, prev_tick: {}".format(gpio_pin, level, tick, prev_tick))
    if level == 0 and prev_tick == 0:
        prev_tick = tick
        # Start blink LED
        pi.write(LED_BLINK_PIN, pigpio.HIGH)
    elif level == 1 and prev_tick > 0:
        tick_diff = pigpio.tickDiff(prev_tick, tick)
        logger.info("Poweroff Falling tick_diff:{} milli sec".format(tick_diff / 1000))
        # Stop blink LED
        pi.write(LED_BLINK_PIN, pigpio.LOW)
        if tick_diff >= LONGPUSH_THRESHOLD and not shutdown_flag:
            power_off()
            shutdown_flag = True
        prev_tick = 0


def setup_gpio():
    global cb_power_off
    # LED blink pin with Power off SW
    pi.set_mode(LED_BLINK_PIN, pigpio.OUTPUT)
    pi.write(LED_BLINK_PIN, pigpio.LOW)
    # Power off pin
    pi.set_mode(POWER_OFF_PIN, pigpio.INPUT)
    pi.set_pull_up_down(POWER_OFF_PIN, pigpio.PUD_UP)
    pi.write(POWER_OFF_PIN, pigpio.HIGH)
    cb_power_off = pi.callback(POWER_OFF_PIN, pigpio.EITHER_EDGE, change_switch)


def cleanup():
    global cb_power_off
    if cb_power_off is not None:
        cb_power_off.cancel()
        cb_power_off = None
    pi.write(LED_BLINK_PIN, pigpio.LOW)
    pi.stop()


if __name__ == '__main__':
    pi = pigpio.pi()
    if not pi.connected:
        logger.warning("pigpiod not stated!")
        exit(1)

    isLogLevelDebug = logger.getEffectiveLevel() <= logging.DEBUG
    parser = argparse.ArgumentParser()
    parser.add_argument("--poweroff-pin", type=int, default=POWER_OFF_PIN, help="PowerOff SW pin.")
    parser.add_argument("--ledblink-pin", type=int, default=LED_BLINK_PIN, help="Blinking LED pin.")
    args = parser.parse_args()
    logger.info(args)
    POWER_OFF_PIN = args.poweroff_pin
    LED_BLINK_PIN = args.ledblink_pin
    setup_gpio()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
