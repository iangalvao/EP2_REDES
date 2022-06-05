import time
import select
import sys
import socket
from threading import Thread, Lock

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
BUFFERSIZE = 1024


def handleNew(data, users, connectedUsers, usersFile, mux):
    unameLen = int(data[4:7])
    username = data[7:7+unameLen].decode('utf-8')
    password = data[7+unameLen:].decode('utf-8')
    users[username] = [password, 0, 0, 0]
    print(usersFile.name)
    # mutex
    usersFile.write(f"{username} {password}\n")
    usersFile.flush()
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


def handleEndGame(data, users, connectedUsers, s, address, connType, pointsFile, logFile, mux):
    player1, player2, result = unpackEndGame(data)
    if result == 1:
        users[player1][1] += 1
        pointsFile.write(f"{player1}\n")
        winner = player1
    elif result == 0:
        users[player1][2] += 1
        users[player2][2] += 1
        pointsFile.write(f"{player1} {player2}\n")
        winner = ""
    elif result == -1:
        users[player2][1] += 1
        pointsFile.write(f"{player2}\n")
        winner = player2
    pointsFile.flush()
    connectedUsers[player1]["status"] = "Connected"
    connectedUsers[player2]["status"] = "Connected"
    p1addr = connectedUsers[player1]["addr"]
    p2addr = connectedUsers[player2]["addr"]
    # mutex
    logFile.write(f"MATCHEND {p1addr} {player1} {p2addr} {player2} {winner}\n")
    logFile.flush()
    # persist


def handleGame(data, connectedUsers, s, address, connType, logFile, mux):
    unameLen = int(data[4:7])
    player1 = data[7:7+unameLen].decode('ASCII')
    player2 = data[7+unameLen:].decode('ASCII')
    print("player1:", player1)
    print("player2:", player2)
    p1conn = connectedUsers[player1]["conn"][0]
    p1connType = connectedUsers[player1]["conn"][1]
    p1addr = connectedUsers[player1]["addr"]

    p2conn = connectedUsers[player2]["conn"][0]
    p2connType = connectedUsers[player2]["conn"][1]
    p2addr = connectedUsers[player2]["addr"]
    connectedUsers[player1]["status"] = "Playing"
    connectedUsers[player2]["status"] = "Playing"
    sendMessage(f"gameX{player2}", p1conn, p1addr, p1connType)
    # Só funciona se os dois usarem o mesmo tipo de conexão
    sendMessage(f"gameO{player1}", p2conn, p2addr, p2connType)
    # persist log
    # mutex
    logFile.write(f"MATCHSTART {p1addr} {player1} {p2addr} {player2}\n")
    logFile.flush()


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


def handlePass(data, users, connectedUsers, addr, usersFile, mux):
    oldPass, newPass, username = unpackPass(data)

    if username not in connectedUsers.keys():
        print("User not connected")
        return
    if oldPass == users[username][0]:
        users[username][0] = newPass
        # mutex
        mux.acquire()
        usersFile.write(f"{username} {newPass}\n")
        usersFile.flush()
        mux.release()
    else:
        print(
            f"Password Change Attempt Failed. User:{username}, password:{oldPass}")
    # persist
    # send(newACK)


def handleLogin(data, users, connectedUsers, addr, s, connType, logFile, mux):
    data = data.decode("ASCII")
    unameLen = int(data[4:7])
    username = data[7:7+unameLen]
    passLen = int(data[7+unameLen:7+unameLen+3])
    password = data[7+unameLen+3:7+unameLen+3+passLen]
    playPort = int(data[7+unameLen+3+passLen:])
    print(
        f"LOGIN username length:{unameLen}\nusername:{username}\npassword:{password}")
    if not (username in users.keys()):
        print(f"Login Attempt Failed. User = {username}, pass: {password}")
        return
    if users[username][0] == password:
        print(f"user {username}: connected.")
        connectedUsers[username] = {"addr": addr, "conn": (
            s, connType), "status": "Connected", "port": playPort}
        # send(loginACK)
        # persist log
        # mutex
        logFile.write(f"LOGIN {addr} {username}\n")
        logFile.flush()
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


def handleLogout(data, users, connectedUsers, s, addr, logFile, mux):
    username, password = unpackLogout(data)
    print(f"login out usr:{username}, pass: {password}")
    if username in connectedUsers.keys():
        if users[username][0] == password:
            connectedUsers.pop(username)
            # persist log
            # mutex
            mux.acquire()
            logFile.write(f"LOGOUT {addr} {username}\n")
            logFile.flush()
            mux.release()
    else:
        print("Failed logout attemp.")
    # send(logoutACK)
    print(connectedUsers)


