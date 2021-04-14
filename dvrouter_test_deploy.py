import os
import getopt
import time
import sys
from socket import socket, AF_INET, SOCK_DGRAM, error as socket_error
from socket import gethostbyaddr, gethostname
import json
import collections

uni = "lw2944"
suffix = ".clic.cs.columbia.edu"

test_host = "localhost"


def get_city_from_hostname(hostname):
    # e.g. lw2944@berlin.clic.cs.columbia.edu
    prefix = hostname.split('.')[0]
    return prefix.split('@')[-1]


def translate_city_to_hostname_port(city: str, port=30000, mode="test") -> (str, int):
    """
    :param city: (str) in test mode, use the mapping below. if deploy mode
    this field will be ignored
    :param mode: test or deploy
    :param port: in test mode, this is trivial. Only provide it in deploy mode
    :return: translated host name
    """
    mapping = {
        "berlin": 8000,
        "rome"  : 8001,
        "vienna": 8002,
        "paris" : 8003,
    }

    if mode == "test":
        translate_host = gethostbyaddr(gethostname())[0]
        translate_port = mapping[city]
    else:
        translate_host = city + suffix
        translate_port = port
    return translate_host, translate_port


def translate_hostname_port_to_city(host: str, port: int = None, mode="test") -> str:
    """
    :param host: str, hostname
    :param port: int. only used for test mode
    :param mode: test or deploy
    :return: get the city name
    """
    mapping = {
        8000: "berlin",
        8001: "rome",
        8002: "vienna",
        8003: "paris",
    }
    translate_host = host
    if mode == "test":
        translate_city = mapping[port]
    else:
        translate_city = get_city_from_hostname(translate_host)
    return translate_city


