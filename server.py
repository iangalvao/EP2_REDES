import sys
import socket
from threading import Thread, get_ident

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
BUFFERSIZE = 1024


def handleNew(data, users, connectedUsers):
    unameLen = int(data[4:7])
    username = data[7:7+unameLen].decode('utf-8')
    password = data[7+unameLen:].decode('utf-8')
    users[username] = [password, 0, 0, 0]
    # send(newACK)


def handlePass(data, users, connectedUsers, addr):
    oldLen = int(data[4:7])
    oldPass = data[7:7+oldLen].decode('utf-8')
    newPass = data[7+oldLen:].decode('utf-8')
    if addr in connectedUsers.keys():
        username = connectedUsers[addr]
    else:
        print("User not connected")
        return
    if oldPass == users[username][0]:
        users[username][0] = newPass
    else:
        print(
            f"Password Change Attempt Failed. User:{username}, password:{oldPass}")
    # send(newACK)


def handleLogin(data, users, connectedUsers, addr):
    unameLen = int(data[4:7])
    username = data[7:7+unameLen].decode('utf-8')
    password = data[7+unameLen:].decode('utf-8')
    print(
        f"LOGIN username length:{unameLen}\nusername:{username}\npassword:{password}")
    if not (username in users.keys()):
        print(f"Login Attempt Failed. User = {username}, pass: {password}")
        return
    if users[username][0] == password:
        print(f"user {username}: connected.")
        connectedUsers[addr] = username
        # send(loginACK)
    else:
        # send(loginNACK)
        print(f"Login Attempt Failed. User = {username}, pass: {password}")
        pass


def handleLogout(connectedUsers, s, addr):
    connectedUsers.pop(addr)
    # send(logoutACK)
    print(connectedUsers)


def handleList(data, connectedUsers, s, address, connType):
    message = createList(data, connectedUsers)
    message = str.encode(message)
    if not message:
        message = b"There are no users connected."
    sendMessage(message, s, address, connType)


def handleCall(data, connectedUsers, s, address, connType):
    unameLen = int(data[4:7])
    username = data[7:7+unameLen].decode('ASCII')
    message = ""
    for addr, usr in connectedUsers.items():
        if usr == username:
            message = addr
    if message != "":
        message = packAddress(message)
        sendMessage(message, s, address, connType)
    else:
        sendMessage(b"NACK", s, address, connType)


def packAddress(addr):
    print(addr)
    message = ""
    message += addr[0]
    message += " "
    message += f"{addr[1]}"
    print(message)
    message = bytes(message, encoding="ASCII")
    return message


def handleHoF(data, users, s, addr, connType):
    message = createHoF(data, users)
    message = str.encode(message)
    if not message:
        message = b"There are no users in the system."
    sendMessage(message, s, addr, connType)


def sendTCP(message, s):
    s.sendall(message)


def sendUDP(message, s, address):
    s.sendto(message, address)


def recTCP(conn):
    data = conn.recv(1024)
    return data


def recUDP(conn):
    bytesAddressPair = conn.recvfrom(1024)
    return bytesAddressPair


def recMessage(s, connType):
    if connType == "tcp":
        return recTCP(s)
    else:
        return recUDP(s)


def sendMessage(message, s, address, connType):
    if connType == "tcp":
        sendTCP(message, s)
    else:
        sendUDP(message, s, address)


def statusToStr(status):
    if status != 0:
        return "Connected"
    else:
        return "Disconnected"


def createHoF(data, users):
    message = "Users/Points\n"
    for user, value in users.items():
        message += user + "/"
        message += historyToStr(value)
        message += '\n'
    return message


def historyToStr(data):
    pontos = 3 * data[1] + data[2]
    return f"{pontos}"


def createList(data, connectedUsers):
    message = ""
    for tnum, user in connectedUsers.items():
        message += f"{len(user):03d}"
        message += user
        print("KEY = ", tnum)
        message += statusToStr(tnum)
        message += '\n'
    return message


def handleUDPClient(bytesAddressPair, s):

    data = bytesAddressPair[0]
    address = bytesAddressPair[1]

    print(f"Connected by {address} using UDP.")
    handleCommand(data, s, address, users, connectedUsers, "udp")


def handleTCPClient(conn, addr, users, connectedUsers):
    print(f"Connected by {addr} using TCP")
    while True:
        data = recTCP(conn)
        print(data)
        if not data:
            break
        handleCommand(data, conn, addr, users, connectedUsers, "tcp")
# conn.sendall(data)


def handleCommand(data, s, address, users, connectedUsers, connType):
    comm = data[0:4]
    print(comm)
    if comm == b"newU":
        handleNew(data, users, connectedUsers)
    elif comm == b"in__":
        handleLogin(data, users, connectedUsers, address)
    elif comm == b"list":
        handleList(data, connectedUsers, s, address, connType)
    elif comm == b"hall":
        handleHoF(data, users, s, address, connType)
    elif comm == b"out_":
        print("starting logout")
        handleLogout(connectedUsers, s, address)
    elif comm == b"pass":
        handlePass(data, users, connectedUsers, address)
    elif comm == b"call":
        handleCall(data, connectedUsers, s, address, connType)
    else:
        print("not a command")


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
            t = Thread(target=handleTCPClient, args=(
                conn, addr, users, connectedUsers))
            threadsTCP.append(t)
            t.start()


users = {}
connectedUsers = {}


if len(sys.argv) == 2:
    port = (int)(sys.argv[1])
    print(port)
else:
    port = PORT
tcpT = Thread(target=listenTCP, args=(HOST, port, users,))
tcpT.start()
udpT = Thread(target=listenUDP, args=(HOST, port, BUFFERSIZE,))
udpT.start()
