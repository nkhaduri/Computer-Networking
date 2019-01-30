import argparse
import subprocess
import time
import signal
import os
from basicHttp import basicHttp
from virtualhost import virtualhost 
from keepalive import keepalive
from rangeheader import rangeheader
from parallelhttp import parallelhttp
from logTest import logTest

def main():
    parser = argparse.ArgumentParser(description='HTTP tests')
    parser.add_argument('http_server', help='Path to http server file.')
    parser.add_argument('config_file', help='Path to configuration file.')
    args = parser.parse_args()

    try:
        proc = subprocess.Popen(['python', args.http_server, args.config_file])
    except subprocess.CalledProcessError as err:        
        print("Could not start server: {}".format(err))

    print('server started successfully')    
    time.sleep(1)

    total_score = 0
    tests = [(basicHttp, 30), (virtualhost, 20), (parallelhttp, 20), 
            (keepalive, 15), (rangeheader, 15)]
    for test, scaler in tests:
        t = test(args.config_file)
        result = t.run() * scaler
        total_score += result

    print("---------------------\nTest for bonus")
    t = logTest(args.config_file)
    bonus = (t.run() == 1)
    
    print("---------------------\nTotal score is: {}".format(total_score))
    if bonus:
        print("You got bonus +5% on midterm!") 
    else:
        print("No bonus, try harder!") 

    # stop service 
    os.kill(proc.pid, signal.SIGUSR1)

if __name__ == '__main__':
    main()