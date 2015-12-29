import subprocess
import threading
import tmax
from time import sleep

__author__ = 'Andres Torti'
logger = tmax.logger

class NetworkHelper(threading.Thread):
    """
    Usefull methods for managing WiFi connections in Linux
    """

    def __init__(self):
        super(NetworkHelper, self).__init__()
        self.max_retries = 3

    def connect_to_wifi(self):
        """
        Connects to the wifi network an blocks until connection is stablished
        :return:
        """
        logger.info("Connecting to wifi!")
        self.run()

    def connect_to_wifi_in_bg(self):
        """
        Connects to the wifi network and returns inmediatly, the connection is done in a background thread
        :return:
        """
        logger.info("Connecting to wifi in background!")
        self.start()

    def kill_wifi(self):
        # Kill every process related to any previous wifi connection
        logger.info("Killing EVERYTHING related to WiFi")
        subprocess.call('/usr/bin/killall wpa_supplicant'.split())
        subprocess.call('/usr/bin/killall dhcpcd'.split())

    def internet_available(self):
        """
        Checks if internet is available pinging www.google.com
        :return: True if there is internet available, False otherwise
        """
        if subprocess.call('ping -c1 www.google.com'.split()) == 0:
            return True
        else:
            return False

    def connected_to_network(self):
        """
        Checks if connected to a WiFi network. Doesn't mean we have Internet.
        :return: True if connected to a network, False otherwise
        """
        if self.get_ip_address() == '0.0.0.0':
            return False
        return True

    def scan_for_networks(self):
        """
        Scans for wifi networks, this will block until the scan is complete
        :return: a list of WiFiNetwork objects containing the information of all the networks found
        """
        try:
            # Scan all the wifi networks
            output = subprocess.check_output('iw dev wlan0 scan'.split())
        except subprocess.CalledProcessError as e:
            logger.error('Couldn\'t run iw dev wlan0 scan' + str(e))
            return

        # Convert the bytes to string, remove tabs and split the lines
        str_output = output.decode('utf-8').replace('\t', '').split('\n')

        # Look for every network property, we must do it in the order they appear in the output from the command
        index = -1  # we start at -1 because the first line we should fine is the one containing 'signal'
        network_list = []
        has_privacy = True

        for line in str_output:
            # This should be the first match for every wifi network
            if 'freq' in line:
                # network has no security method
                if not has_privacy:
                    network_list[index].encryption = "open"

                index += 1
                has_privacy = False
                network_list.append(WiFiNetwork())

            if 'signal' in line:
                # Convert the signal substring to a float number, the line should be something like this:
                #   signal: -89.00 dBm
                network_list[index].signal = float(line[line.find(':') + 1:line.find('dBm') - 1])

            elif 'SSID' in line:
                # Get the SSID of the network, the line is something like this:
                #   SSID: My WiFi SSID
                network_list[index].ssid = line[line.find(':') + 1:].strip()

            elif 'Privacy' in line:
                # The network has some kind of privacy, WPA or WEP, otherwise it's an open network
                has_privacy = True

            elif 'primary channel' in line:
                # Get the channel number, the line is something like this:
                #   * primary channel: 3
                network_list[index].channel = int(line[line.find(':') + 1:])

            elif ('WPA' in line) or ('WEP' in line):
                # Encryption type (not always available), the line is something like this:
                #   WPA:
                if has_privacy:
                    network_list[index].encryption = line[:line.find(':')]

        return network_list

    def get_ip_address(self):
        """
        Get's the current IP address as string
        """
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except:
            return "0.0.0.0"

    def run(self):
        # Kill every process related to any previous wifi connection
        self.kill_wifi()

        logger.info("Running: wpa_supplicant")
        subprocess.call('wpa_supplicant -iwlan0 -c/etc/wpa_supplicant.conf nl80211,wext -B'.split())

        # wpa_supplicant writes the output to dmesg, so we continously read the last message from dmesg
        #  until we get connected (dmesg | tail -1)
        while 'wlcore: Association completed'.encode('utf-8') not in \
                subprocess.check_output('dmesg | tail -1', shell=True):
            sleep(0.001)

        logger.info("Associated to network, checking network SSID")

        # Lets check the network name
        output = subprocess.check_output("iw dev wlan0 link".split())
        # Convert the bytes to string, remove tabs and split the lines
        str_output = output.decode('utf-8').replace('\t', '').split('\n')

        # Look for the network SSID
        for line in str_output:
            if 'SSID:' in line:
                logger.info("Connected to " + line)
                break

        logger.info("Getting an IP address")
        # So lets get an IP address, this will block until the command exits
        try:
            output = subprocess.check_output("dhcpcd wlan0".split())
        except subprocess.CalledProcessError as e:
            logger.error("Couldn't get an IP address, exiting!\n" + str(e))
            return

        # We got an IP address! Lets check it out
        # Convert the bytes to string, remove tabs and split the lines
        str_output = output.decode('utf-8').replace('\t', '').split('\n')

        for line in str_output:
            # Print the IP address
            if 'wlan0: leased' in line:
                logger.info(line)


class WiFiNetwork:
    def __init__(self, ssid="", signal=0, channel=-1, encryption="unknown"):
        """
        Creates a definition of a WiFi network
        :param ssid: string with the SSID of the network
        :param signal: float value indicating the signal intensity in dBm
        :param channel: integer indicating channel number
        :param encryption: string indicating type of encryption ("WAP", "WEP", "open", "unknown")
        """
        self.ssid = ssid
        self.signal = signal
        self.channel = channel
        self.encryption = encryption