import select
import socket
import sys

from psycopg2 import connect

bufferSize = 1024
HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 8000  # The port used by the server


def callOpponent(data, server):
    data = data.decode("ASCII").split(" ")
    host = data[0]
    port = int(data[1])
    print(f"HOST / PORT = {host} / {port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as opponent:
        opponent.connect((host, port))
        opponent.sendall(b"call")


def packNew(user, password):
    command = "newU"
    usernameLen = len(user)
    message = f"{command}{usernameLen:03d}{user}{password}"
    return message


def packPass(old, new):
    command = "pass"
    oldLen = len(old)
    message = f"{command}{oldLen:03d}{old}{new}"
    return message


def packIn(user, password):
    command = "in__"
    usernameLen = len(user)
    message = f"{command}{usernameLen:03d}{user}{password}"
    return message


def packList():
    return "list"


def packHall():
    return "hall"


def packOut():
    return "out_"


def packCall(opponent):
    command = "call"
    opponentLen = len(opponent)
    message = f"{command}{opponentLen:03d}{opponent}"
    return message


def runUDP(serverAddressPort):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        while True:
            comm = input("JogoDaVelha>").split()
            if comm:
                if comm[0] == "bye":
                    break
                elif comm[0] == "new":
                    if len(comm) != 3:
                        print("uso: new <usuario> <senha>")
                    else:
                        message = packNew(comm[1], comm[2])
                        s.sendto(bytes(message, encoding="ASCII"),
                                 serverAddressPort)
                elif comm[0] == "in":
                    if len(comm) != 3:
                        print("uso: in <usuario> <senha>")
                    else:
                        message = packIn(comm[1], comm[2])
                        s.sendto(bytes(message, encoding="ASCII"),
                                 serverAddressPort)
                elif comm[0] == "list":
                    message = packList()
                    s.sendto(bytes(message, encoding="ASCII"),
                             serverAddressPort)
                    message = s.recv(1024)
                    print(message)
                elif comm[0] == "hall":
                    message = packHall()
                    s.sendto(bytes(message, encoding="ASCII"),
                             serverAddressPort)
                    message = s.recvfrom(1024)[0]
                    print(message.decode('utf-8'))
                elif comm[0] == "out":
                    message = packOut()
                    s.sendto(bytes(message, encoding="ASCII"),
                             serverAddressPort)
                elif comm[0] == "pass":
                    if len(comm) != 3:
                        print("uso: pass <senha> <nova_senha>")
                    else:
                        message = packPass(comm[1], comm[2])
                        s.sendto(bytes(message, encoding="ASCII"),
                                 serverAddressPort)
                elif comm[0] == "bye":
                    break
                elif comm[0] == "call":
                    if len(comm) != 2:
                        print("uso: call <oponent>")
                    else:
                        message = packCall(comm[1])
                        s.sendto(bytes(message, encoding="ASCII"),
                                 serverAddressPort)
                        message = s.recv(1024)
                        print(message)
                        callOpponent(message, s)


def runTCP(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        inputs = [s, sys.stdin]
        running = 1
        print("JogoDaVelha >", end="")
        sys.stdout.flush()
        while running:
            #print("JogoDaVelha >", end="")
            # comm = input("JogoDaVelha>").split()
            inputready, outputready, exceptready = select.select(
                inputs, [], [])

            for x in inputready:
                if x.fileno() == sys.stdin.fileno():
                    print("stdinReady")
                    comm = sys.stdin.readline().strip().split(" ")
                    print(f"::::{comm}::::")
                    if comm:
                        if comm[0] == "bye":
                            print("BYE")
                            running = 0
                        elif comm[0] == "new":
                            if len(comm) != 3:
                                print("uso: new <usuario> <senha>")
                            else:
                                message = packNew(comm[1], comm[2])
                                s.sendall(bytes(message, encoding="ASCII"))
                        elif comm[0] == "in":
                            if len(comm) != 3:
                                print("uso: in <usuario> <senha>")
                            else:
                                message = packIn(comm[1], comm[2])
                                s.sendall(bytes(message, encoding="ASCII"))
                        elif comm[0] == "list":
                            message = packList()
                            message = str.encode(message)
                            s.sendall(message)
                          #  message = s.recv(1024)
                           # print(message.decode('utf-8'))
                        elif comm[0] == "hall":
                            message = packHall()
                            s.sendall(bytes(message, encoding="ASCII"))
                            message = s.recv(1024)
                            print(message.decode('utf-8'))
                        elif comm[0] == "out":
                            message = packOut()
                            s.sendall(bytes(message, encoding="ASCII"))
                        elif comm[0] == "pass":
                            if len(comm) != 3:
                                print("uso: pass <senha> <nova_senha>")
                            else:
                                message = packPass(comm[1], comm[2])
                                s.sendall(bytes(message, encoding="ASCII"))
                        elif comm[0] == "bye":
                            running = 0
                        elif comm[0] == "call":
                            if len(comm) != 2:
                                print("uso: call <oponent>")
                            else:
                                message = packCall(comm[1])
                                s.sendall(bytes(message, encoding="ASCII"))
                                message = s.recv(1024)
                                call_opponent(message)
                                print(message)
                        else:
                            print(f"Comando não reconhecido:{comm}.")
                elif x.fileno() == s.fileno():
                    message = s.recv(1024)
                    print(message.decode('ASCII'))


if len(sys.argv) == 4:
    host = sys.argv[1]
    port = (int)(sys.argv[2])
    method = sys.argv[3]

else:
    host = "127.0.0.1"
    port = PORT
    method = "tcp"
serverAddressPort = (host, port)

if method == "udp":
    runUDP(serverAddressPort)
elif method == "tcp":
    runTCP(host, port)
