import serial
import logging
import struct
import threading
import subprocess
import sys
import inspect
import queue
import re

__author__ = 'Andres Torti'

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('[%(levelname)s] [%(threadName)s] %(asctime)s : %(message)s',
                                      datefmt='%d/%m/%Y %I:%M:%S %p')
console_handler.setFormatter(console_formatter)

file_handler = logging.FileHandler('tmax_micro.log')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('[%(levelname)s] [%(threadName)s] %(asctime)s : %(message)s',
                                   datefmt='%d/%m/%Y %I:%M:%S %p')
file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def get_octoprint_version():
    version = subprocess.check_output('/home/andres/OctoPrint/venv/bin/octoprint --version'.split()).decode('utf-8')
    if 'dev' in version:
        p = re.compile('([0-9]\.[0-9]\.[0-9]\.dev?)')  # Match version
        return p.search(version).group()
    else:
        p = re.compile('([0-9]\.[0-9]\.[0-9])')
        return p.search(version).group()


class TmaxAPI(threading.Thread):
    """
    API for communication with the control board
    """
    # Protocol definitions
    START_BYTE = 0x0A
    STOP_BYTE = 0xA0

    # Data Types
    SYSTEM_STARTED = 0
    EXTRUDER_TEMPERATURE = 1
    FILE_PRINTING = 2
    PRINT_PROGRESS = 3
    PRINT_TIME_LEFT = 4
    ELAPSED_PRINT_TIME = 5
    BED_TEMPERATURE = 6
    SHUTTING_DOWN = 8
    OCTOPRINT_STARTING = 9

    WIFI_OFF = 10
    WIFI_ON = 11
    WIFI_INTERNET = 12
    IP_ADDRESS = 13

    # State machine status
    READING_START = 1
    READING_TYPE = 2
    READING_COUNT = 3
    READING_DATA = 4
    READING_STOP = 5
    PARSE_COMMAND = 6

    def __init__(self, serialport, baud, octoprint_api, writetimeout=1):
        """
        API for communication with the control board
        :param serialport:     serial port used for communication (ie: /dev/ttyO3)
        :param baud:           baud rate
        :param writetimeout:   timeout for writing data in seconds
        :param octoprint_api   octoprint API to use to communicate with
        """
        super(TmaxAPI, self).__init__()

        # Variables needed for incomming commands treatment
        self.fifo = queue.Queue(maxsize=1024)
        self.state_machine_status = self.READING_START
        self.octoprint_api = octoprint_api
        self.frame = {}
        self.byteCounter = 0
        self.callback_map = {}

        # Open serial port
        try:
            self.ser = serial.Serial(serialport, baud, writeTimeout=writetimeout, timeout=0.1)
        except serial.SerialException as e:
            logger.error("Couldn't open serial port!" + e)
            raise  # re-raise the exception

        logger.info("Opened port " + self.ser.name)

    def start_listening_port(self):
        """
        Starts a thread that will listen to incoming data in the port opened
        """
        self.start()

    def add_command_callback(self, command_type, callback_method):
        """
        Add a callback function to be executed when the specific command is received
        :param command_type: when this command is received the method is called. The available command types
                             are available inside this class, for example TmaxApi.PAUSE_JOB
        :param callback_method: method to call when the command is received. When the method is executed the received
                                command frame is passed to it
        """
        self.callback_map[command_type] = callback_method

    # Continously read data from the serial port and put it in a Queue
    def run(self):
        while True:
            try:
                # Check for incoming data in the serial port with a specified timeout, when a byte is read
                #  or read timeout is reached we check for available data and build a command frame, when the
                #  frame is completed execute the corresponding callbacks
                d = int.from_bytes(self.ser.read(), byteorder='little')
                self.fifo.put(d)
                self._check_data(0.1)
            except queue.Empty as e:
                logger.info("Empty queue, reading timeout " + str(e))

    def _check_data(self, timeout):
        """
        Checks incoming data and executes the corresponding commands. This should be called periodically to
         analyze incoming data after calling start_listening_port()
        """
        if not self.fifo.empty():

            try:
                # Start byte
                if self.state_machine_status == self.READING_START:
                    if self.fifo.get(timeout=timeout) == self.START_BYTE:
                        self.state_machine_status = self.READING_TYPE
                        self.frame = {}  # Clear the previous frame

                # Data type
                elif self.state_machine_status == self.READING_TYPE:
                    self.frame['type'] = self.fifo.get(timeout=timeout)
                    self.state_machine_status = self.READING_COUNT

                # Byte count
                elif self.state_machine_status == self.READING_COUNT:
                    self.frame['count'] = self.fifo.get(timeout=timeout)
                    self.state_machine_status = self.READING_DATA
                    self.byteCounter = 0

                # Data
                elif self.state_machine_status == self.READING_DATA:
                    data = []

                    while self.byteCounter < self.frame['count']:
                        data.append(self.fifo.get(timeout=timeout))
                        self.byteCounter += 1

                    self.frame['data'] = data
                    self.state_machine_status = self.READING_STOP

                # Stop byte
                elif self.state_machine_status == self.READING_STOP:
                    if self.fifo.get(timeout=timeout) == self.STOP_BYTE:
                        self.state_machine_status = self.PARSE_COMMAND

                # Parse command
                elif self.state_machine_status == self.PARSE_COMMAND:
                    self._parse_command(self.frame)

            except queue.Empty as e:
                logger.error('Empty queue exception ' + str(e))

    def _parse_command(self, frame):
        for command_type, callback in self.callback_map.items():
            if command_type == frame['type']:
                callback(frame)

    def send_frame(self, datatype, data):
        """
        Sends a frame thorugh the opened serial port
        :param datatype:    data type to be sent
        :param data:        bytes, list, integer or string to be sent
        """

        # Convert string to bytes object
        if isinstance(data, str):
            data = data.encode("utf-8")

        # Determine the number of bytes
        if isinstance(data, int):
            bytecount = 1
        else:
            try:
                bytecount = len(data)
            except TypeError:
                bytecount = 0

        # Create a bytearray with the frame size
        frame = bytearray()
        frame.append(TmaxAPI.START_BYTE)
        frame.append(datatype)
        frame.append(bytecount)

        if bytecount > 0:
            # if we have a list, iterate over it
            if (isinstance(data, list) and isinstance(data[0], int)) or isinstance(data, str) or isinstance(data,
                                                                                                            bytes):
                for i in data:
                    frame.append(i)
            # otherwise append the integer value
            elif isinstance(data, int):
                frame.append(data)
            else:
                # If we can't find a valid data type, just return, invalid frame I guess
                logger.error("Couldn't find a valid data type in send_frame() - " + str(data) +
                             " - Caller is: " + inspect.stack()[1][3])
                return

        frame.append(TmaxAPI.STOP_BYTE)

        # Send the frame
        self.ser.write(frame)

    def send_ip_address(self, ip_address):
        """
        Sends the defined IP address to be shown in the GLCD
        :param ip_address: IP address as string
        """
        self.send_frame(TmaxAPI.IP_ADDRESS, ip_address)

    def send_wifioff(self):
        self.send_frame(TmaxAPI.WIFI_OFF, None)

    def send_wifion(self):
        self.send_frame(TmaxAPI.WIFI_ON, None)

    def send_wifi_internet(self):
        self.send_frame(TmaxAPI.WIFI_INTERNET, None)

    def send_system_started(self):
        """
        Sends a frame indicating that the system has started
        """
        self.send_frame(TmaxAPI.SYSTEM_STARTED, None)

    def send_octoprintstarting(self, version):
        """
        Sends octoprint version
        :param version:         octoprint version as string
        """
        self.send_frame(TmaxAPI.OCTOPRINT_STARTING, version)

    def send_extruder_temp(self, target_temp, current_temp):
        """
        Sends the extruder target and current temperature
        :param target_temp:     target temperature in degrees centigrade (0 to 65535 integer)
        :param current_temp:    current temperature in degrees centigrade (0 to 65535 integer)
        """
        # Convert each integer to 2 bytes ('H')
        b = struct.pack("H", target_temp) + struct.pack('H', current_temp)
        self.send_frame(TmaxAPI.EXTRUDER_TEMPERATURE, b)

    def send_bed_temp(self, temp):
        """
        Sends the bed temperature
        :param temp: desired bed temperature in degrees centigrade as an integer from 0 to 255
        """
        self.send_frame(TmaxAPI.BED_TEMPERATURE, temp)

    def send_file_printing(self, filename):
        """
        Sends an string containing the name of the file being printed
        :param filename:        name of the file
        """
        self.send_frame(TmaxAPI.FILE_PRINTING, filename)

    def send_print_progress(self, progress):
        """
        Sends the print progress
        :param progress:        printing progress as an integer from 0 to 100
        """
        self.send_frame(TmaxAPI.PRINT_PROGRESS, progress)

    def send_printtime_left(self, time):
        """
        Sends the time left for the printing to complete
        :param time:            time for the printing to complete in seconds
        """
        b = struct.pack("I", time)  # Convert integer to 4 bytes ('I')
        self.send_frame(TmaxAPI.PRINT_TIME_LEFT, b)

    def send_elapsed_printtime(self, elapsed_time):
        """
        Sends the printing's elapsed time
        :param elapsed_time:    elapsed time in seconds
        """
        b = struct.pack("I", elapsed_time)  # Convert integer to 4 bytes ('I')
        self.send_frame(TmaxAPI.ELAPSED_PRINT_TIME, b)

    def send_shutting_down(self):
        """
        Alerts the control board we are shutting down!
        """
        self.send_frame(TmaxAPI.SHUTTING_DOWN, None)