def handleList(data, connectedUsers, s, address, connType):
    message = createList(data, connectedUsers)
    if not message:
        message = "There are no users connected."
    sendMessage(message, s, address, connType)


def handleCall(data, connectedUsers, s, address, connType):
    unameLen = int(data[4:7])
    username = data[7:7+unameLen].decode('ASCII')
    message = ""

    port = connectedUsers[username]["port"]
    addr = (address[0], port)
    print("CALL address:", addr)
    if addr:
        message = packAddress(addr)
        sendMessage(message, s, address, connType)
    else:
        sendMessage("NACK", s, address, connType)


def packAddress(addr):
    print(addr)
    message = ""
    message += addr[0]
    message += " "
    message += f"{addr[1]}"
    print(message)
    message = message
    return message


def handleHoF(data, users, s, addr, connType):
    message = createHoF(data, users)
    if not message:
        message = "There are no users in the system."
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
    message += "\n"
    message = bytes(message, encoding="ASCII")
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
        message += attrs["status"]
        message += '\n'
    return message


class ClientState():
    def __init__(self) -> None:
        self.lasthearbeat = time.time()
        self.conn = 0
        self.lasthbACK = time.time()
        self.sendhb = 1


def handleUDPClient(bytesAddressPair, s, udpUsers, user, connectedUsers,  recovery):
    data = bytesAddressPair[0]
    address = bytesAddressPair[1]

    if address in udpUsers.keys():
        cS = udpUsers[address]
    else:
        cS = ClientState()
        udpUsers[address] = cS
        # persist log
        # mutex
        mux = recovery["mux"]
        mux.acquire()
        recovery["log"].write(f"CONN {address} UDP\n")
        recovery["log"].flush()
        mux.release()
        print(f"Connected by {address} using UDP.")

    handleCommand(data, s, address, users, connectedUsers, "udp", cS, recovery)


def handleTCPClient(conn, addr, users, connectedUsers, recovery):
    print(f"Connected by {addr} using TCP")
    # mutex
    mux = recovery["mux"]
    mux.acquire()
    recovery["log"].write(f"CONN {addr} TCP\n")
    mux.release()
    # persist log
    running = 1

    inputs = [conn]
    cS = ClientState()
    while running:
        now = time.time()
        timediff = now - cS.lasthbACK
        if timediff >= 1:
            if cS.sendhb == 1:
                sendMessage("HRTB", conn, addr, "tcp")
                cS.lasthearbeat = time.time()
                cS.sendhb = 0
            else:
                if timediff > 30:
                    print("Disconecting Client. No heartbeat response.")
                    conn.close()
                    running = 0
                    break
        try:
            inputready, outputready, exceptready = select.select(
                inputs, [], [], 1)
        except select.error as e:
            print(e)
        for x in inputready:
            if x.fileno() == conn.fileno():
                data = recTCP(conn)
                if not data:
                    print(f"Client Disconnected: {addr}")
                    running = 0
                handleCommand(data, conn, addr, users,
                              connectedUsers, "tcp", cS, recovery)
# conn.sendall(data)


def handleCommand(stream, s, address, users, connectedUsers, connType, cS: ClientState, recovery):
    stream = stream.split(b"\n")
    stream.pop()
    for data in stream:
        comm = data[0:4]
        print(data)
        if comm == b"newU":
            handleNew(data, users, connectedUsers,
                      recovery["users"], recovery["mux"])
        elif comm == b"in__":
            handleLogin(data, users, connectedUsers, address,
                        s, connType, recovery["log"], recovery["mux"])
        elif comm == b"list":
            handleList(data, connectedUsers, s, address, connType)
        elif comm == b"hall":
            handleHoF(data, users, s, address, connType)
        elif comm == b"out_":
            print("starting logout")
            handleLogout(data, users, connectedUsers,
                         s, address, recovery["log"], recovery["mux"])
        elif comm == b"pass":
            handlePass(data, users, connectedUsers, address,
                       recovery["users"], recovery["mux"])
        elif comm == b"call":
            handleCall(data, connectedUsers, s, address, connType)
        elif comm == b"game":
            handleGame(data, connectedUsers, s, address,
                       connType, recovery["log"], recovery["mux"])
        elif comm == b"endG":
            handleEndGame(data, users, connectedUsers, s,
                          address, connType, recovery["points"], recovery["log"], recovery["mux"])
        elif comm == b"HACK":
            cS.lasthbACK = time.time()
            cS.sendhb = 1
        else:
            print(f"not a command: {comm}")


