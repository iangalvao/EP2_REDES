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


def unpackEndGame(data):
    message = data.decode("ASCII")
    result = message[4]
    if result == "V":
        res = 1
    elif result == "E":
        res = 0
    else:
        res = -1
    usrLen = int(message[5:8])
    player1 = message[8:8+usrLen]
    player2 = message[8+usrLen:]
    return (player1, player2, res)


def handleEndGame(data, users, connectedUsers, s, address, connType):
    player1, player2, result = unpackEndGame(data)
    if result == 1:
        users[player1][1] += 1
    elif result == 0:
        users[player1][2] += 1
        users[player2][2] += 1
    elif result == -1:
        users[player2][1] += 1
    connectedUsers[player1]["status"] = "Connected"
    connectedUsers[player2]["status"] = "Connected"


def handleGame(data, connectedUsers, s, address, connType):
    unameLen = int(data[4:7])
    player1 = data[7:7+unameLen].decode('ASCII')
    player2 = data[7+unameLen:].decode('ASCII')
    print("player1:", player1)
    print("player2:", player2)
    p1conn = connectedUsers[player1]["conn"][0]
    p1connType = connectedUsers[player1]["conn"][1]
    p2conn = connectedUsers[player2]["conn"][0]
    p2connType = connectedUsers[player2]["conn"][1]
    p1conn.sendall(b"gameX")
    p2conn.sendall(b"gameO")


def unpackPass(data):
    cursor = 7
    oldLen = int(data[4:7])
    oldPass = data[cursor:cursor+oldLen].decode('ASCII')
    cursor += oldLen
    newLen = int(data[cursor:cursor+3])
    cursor += 3
    newPass = data[cursor:cursor + newLen].decode('ASCII')
    cursor += newLen
    usr = data[cursor:].decode("ASCII")
    return (oldPass, newPass, usr)


def handlePass(data, users, connectedUsers, addr):
    oldPass, newPass, username = unpackPass(data)

    if username not in connectedUsers.keys():
        print("User not connected")
        return
    if oldPass == users[username][0]:
        users[username][0] = newPass
    else:
        print(
            f"Password Change Attempt Failed. User:{username}, password:{oldPass}")
    # send(newACK)


def handleLogin(data, users, connectedUsers, addr, s, connType):
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
        connectedUsers[username] = {"addr": addr, "conn": (s, connType)}
        # send(loginACK)
    else:
        # send(loginNACK)
        print(f"Login Attempt Failed. User = {username}, pass: {password}")
        pass


def unpackLogout(data):
    cursor = 7
    nameLen = int(data[4:7])
    name = data[cursor:cursor+nameLen].decode('ASCII')
    cursor += nameLen
    password = data[cursor:].decode("ASCII")
    return (name, password)


def handleLogout(data, users, connectedUsers, s, addr):
    username, password = unpackLogout(data)
    print(f"login out usr:{username}, pass: {password}")
    if username in connectedUsers.keys():
        if users[username][0] == password:
            connectedUsers.pop(username)
    else:
        print("Failed logout attemp.")
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
    addr = connectedUsers[username]["addr"]
    if addr:
        message = packAddress(addr)
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
    for user, attrs in connectedUsers.items():
        message += f"{len(user):03d}"
        message += user
        message += "Connected"
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
        handleLogin(data, users, connectedUsers, address, s, connType)
    elif comm == b"list":
        handleList(data, connectedUsers, s, address, connType)
    elif comm == b"hall":
        handleHoF(data, users, s, address, connType)
    elif comm == b"out_":
        print("starting logout")
        handleLogout(data, users, connectedUsers, s, address)
    elif comm == b"pass":
        handlePass(data, users, connectedUsers, address)
    elif comm == b"call":
        handleCall(data, connectedUsers, s, address, connType)
    elif comm == b"game":
        handleGame(data, connectedUsers, s, address, connType)
    elif comm == b"endG":
        handleEndGame(data, users, connectedUsers, s, address, connType)
    else:
        print(f"not a command: {comm}")


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
