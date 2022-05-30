# echo-client.py

import sys
import socket

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server


def sendHello(host, port):

    s.sendall(b"Hello, world")
    data = s.recv(1024)
    print(f"Received {data!r}")


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


def packOut():
    return "out_"


if len(sys.argv) == 3:
    port = (int)(sys.argv[1])
    print(port)
    host = sys.argv[2]

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    while True:
        comm = input("JogoDaVelha>").split()
        if comm:
            if comm[0] == "bye":
                break
            elif comm[0] == "hello":
                sendHello(HOST, PORT)
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
                break