class Node:
    # Build a UDP socket, store your arguments
    # Initialize your routing table, etc.
    # Port could be none. If it is, use 10000 + os.geteuid()
    # Cities is: ['rome:1', 'paris':7]
    def __init__(self, port, cities, mode="test"):
        # mode = 'test' or 'deploy'
        # test mode means running in localhost
        # deploy mode means running in CLIC
        print("Starting socket in *{}* mode......".format(mode))
        self.iter = 0  # register the iteration
        self.mode = mode
        self.host = gethostbyaddr(gethostname())[0]
        print(self.host)
        if port is None:
            self.port = 30000  # + os.geteuid()  # geteuid is effective uid
        else:
            self.port = port

        self.city = translate_hostname_port_to_city(self.host, port=self.port, mode=mode)

        if self.mode == "test":
            self.output_dir = "test"
        else:
            self.output_dir = "."  # print to the root dir

        filename = self.city + "_routing.txt"
        output_file = os.path.join(self.output_dir, filename)
        self.file = open(output_file, mode='w')

        # create socket
        try:
            self.socket = socket(AF_INET, SOCK_DGRAM)
            print("socket running in host {} and port {}...".format(self.host, self.port))
        except socket_error as msg:
            print('Failed to create socket. Error Code : ' + str(
                msg[0]) + ' Message ' + msg[1])
            sys.exit()

        try:
            if self.mode == 'test':
                self.socket.bind((self.host, self.port))
            else:
                # for deploy mode. maybe host name is not enough
                self.socket.bind(('0.0.0.0', self.port))
        except socket_error as msg:
            print(
                'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[
                    1])
            sys.exit()
        time.sleep(10)  # wait for all the port to get together
        print("Server socket created and bind to host {} and port {}!".format(
            self.host, self.port))

        self.table = {}
        self.destination = []  # unfold like (host, port)
        print("Iteration 0, parsing node....")
        self.parse_nodes(cities)
        print("Notify other nodes....")
        self.send_routing_table()

    # Dump current list of all nodes this router knows and
    # the weight of shortest path.
    # Please see berlin_routing.txt, paris_routing.txt
    # PLEASE USE <hostname>_routing.txt names.
    # For a sanity check, you can check the last line of your text file
    # with mine. If it matches, great!
    def dump_routing_table(self):
        # need to sort alphabetically
        arr = []
        for key in sorted(self.table.keys()):
            arr.append(key + " " + str(self.table[key]))
        line = '|'.join(arr)
        self.file.write(line)
        self.file.write("\n")

    def finish_writing(self):
        self.file.close()

    # Parse Arguments
    # Initialize list of neighbors and T = 0 of RIP Table
    # Only call this once
    # Cities is: ['rome:1', 'paris':7]
    def parse_nodes(self, cities):
        self.table[self.city] = 0

        for city in cities:
            # table initialization
            name, weight = city.split(':')
            if self.mode == "test":
                name = translate_hostname_port_to_city(self.host, int(name),
                                                       self.mode)
            # need to translate a layer just for test mode
            host, port = translate_city_to_hostname_port(name, self.port, self.mode)
            self.destination.append((host, port))
            self.table[name] = int(weight)
        print("destinations: ", self.destination)
        print("tables: ", self.table)

    # Send all neighbors your current routing table
    def send_routing_table(self):
        table = self.table
        table = json.dumps(table)
        for host, port in self.destination:
            self.socket.sendto(table.encode(), (host, port))

        print("At iteration {}, the routing table is {}".format(self.iter, self.table))
        self.dump_routing_table()
        self.iter += 1

    # Receive data from a neighbor of their routing table
    # Update our rating table as needed
    def inbound(self):
        payload, addr = self.socket.recvfrom(2048)
        print("receive from {} ...".format(addr))
        # if self.mode == 'test':
        #     incoming_port = str(addr[1])
        # else:
        #     incoming_port = get_city_from_hostname(addr[0])
        load_json = json.loads(payload.decode())
        updated = self.update_routing_table(load_json, gethostbyaddr(addr[0])[0], addr[1])
        return updated

    # Called from inbound. Update Routing Table given what neighbor told you
    # argument: routing is the unpacked JSON file of routing table from neighbor
    def update_routing_table(self, routing, host, port):
        city = translate_hostname_port_to_city(host, port, self.mode)
        print("host is ", host)
        print("port is ", port)
        print("city is ", city)
        updated = False
        dist_to_neighbor = self.table[city]

        for key, value in routing.items():
            new_dist = dist_to_neighbor + value
            if key in self.table.keys():
                # exist, take min
                print("{} exists before....".format(key))
                if self.table[key] > new_dist:
                    # need to update
                    print("{} needs to be updated from {} to {}....".format(key, self.table[key], new_dist))
                    updated = True
                    self.table[key] = new_dist
            else:
                # not exist, add this
                print("{} not exist before, add this...".format(key))
                updated = True
                self.table[key] = new_dist
        return updated  # indicate whether it is updated

    # Called from inbound. After getting routing table updates
    # run Bellman Ford to update Routing Table values
    def bellman_ford(self):
        raise NotImplementedError


def main():
    # Turns: ["-p" "8000", "berlin:1", "Vienna:1"] to ("-p", "8000"), ["berlin:1", "Vienna:1"]
    # If no -p passed you get
    # ["berlin:1", "Vienna:1"] to (-p, None), ["berlin:1", "Vienna:1"]
    options, cities = getopt.getopt(sys.argv[1:], "p:")
    print(options)
    print(cities)
    try:
        port = int(options[0][1])
    except IndexError:
        port = None
    except ValueError:
        port = None
    node = Node(port, cities, mode="test")

    while True:
        try:
            # I'll leave this to you to implement
            # Should be obvious which order of functions to call in what order

            # at T = 0, need to send first
            updated = node.inbound()  # wait for changes
            if updated:
                node.send_routing_table()

            # It should converge super-fast without the timer!
            # But feel free to use sleep()
            # both for troubleshooting, and minimize risk of overloading CLIC
            # Although Please Remove any sleep in final submission!

            time.sleep(5)
            # time.sleep(30)

        # Use CTRL-C to exit
        # You do NOT need to worry of updating routing table
        # if a node drops!
        # Show final routing table for checking if RIP worked
        except KeyboardInterrupt:
            node.file.close()
            break


if __name__ == '__main__':
    main()
