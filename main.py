import platform
import tmax
import octoprint
import threading
import argparse
import sys
import time

__author__ = 'Andres Torti'


def update_glcd_values():
    try:
        # If we are connected to the printer send data to the LCD
        if octo_api.is_printer_connected():
            tmax_api.send_printtime_left(octo_api.get_print_time_left())
            tmax_api.send_elapsed_printtime(octo_api.get_elapsed_print_time())
            tmax_api.send_print_progress(octo_api.get_print_progress())
            tmax_api.send_extruder_temp(octo_api.get_extruder_target_temp(), octo_api.get_extruder_current_temp())
            tmax_api.send_file_printing(octo_api.get_file_printing())
    except Exception as e:
        tmax.logger.warning("Error communicating with Octoprint " + str(e))

    # Update the printer parameters every 500ms
    threading.Timer(0.5, update_glcd_values).start()

if __name__ == '__main__':
    # If some command was passed, parse it, otherwise run as default app
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument('--bedtemp', help='set bed temperature in degrees centigrade', type=int)
        parser.add_argument('--killwifi', help='disconnects from the WiFi network', action='store_true')
        parser.add_argument('--shutdown',
                            help='power off the system by first disconnecting wifi and telling the controller board',
                            action='store_true')
        args = parser.parse_args()

        # Send bed temp
        if args.bedtemp:
            tmax_api = tmax.TmaxAPI('/dev/ttyO3', 9600, None, 20)
            tmax_api.send_bed_temp(args.bedtemp)
            sys.exit()

        # Disconnect from WiFi
        if args.killwifi:
            wifi = tmax.WiFiHelper()
            wifi.kill_wifi()
            sys.exit()

        # Shutdown!
        if args.shutdown:
            # kill wifi!
            tmax.logger.info('Killing WiFi')
            wifi = tmax.WiFiHelper()
            wifi.kill_wifi()
            wifi.kill_wifi()

            # Open serial port
            tmax_api = tmax.TmaxAPI('/dev/ttyO3', 9600, None, 20)

            # Shutdown!
            import subprocess
            tmax.logger.info('Stoping octoprint')
            subprocess.call('killall --signal SIGINT octoprint'.split())    # kill octoprint

            # Tell the controller board we are shutting down
            tmax_api.send_shutting_down()

            # Process running
            tmax.logger.info('Process running right now')
            tmax.logger.info(subprocess.check_output('ps ef -u root'.split()).decode('utf-8'))

            # We killed wifi, octoprint and python3 instance, shutdown now
            tmax.logger.info('Shutting down!')
            subprocess.call('shutdown -h now'.split())
            sys.exit()

    # Platform info
    tmax.logger.info(platform.uname())

    # WiFi connection
    wifi = tmax.WiFiHelper()
    if not wifi.connected_to_network():
        wifi.connect_to_wifi()
    else:
        tmax.logger.info("Already in network!")

    # Octoprint REST API
    octo_api = octoprint.OctoprintAPI('localhost')

    # Open /dev/ttyO3 which corresponds to UART4
    tmax_api = tmax.TmaxAPI('/dev/ttyO3', 9600, octo_api, 20)

    # Tell the control board we are starting octoprint
    tmax_api.send_octoprintstarting(tmax.get_octoprint_version())

    # Run octoprint outside root user, that is, without superuser privileges
    octoprint_server = tmax.OctoprintExecuter()
    octoprint_server.start_octoprint()
    while not octoprint_server.is_server_running():
        pass

    # Add callbacks and start listenening for incoming data in UART4
    #tmax_api.start_listening_port()

    # Tell the control board we are ready!
    tmax.logger.info('Sending system started')
    tmax_api.send_system_started()
    tmax_api.send_ip_address(wifi.get_ip_address())
    update_glcd_values()

    while True:
        # Always check in case we loose connection
        if not wifi.connected_to_network():
            tmax.logger.warn("Connection lost, trying to reconnect to network")
            tmax_api.send_wifioff()
            wifi.connect_to_wifi()
            tmax_api.send_ip_address(wifi.get_ip_address())

        # After checking if I'm connected and trying to connect if I wasn't let's check if the connection was
        #  or not successful and update the status in the LCD
        if wifi.connected_to_network():
            if wifi.internet_available():
                tmax_api.send_wifi_internet()
            else:
                tmax_api.send_wifion()
        else:
            tmax_api.send_wifioff()

        # Refresh the status every 5 seconds, no need to check it so fast
        time.sleep(5)

