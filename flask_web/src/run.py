import os
import time
from weather_finder import app, app_logger

"""
This module load after app(==__init__.py)
"""

if __name__ == '__main__':
    has_prod = os.environ.get("ENV") == "production"
    # app config SERVER_NAME
    srv_host = app.config["SERVER_NAME"]
    srv_hosts = srv_host.split(":")
    host, port = srv_hosts[0], srv_hosts[1]
    app_logger.info("run.py in host: {}, port: {}".format(host, port))
    if has_prod:
        # Production mode
        try:
            # Prerequisites: pip install waitress
            from waitress import serve
            app_logger.info("Production start.")
            retry = 0
            while True:
                try:
                    serve(app, host=host, port=port)
                    # Not raise OSError 
                    break
                except OSError as oserr:
                    # 16:41:57 xxxxx systemd[1]: Started Flask webapp WeatherFinder service.
                    # ...
                    # 16:42:03 xxxxx avahi-daemon[419]: Registering new address record for ... on eth0.*.
                    # 16:42:03 xxxxx dhcpcd[420]: eth0: soliciting an IPv6 router
                    # 16:42:03 xxxxx start.sh[397]: ERROR:app_main:[Errno 99] Cannot assign requested address
                    # ...
                    # 16:42:04 xxxxx systemd-networkd[157]: eth0: Gained IPv6LL
                    # 16:42:04 xxxxx systemd-timesyncd[349]: Network configuration changed, trying to establish connection.
                    retry += 1
                    app_logger.error(oserr)
                    if retry <= 3:
                        time.sleep(5.0) # if time.sleep(3.0) -> retry:2
                        app_logger.warning("Sleep 5 seconds after retry:{}.".format(retry))
                    else:
                        raise oserr 
        except ImportError:
            # Production with flask,debug False
            app_logger.info("Development start, without debug.")
            app.run(host=host, port=port, debug=False)
    else:
        # Development mode
        app_logger.info("Development start, with debug.")
        app.run(host=host, port=port, debug=True)
