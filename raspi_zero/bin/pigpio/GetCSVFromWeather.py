import argparse
import os
from db.weatherdb import WeatherFinder
from log import logsetting

"""
Export t_weather to CSV file.
"""

logger = logsetting.create_logger("main_app")

OUTPUT_CSV_PATH = os.environ.get("OUTPUT_CSV_PATH", "~/Downloads/csv/")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-name", type=str, help="Device name with t_device name.")
    parser.add_argument("--date-from", type=str, help="Date from with t_weather.measurement_time.")
    parser.add_argument("--date-to", type=str, help="Date to with t_weather.measuremen_time.")
    parser.add_argument("--without-header", action="store_true", help="Without header.")
    parser.add_argument("--with-device-csv", action="store_true", help="With t_device CSV.")
    args = parser.parse_args()
    logger.info(args)

    weather_finder = WeatherFinder(logger=logger)
    try:
        # from t_weather to csv
        csv_iterable = weather_finder.find(args.device_name, date_from=args.date_from, date_to=args.date_to)
        # filename: build "" + "device name" + "date_from" + "date_to" + "date now" + ".csv"
        csv_file = os.path.join(os.path.expanduser(OUTPUT_CSV_PATH), weather_finder.csv_filename)
        with open(csv_file, 'w', newline='') as fp:
            if not args.without_header:
                fp.write(WeatherFinder.CSV_WEATHER_HEADER)
            for line in csv_iterable:
                fp.write(line + "\n")
        logger.info("Saved Weather CSV: {}".format(csv_file))

        # from t_device to csv with Header
        if args.with_device_csv:
            csv_devices = weather_finder.get_devices()
            # filename: "devices.csv"
            csv_file = os.path.join(os.path.expanduser(OUTPUT_CSV_PATH), WeatherFinder.DEVICE_CSV_FILENAME)
            with open(csv_file, 'w', newline='') as fp:
                # Always has header.
                fp.write(WeatherFinder.CSV_DEVICE_HEADER)
                for line in csv_devices:
                    fp.write(line + "\n")
            logger.info("Saved Device CSV: {}".format(csv_file))
    except Exception as e:
        logger.warning("WeatherFinder error: {}".format(e))
    finally:
        weather_finder.close()