class OctoprintExecuter(threading.Thread):
    def __init__(self):
        super(OctoprintExecuter, self).__init__()
        self.server_running = False

    def is_server_running(self):
        return self.server_running

    def start_octoprint(self):
        """
        Runs octoprint in a background thread
        """
        self.start()

    def run(self):
        logger.info("Starting Octoprint")

        # start octoprint with elevated proccess priority and running it as daemon
        command_run = 'nice -n -10 su andres -c "/home/andres/OctoPrint/venv/bin/octoprint --daemon start"'
        command_stop = 'nice -n -10 su andres -c "/home/andres/OctoPrint/venv/bin/octoprint --daemon stop"'

        while subprocess.call(command_run, shell=True) != 0:
            subprocess.call(command_stop, shell=True)

        # read octoprint log while running
        popen = subprocess.Popen('tail -f /home/andres/.octoprint/logs/octoprint.log', stdout=subprocess.PIPE, shell=True)
        lines_iterator = iter(popen.stdout.readline, b"")

        for line in lines_iterator:
            # print octoprint output
            print(line.decode('utf-8'), end="")

            if 'octoprint.server - INFO - Listening on'.encode('utf-8') in line:
                self.server_running = True
                logger.info('Octoprint started!')

            elif 'octoprint.server - INFO - Goodbye!'.encode('utf-8') in line:
                self.server_running = False
                logger.info('Octoprint closed!')
