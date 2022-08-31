import logging
import os
import signal
import subprocess
import time
import threading
import pigpio

import util.file_util as FU
from log import logsetting

"""
Buttons startup srcipt on service
"""

base_dir = os.path.abspath(os.path.dirname(__file__))
logger = logsetting.create_logger("service_buttonstart")


pi = None
conf_app = None
cb_list = []
isLogLevelDebug = False
# Prevent chattering
prev_tick = 0
THRESHOLD_DIFF_TICK = 500000


def detect_signal(signum, frame):
    """
    Detect shutdown, and execute cleanup.
    :param signum: Signal number
    :param frame: frame
    """
    logger.info("signum: {}, frame: {}".format(signum, frame))
    if signum == signal.SIGTERM:
        # signal shutdown or kill
        cleanup()
        # Current process terminate
        exit(0)


def cleanup():
    for _cb in cb_list:
        _cb.cancel()
    pi.stop()


def subproc_start(script):
    script_name = os.path.basename(script)
    try:
        logger.info("Subprocess {} start.".format(script_name))
        exec_status = subprocess.run([script])
        logger.info("Subprocess {} terminated: {}".format(script_name, exec_status))
    except Exception as ex:
        logger.warning(ex)


def change_actions(gpio_pin, level, tick):
    global prev_tick
    logger.info("pin: {}, level: {}, tick: {}".format(gpio_pin, level, tick))
    if prev_tick != 0:
        tick_diff = pigpio.tickDiff(prev_tick, tick)
        if isLogLevelDebug:
            logger.debug("tick_diff:{}".format(tick_diff))
        if tick_diff < THRESHOLD_DIFF_TICK:
            logger.info("tick_diff:{} < {} return".format(tick_diff, THRESHOLD_DIFF_TICK))
            return

    prev_tick = tick
    for action in conf_app["actions"]:
        button_service = conf_app[action]
        act_pin = button_service["PIN"]
        if act_pin == gpio_pin and button_service["enable"]:
            script = button_service["script"]
            script_name = os.path.basename(script)
            subprc_thread = threading.Thread(target=subproc_start, args=(script,))
            logger.info("Subprocess {} thread start".format(script_name))
            subprc_thread.start()


def setup_gpio():
    global cb_list
    for action in conf_app["actions"]:
        button_service = conf_app[action]
        if isLogLevelDebug:
            logger.debug("{}: {}".format(action, button_service))
        act_pin = button_service["PIN"]
        act_PUD_down = button_service["PUD_down"]
        pi.set_mode(act_pin, pigpio.INPUT)
        if act_PUD_down:
            pi.write(act_pin, pigpio.LOW)
            pi.set_pull_up_down(act_pin, pigpio.PUD_DOWN)
            cb_action = pi.callback(act_pin, pigpio.RISING_EDGE, change_actions)
        else:
            pi.write(act_pin, pigpio.HIGH)
            pi.set_pull_up_down(act_pin, pigpio.PUD_UP)
            cb_action = pi.callback(act_pin, pigpio.FALLING_EDGE, change_actions)
        # Callback
        cb_list.append(cb_action)
    if isLogLevelDebug:
        logger.debug("Callback list: {}".format(cb_list))


if __name__ == '__main__':
    pi = pigpio.pi()
    if not pi.connected:
        logger.warning("pigpiod not stated!")
        exit(1)

    # Check shutdown signal
    signal.signal(signal.SIGTERM, detect_signal)

    isLogLevelDebug = logger.getEffectiveLevel() <= logging.DEBUG
    conf_app = FU.read_json(os.path.join(base_dir, "conf", "conf_buttonstart.json"))
    if isLogLevelDebug:
        logger.debug(conf_app)

    setup_gpio()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
