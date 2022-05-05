import os
import pigpio
import time
import util.file_util as FU
from log import logsetting

"""
Play Melody.
[Terminate]
Terminate button down.
"""

base_dir = os.path.abspath(os.path.dirname(__file__))
logger = logsetting.create_logger("main_app")

# Global instance
pi = None
# Melody IC pin
MELODY_PIN = 23
PLAY_TIME, POSE_TIME, PLAY_REPEAT = 30, 30, 3
# This process terminate button pin
TERMINATE_PIN = 12
# Button callback
cb_terminate = None
# Terminate flag
terminate_on = False


def cleanup():
    if cb_terminate is not None:
        cb_terminate.cancel()
    pi.write(MELODY_PIN, pigpio.LOW)
    pi.write(TERMINATE_PIN, pigpio.LOW)
    pi.stop()


def change_terminate(gpio_pin, level, tick):
    global terminate_on
    logger.info("pin: {}, level: {}, tick: {}".format(gpio_pin, level, tick))
    terminate_on = True


def setup_gpio():
    # Setup terminate pin
    global cb_terminate
    pi.set_mode(TERMINATE_PIN, pigpio.INPUT)
    pi.write(TERMINATE_PIN, pigpio.LOW)
    # Set internal pull-down register.
    pi.set_pull_up_down(TERMINATE_PIN, pigpio.PUD_DOWN)
    # SW OFF(LOW) -> ON(HIGH)
    cb_terminate = pi.callback(TERMINATE_PIN, pigpio.RISING_EDGE, change_terminate)
    # Setup play melody pin
    pi.set_mode(MELODY_PIN, pigpio.OUTPUT)
    pi.write(MELODY_PIN, pigpio.LOW)


def play_melody():
    logger.info("Play melody start.")
    for i in range(PLAY_REPEAT):
        logger.debug("play-{}: terminate_on: {}".format(i + 1, terminate_on))
        if i > 0:
            if terminate_on:
                break

        pi.write(MELODY_PIN, pigpio.HIGH)
        time.sleep(PLAY_TIME)
        pi.write(MELODY_PIN, pigpio.LOW)

        if i < PLAY_REPEAT - 1:
            logger.debug("Pose sleep before check terminate_on: {}".format(terminate_on))
            if terminate_on:
                break
            time.sleep(POSE_TIME)
    logger.info("Play melody completed.")


if __name__ == '__main__':
    pi = pigpio.pi()
    if not pi.connected:
        logger.warning("pigpiod not stated!")
        exit(1)

    # Configuration
    conf = FU.read_json(os.path.join(base_dir, "conf", "conf_melody.json"))
    logger.info("conf_melody: {}".format(conf))
    MELODY_PIN = conf["PIN"]
    PLAY_TIME, POSE_TIME, PLAY_REPEAT = conf["playtime"], conf["posetime"], conf["playrepeat"]
    # Terminate button setting.
    TERMINATE_PIN = conf["actions"]["terminate"]["PIN"]
    logger.debug("MELODY_PIN: {}, TERMINATE_PIN: {}".format(MELODY_PIN, TERMINATE_PIN))
    setup_gpio()

    try:
        play_melody()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
