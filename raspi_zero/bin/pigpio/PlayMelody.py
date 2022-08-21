import logging
import os
import pigpio
import signal
import time
import util.file_util as FU
from log import logsetting

"""
Play Melody.
"""

base_dir = os.path.abspath(os.path.dirname(__file__))
logger = logsetting.create_logger("main_app")

# Global instance
pi = None
# Melody IC pin
MELODY_PIN = 23
PLAY_TIME, POSE_TIME, PLAY_REPEAT = 30, 30, 3
isLogLevelDebug = False


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
    try:
        pi.write(MELODY_PIN, pigpio.LOW)
    except Exception as ex:
        logger.warning(ex)
    pi.stop()


def setup_gpio():
    # Setup play melody pin
    pi.set_mode(MELODY_PIN, pigpio.OUTPUT)
    pi.write(MELODY_PIN, pigpio.LOW)


def play_melody():
    logger.info("Play melody start.")
    for i in range(PLAY_REPEAT):
        if isLogLevelDebug:
            logger.debug("play-{}".format(i + 1))

        pi.write(MELODY_PIN, pigpio.HIGH)
        time.sleep(PLAY_TIME)
        pi.write(MELODY_PIN, pigpio.LOW)

        if i < PLAY_REPEAT - 1:
            time.sleep(POSE_TIME)
    logger.info("Play melody completed.")


if __name__ == '__main__':
    pi = pigpio.pi()
    if not pi.connected:
        logger.warning("pigpiod not stated!")
        exit(1)

    # Check shutdown or kill process signal
    signal.signal(signal.SIGTERM, detect_signal)

    isLogLevelDebug = logger.getEffectiveLevel() <= logging.DEBUG
    # Configuration
    conf = FU.read_json(os.path.join(base_dir, "conf", "conf_melody.json"))
    if isLogLevelDebug:
        logger.debug("conf_melody: {}".format(conf))
    MELODY_PIN = conf["PIN"]
    PLAY_TIME, POSE_TIME, PLAY_REPEAT = conf["playtime"], conf["posetime"], conf["playrepeat"]
    if isLogLevelDebug:
        logger.debug("MELODY_PIN: {}".format(MELODY_PIN))
    setup_gpio()

    try:
        play_melody()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
