import requests

__author__ = 'Andres Torti'


class OctoprintAPI:
    def __init__(self, host):
        self.host = host
        self.s = requests.Session()
        self.s.headers.update({'X-Api-Key': 'E74F1D373ABD4D46A10CD325FFF0C187',
                               'Content-Type': 'application/json'})

    def is_printer_connected(self):
        if self.s.get('http://' + self.host + ':5000/api/printer').status_code != 200:
            return False
        else:
            return True

    def get_printer_status(self):
        data = self.s.get('http://' + self.host + ':5000/api/printer').content.decode('utf-8').split('\n')
        for line in data:
            if 'text' in line:
                # check if null
                if 'null' in line:
                    return 0
                else:
                    return line[line.find(':')+1:line.find(',')]
        return ''

    def set_bed_temp(self, temp):
        r = self.s.post('http://' + self.host + ':5000/api/printer/bed', json={'command': 'target', 'target': temp})
        print(r)
        print(r.content)
        print()

    def pause_job(self):
        r = self.s.post('http://' + self.host + ':5000/api/job', json={'command': 'pause'})

    def resume_job(self):
        r = self.s.post('http://' + self.host + ':5000/api/job', json={'command': 'pause'})

    def start_job(self):
        r = self.s.post('http://' + self.host + ':5000/api/job', json={'command': 'start'})

    def cancel_job(self):
        r = self.s.post('http://' + self.host + ':5000/api/job', json={'command': 'cancel'})

    def get_version(self):
        data = self.s.get('http://' + self.host + ':5000/api/version').content.decode('utf-8').split('\n')
        for line in data:
            if 'server' in line:
                import re
                p = re.compile('([0-9]\.[0-9]\.[0-9]\.dev?)')
                return p.search(line).group()
        return '0.0.0'

    def get_print_progress(self):
        data = self.s.get('http://' + self.host + ':5000/api/job').content.decode('utf-8').split('\n')
        for line in data:
            if 'completion' in line:
                # check if null
                if 'null' in line:
                    return 0
                else:
                    return int(float(line[line.find(':')+1:line.find(',')]))
        return 0

    def get_total_print_time(self):
        data = self.s.get('http://' + self.host + ':5000/api/job').content.decode('utf-8').split('\n')
        for line in data:
            if 'estimatedPrintTime' in line:
                # check if null
                if 'null' in line:
                    return 0
                else:
                    return int(float(line[line.find(':')+1:line.find(',')]))
        return 0

    def get_print_time_left(self):
        data = self.s.get('http://' + self.host + ':5000/api/job').content.decode('utf-8').split('\n')
        for line in data:
            if 'printTimeLeft' in line:
                # check if null
                if 'null' in line:
                    return 0
                else:
                    return int(float(line[line.find(':')+1:]))
        return 0

    def get_elapsed_print_time(self):
        data = self.s.get('http://' + self.host + ':5000/api/job').content.decode('utf-8').split('\n')
        for line in data:
            if 'printTime' in line:
                # check if null
                if 'null' in line:
                    return 0
                else:
                    return int(float(line[line.find(':')+1:line.find(',')]))
        return 0

    def get_file_printing(self):
        data = self.s.get('http://' + self.host + ':5000/api/job').content.decode('utf-8').split('\n')
        for line in data:
            if 'name' in line:
                # check if null
                if 'null' in line:
                    return "Detenido..."
                else:
                    return line[line.find(':')+1:line.find(',')].replace('"', '').strip()
        return "Detenido..."

    def get_extruder_target_temp(self):
        data = self.s.get('http://' + self.host + ':5000/api/printer/tool').content.decode('utf-8').split('\n')
        for line in data:
            if 'target' in line:
                if 'null' in line:
                    return 0
                else:
                    return int( round(float(line[line.find(':')+1:line.find(',')]), 0) )
        return 0

    def get_extruder_current_temp(self):
        data = self.s.get('http://' + self.host + ':5000/api/printer/tool').content.decode('utf-8').split('\n')
        for line in data:
            if 'actual' in line:
                return int( round(float(line[line.find(':')+1:line.find(',')]), 0) )
        return 0

    def get_bed_temp(self):
        data = self.s.get('http://' + self.host + ':5000/api/printer/bed').content.decode('utf-8').split('\n')
        for line in data:
            if 'target' in line:
                return int(float(line[line.find(':')+1:]))
        return 0
