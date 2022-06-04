import select
import socket
import sys

from psycopg2 import connect
from requests import request

bufferSize = 1024
HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 8000  # The port used by the server


def callOpponent(data, server):
    data = data.decode("ASCII").split(" ")
    host = data[0]
    port = int(data[1])
    print(f"HOST / PORT = {host} / {port}")
    opponent = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    opponent.connect((host, port+1))
    opponent.sendall(b"call")
    return opponent


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


class Login():
    def __init__(self) -> None:
        self.name = None
        self.password = None
        self.state = 0

    def login(self, name, password):
        self.name = name
        self.password = password
        self.state = 1

    def logout(self):
        self.name = None
        self.password = None
        self.state = 0


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
                        opponent = socket.socket(
                            socket.AF_INET, socket.SOCK_STREAM)
                        # inputs.append(opponent)
                        callOpponent(message, s)


def runTCP(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        s.connect((host, port))
        name = s.getsockname()
        myHost = name[0]
        myPort = name[1]
        listenConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listenConn.bind((myHost, myPort+1))
        listenConn.listen()
        print(f"my Host: {myHost} my Port: {myPort}")
        inputs = [s, sys.stdin, listenConn]
        opponent = None
        running = 1
        request = 0
        login = Login()
        print("JogoDaVelha >", end="")
        sys.stdout.flush()
        while running:
            #print("JogoDaVelha >", end="")
            # comm = input("JogoDaVelha>").split()
            inputready, outputready, exceptready = select.select(
                inputs, [], [])

            for x in inputready:
                if x.fileno() == sys.stdin.fileno():

                    comm = sys.stdin.readline().strip().split(" ")
                    if request == 1:
                        if comm[0] == "yes":
                            print("ACCEPTED CALL")
                            opponent.sendall("callACK")
                            comm = None
                        else:
                            request == 0
                    if comm:
                        if comm[0] == "new":
                            if len(comm) != 3:
                                print("uso: new <usuario> <senha>")
                            else:
                                message = packNew(comm[1], comm[2])
                                s.sendall(bytes(message, encoding="ASCII"))
                        elif comm[0] == "in":
                            if len(comm) != 3:
                                print("uso: in <usuario> <senha>")
                            else:
                                # alterar para inAck
                                login.login(comm[1], comm[2])
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
                            #message = s.recv(1024)
                            print(message.decode('utf-8'))
                        elif comm[0] == "out":
                            if login.state == 1:
                                login.logout
                                message = packOut()
                                s.sendall(bytes(message, encoding="ASCII"))
                            else:
                                print("You execute login. Use in <usr> <pass>.")
                        elif comm[0] == "pass":
                            if len(comm) != 3:
                                print("uso: pass <senha> <nova_senha>")
                            else:
                                if login.state == 1:
                                    message = packPass(comm[1], comm[2])
                                    s.sendall(bytes(message, encoding="ASCII"))
                                else:
                                    print(
                                        "You execute login. Use in <usr> <pass>.")
                        elif comm[0] == "bye":
                            running = 0
                        elif comm[0] == "call":
                            if login.state == 1:
                                if len(comm) != 2:
                                    print("uso: call <oponent>")
                                else:
                                    message = packCall(comm[1])
                                    s.sendall(bytes(message, encoding="ASCII"))
                                    message = s.recv(1024)
                                    opponent = callOpponent(message, s)
                                    inputs.append(opponent)
                                    print(message)
                            else:
                                print("You execute login. Use in <usr> <pass>.")
                        else:
                            print(f"Comando não reconhecido:{comm}.")
                    print("JogoDaVelha >", end="")
                    sys.stdout.flush()
                elif x.fileno() == s.fileno():
                    message = s.recv(1024)
                    print(message.decode('ASCII'))
                elif x.fileno() == listenConn.fileno():
                    opponent, addr = listenConn.accept()
                    inputs.append(opponent)

                elif (opponent and x.fileno() == opponent.fileno()):
                    message = opponent.recv(1024)
                    if not message:
                        inputs.remove(opponent)
                        opponent.close()
                        opponent = None
                    else:
                        #message = message.decode('ASCII')
                        print("RECIEVED: ", message.decode('ASCII'))
                        if message == b"call":
                            if login.state == 1:
                                print(
                                    "NEW PLAY REQUEST. TYPE yes TO ACCEPT OR OTHER TO REFUSE.")
                                request = 1
                            else:
                                pass
                        elif message == b"callACK":
                            if login.state == 1:
                                s.sendall(b"GAME")
                            else:
                                print("You execute login. Use in <usr> <pass>.")


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