def sendHeartBeats(udpUsers, s):
    print("SENDHEARTBEATS")
    for addr, cS in udpUsers.items():
        now = time.time()
        timediff = now - cS.lasthbACK
        if timediff >= 1:
            if cS.sendhb == 1:
                sendMessage("HRTB", s, addr, "udp")
                cS.lasthearbeat = time.time()
                cS.sendhb = 0
            else:
                if timediff > 30:
                    print("Disconecting Client. No heartbeat response.")
                    # rmove from udpusers
                    running = 0
                    break


def listenUDP(host, port, bufferSize, users, connectedUsers, recovery):
    threadsUDP = []
    udpUsers = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", port))
        inputs = [s]
        while(True):
            try:
                inputready, outputready, exceptready = select.select(
                    inputs, [], [], 1)
            except select.error as e:
                print(e)
            sendHeartBeats(udpUsers, s)
            for x in inputready:
                if x.fileno() == s.fileno():
                    bytesAddressPair = s.recvfrom(bufferSize)
                    t = Thread(target=handleUDPClient, args=(
                        bytesAddressPair, s, udpUsers, users, connectedUsers, recovery))
                    threadsUDP.append(t)
                    t.start()


def listenTCP(host, port, users, connectedUsers, recovery):
    threadsTCP = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", port))
        s.listen()
        while True:
            conn, addr = s.accept()
            t = Thread(target=handleTCPClient, args=(
                conn, addr, users, connectedUsers, recovery))
            threadsTCP.append(t)
            t.start()


users = {}
connectedUsers = {}


def loadUsers(f):
    users = {}
    lines = f.read().split('\n')
    for line in lines:
        if line:
            data = line.split(" ")
            users[data[0]] = [data[1], 0, 0, 0]
    print(users)
    return users


def loadPoints(f, users):
    lines = f.read().split('\n')
    for line in lines:
        if line:
            data = line.split(" ")
            if len(data) == 1:
                user = data[0]
                if user in users.keys():
                    users[user][1] += 1
            elif len(data) == 2:
                user1 = data[0]
                user2 = data[1]
                if user1 in users.keys():
                    users[user1][2] += 1
                if user2 in users.keys():
                    users[user2][2] += 1
    print(users)
    return users


if len(sys.argv) == 2:
    port = (int)(sys.argv[1])
    print(port)
else:
    port = PORT

try:
    recovery = open("usersRecovery.txt", "r")
    users = loadUsers(recovery)
    recovery.close()
    print("USERS RECOVERY FILE FOUND. USERS CREDENTIALS RECOVERED.")
except FileNotFoundError:
    print("USERS RECOVERY FILE NOT FOUND. CREATING NEW USERS FILE.")

try:
    recovery = open("pointsRecovery.txt", "r")
    users = loadPoints(recovery, users)
    recovery.close()
    print("MATCHES HISTORY RECOVERY FILE FOUND. USERS POINTS RECOVERED.")
except FileNotFoundError:
    print("MATCHES HISTORY RECOVERY FILE NOT FOUND. CREATING NEW POINTS FILE.")

try:
    recovery = open("logFile.txt", "r")
    #users, connectedUsers = loadLog(recovery, users)
    recovery.close()
    print("LOG RECOVERY FILE FOUND. CONNECTIONS AND MATCHES RECOVERED.")
except FileNotFoundError:
    print("LOG RECOVERY FILE NOT FOUND. CREATING CONNECTIONS AND MATCHES FILE.")


mutex = Lock()
usersRecovery = open("usersRecovery.txt", "a")
pointRecovery = open("pointsRecovery.txt", "a")
logFile = open("logFile.txt", "a")
recovery = {"users": usersRecovery,
            "points": pointRecovery, "log": logFile, "mux": mutex}
tcpT = Thread(target=listenTCP, args=(
    HOST, port, users, connectedUsers, recovery,))
tcpT.start()
udpT = Thread(target=listenUDP, args=(
    HOST, port, BUFFERSIZE, users, connectedUsers, recovery,))
udpT.start()
