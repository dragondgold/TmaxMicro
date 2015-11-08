import requests
import sys

__author__ = 'Andres Torti'

if __name__ == '__main__':
    # Check if octoprint is available
    host = 'localhost'
    s = requests.Session()
    s.headers.update({'X-Api-Key': 'B0BE78429FCA477DA8399CE75928E093', 'Content-Type': 'application/json'})

    try:
        data = s.get('http://' + host + ':5000/api/version').content.decode('utf-8').split('\n')
        for line in data:
            if 'server' in line:
                import re
                p = re.compile('([0-9]\.[0-9]\.[0-9]\.dev?)')
                print(p.search(line).group())
                sys.exit()

        print('0.0.0')
    except:
        print('Couldn\'t connect to octoprint in ' + str(host))
