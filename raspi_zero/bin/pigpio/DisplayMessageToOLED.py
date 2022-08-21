import argparse
import logging
import os
import time
import signal
import pigpio
from urllib.parse import unquote_plus
from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.oled.device import ws0010
from PIL import Image, ImageDraw, ImageFont
import util.file_util as FU
from log import logsetting

"""
Continue to output the argument message to the OLED
"""

base_dir = os.path.abspath(os.path.dirname(__file__))
logger = logsetting.create_logger("disp_oled")

# Controller: ws0010
DISPLAY_SIZE = (100, 16)
# Global instance
pi = None
device, interface = None, None
isLogLevelDebug = False


def detect_signal(signum, frame):
    logger.info("signum: {}, frame: {}".format(signum, frame))
    if signum == signal.SIGTERM:
        # signal shutdown or kill
        cleanup()
        exit(0)


def cleanup():
    if device is not None:
        try:
            # The GPIO channel has not been set up as an OUTPUT
            #device.cleanup()
            # Initializes the device memory with an empty (blank) image.
            device.clear()
        except Exception as ex:
            logger.warning(ex)
    pi.stop()


def create_image(width, height):
    return Image.new('1', (width, height)) # '1': Mono


def display_text(text, select_font=None):
    with canvas(device, create_image(device.width, device.height)) as draw:
        draw.text((0, 0), text, font=select_font, fill="white")


def display_list(lines, select_font=None):
    line_cnt = len(lines)
    for i, line in enumerate(lines):
        display_text(line, select_font=select_font)
        if i < line_cnt - 1:
            time.sleep(2)


def scroll_text(text, textWd, textHt, select_font=None, speed=1):
    dx = device.width
    virtual = viewport(device, width=max(device.width, textWd + dx + dx), height=max(textHt, device.height))
    with canvas(virtual) as draw:
        draw.text((dx, 0), text, font=select_font, fill="white")

    i = 0
    while i < dx + textWd:
        virtual.set_position((i, 0))
        i += speed
        time.sleep(0.025)


if __name__ == "__main__":
    pi = pigpio.pi()
    if not pi.connected:
        logger.warning("pigpiod not stated!")
        exit(1)

    # Check shutdown signal
    signal.signal(signal.SIGTERM, detect_signal)

    isLogLevelDebug = logger.getEffectiveLevel() <= logging.DEBUG
    # Self process ID: use process kill
    if isLogLevelDebug:
        pid = os.getpid()
        logger.debug("PID: {}".format(pid))

    parser = argparse.ArgumentParser()
    parser.add_argument("--encoded-message", type=str, required=True, help="URLEncoded message.")
    parser.add_argument("--has-list", action="store_true", default=False, help="Messages with Tab separated.")
    args = parser.parse_args()
    if isLogLevelDebug:
        logger.debug("args: {}".format(args))
    encoded_message = args.encoded_message
    display_message = unquote_plus(encoded_message)
    if isLogLevelDebug:
        logger.debug("display_message: {}".format(display_message))
    # リストならTAB区切り
    has_list = args.has_list
    if has_list:
        display_lines = display_message.split("\t")

    # Configuration
    oled_conf = FU.read_json(os.path.join(base_dir, "conf", "conf_oled.json"))
    if isLogLevelDebug:
        logger.debug("oled_conf: {}".format(oled_conf))
    if_conf = oled_conf["interface"]
    REPEAT_SLEEP = oled_conf["repeatSleep"]
    font_conf = oled_conf["font"]

    # OLED setting.
    interface = bitbang_6800(RS=if_conf["RS"], E=if_conf["E"], PINS=if_conf["PINS"])
    device = ws0010(interface, width=DISPLAY_SIZE[0], height=DISPLAY_SIZE[1])
    try:
        img = create_image(*DISPLAY_SIZE)
        img_draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_conf["name"], font_conf["size"])
        if not has_list:
            txtWd, txtHt = img_draw.textsize(display_message, font=font)
            if isLogLevelDebug:
                logger.debug("txtWd: {}, txtHt: {}".format(txtWd, txtHt))
        one_shot = False
        while True:
            if has_list:
                display_list(display_lines, select_font=font)
            elif txtWd > device.width + 20:
                scroll_text(display_message, txtWd, txtHt, select_font=font)
            else:
                if not one_shot:
                    # at once ON
                    display_text(display_message, select_font=font)
                    one_shot = True

            time.sleep(REPEAT_SLEEP)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
