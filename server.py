import sys
import socket
from threading import Thread

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
BUFFERSIZE = 1024


def handleNew(data, users, connectedUsers):
    unameLen = int(data[4:7])
    username = data[7:7+unameLen]
    password = data[7+unameLen:]
    print(
        f"username length:{unameLen}\nusername:{username}\npassword:{password}")
    users[username] = password
    print(users)


def handleLogin(data, users, connectedUsers):
    unameLen = int(data[4:7])
    username = data[7:7+unameLen]
    password = data[7+unameLen:]
    print(
        f"username length:{unameLen}\nusername:{username}\npassword:{password}")
    if users[username] == password:
        print(f"user {username}: connected.")
        connectedUsers[username] = 1
    else:
        pass


def handleList(data, connectedUsers):
    message = ""
    for user, status in connectedUsers.keys():
        message += f"{len(user):03d}"
        message += user
        message += statusToStr(status)
        pass


def handleHoF(data, users):
    pass


def handleUDPClient(bytesAddressPair, s):
    msgFromServer = "Hello UDP Client"
    bytesToSend = str.encode(msgFromServer)

    message = bytesAddressPair[0]
    address = bytesAddressPair[1]
    print(f"Connected by {address} using UDP.")
    s.sendto(bytesToSend, address)


def listenUDP(host, port, bufferSize):
    threadsUDP = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, port))
        while(True):
            bytesAddressPair = s.recvfrom(bufferSize)
            t = Thread(target=handleUDPClient, args=(bytesAddressPair, s,))
            threadsUDP.append(t)
            t.start()


def listenTCP(host, port, users):
    threadsTCP = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, port))
        s.listen()
        while True:
            conn, addr = s.accept()
            t = Thread(target=handleTCPClient, args=(conn, addr, users, ))
            threadsTCP.append(t)
            t.start()


users = {}
connectedUsers = {}


def handleTCPClient(conn, addr, users):
    with conn:
        print(f"Connected by {addr} using TCP")
        while True:
            data = conn.recv(1024)
            print(data)
            if not data:
                break
            comm = data[0:4]
            print(comm)
            if comm == b"newU":
                handleNew(data, users, connectedUsers)

            elif comm == b"in__":
                handleLogin(data, users, connectedUsers)

            elif comm == b"list":
                handleList(data, connectedUsers)

            elif comm == b"hall":
                handleHoF(data, users)

    # conn.sendall(data)


if len(sys.argv) == 2:
    port = (int)(sys.argv[1])
    print(port)
tcpT = Thread(target=listenTCP, args=(HOST, port, users,))
tcpT.start()
udpT = Thread(target=listenUDP, args=(HOST, port, BUFFERSIZE,))
udpT.start()
