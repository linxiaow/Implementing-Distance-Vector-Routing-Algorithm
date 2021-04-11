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


class Node:
    # Build a UDP socket, store your arguments
    # Initialize your routing table, etc.
    # Port could be none. If it is, use 10000 + os.geteuid()
    # Cities is: ['rome:1', 'paris':7]
    def __init__(self, port, cities, mode="test"):
        # mode = 'test' or 'deploy'
        # test mode means running in localhost
        # deploy mode means running in CLIC
        print("Starting socket in {} mode......".format(mode))
        self.iter = 0  # register the iteration
        self.mode = mode
        self.host = gethostbyaddr(gethostname())[0]
        self.table = {}
        self.destination = []  # unfold like (host, port)
        # get destination hosts and destination ports
        if port is None:
            self.port = 30000 + os.geteuid()  # geteuid is effective uid
        else:
            self.port = port
        # create socket
        try:
            self.socket = socket(AF_INET, SOCK_DGRAM)
            print("socket running in host {} and port {}...".format(self.host, self.port))
        except socket_error as msg:
            print('Failed to create socket. Error Code : ' + str(
                msg[0]) + ' Message ' + msg[1])
            sys.exit()

        try:
            self.socket.bind((self.host, self.port))
        except socket_error as msg:
            print(
                'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[
                    1])
            sys.exit()
        print("Server socket created and bind to host {} and port {}!".format(
            self.host, self.port))

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
        raise NotImplementedError

    # Parse Arguments
    # Initialize list of neighbors and T = 0 of RIP Table
    # Only call this once
    # Cities is: ['rome:1', 'paris':7]
    def parse_nodes(self, cities):
        if self.mode == "deploy":
            for city in cities:
                name, _ = city.split(':')
                self.destination.append((uni + "@" + city + suffix, 30000))
            self.table[self.host] = 0
        else:
            # test mode
            # the hosts are always localhost
            # cities are given as ports
            for city in cities:
                name, _ = city.split(':')
                self.destination.append((self.host, name))
            self.table[str(self.port)] = 0

        for city in cities:
            # table initialization
            name, weight = city.split(':')
            self.table[name] = int(weight)
        print("destinations: ", self.destination)
        print("tables: ", self.table)

    # Send all neighbors your current routing table
    def send_routing_table(self):
        table = self.table.copy()
        if self.mode == "test":
            table["source"] = str(self.port)
        else:
            # deploy
            table["source"] = self.host
        table = json.dumps(table)
        for host, port in self.destination:
            self.socket.sendto(table.encode(), (host, int(port)))

        print("At iteration {}, the routing table is {}".format(self.iter, self.table))
        self.iter += 1

    # Receive data from a neighbor of their routing table
    # Update our rating table as needed
    def inbound(self):
        payload, addr = self.socket.recvfrom(2048)
        print("receive from {} ...".format(addr))
        load_json = json.loads(payload)
        updated = self.update_routing_table(load_json)
        return updated

    # Called from inbound. Update Routing Table given what neighbor told you
    # argument: routing is the unpacked JSON file of routing table from neighbor
    def update_routing_table(self, routing):
        city = routing["source"]
        updated = False
        dist_to_neighbor = self.table[city]
        for key, value in routing.items():
            if key == "source":
                continue

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
            time.sleep(30)

        # Use CTRL-C to exit
        # You do NOT need to worry of updating routing table
        # if a node drops!
        # Show final routing table for checking if RIP worked
        except KeyboardInterrupt:
            node.dump_routing_table()
            break


if __name__ == '__main__':
    main()
