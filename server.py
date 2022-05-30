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


def handlePass(data, users, connectedUsers):
    oldLen = int(data[4:7])
    oldPass = data[7:7+oldLen].decode('utf-8')
    newPass = data[7+oldLen:].decode('utf-8')
    username = connectedUsers[get_ident()]
    if oldPass == users[username][0]:
        users[username][0] = newPass
    else:
        print(
            f"Password Change Attempt Failed. User:{username}, password:{oldPass}")
    # send(newACK)


def handleLogin(data, users, connectedUsers):
    unameLen = int(data[4:7])
    username = data[7:7+unameLen].decode('utf-8')
    password = data[7+unameLen:].decode('utf-8')
    print(
        f"LOGIN username length:{unameLen}\nusername:{username}\npassword:{password}")
    if users[username][0] == password:
        print(f"user {username}: connected.")
        connectedUsers[get_ident()] = username
        # send(loginACK)
    else:
        # send(loginNACK)
        print(f"Login Attempt Failed. User = {username}, pass: {password}")
        pass


def handleLogout(connectedUsers, s):
    connectedUsers.pop(get_ident())
    # send(logoutACK)
    print(connectedUsers)


def handleList(data, connectedUsers, s):
    message = createList(data, connectedUsers)
    message = str.encode(message)
    if not message:
        message = b"There are no users connected."
    s.sendall(message)


def handleHoF(data, users, s):
    message = createHoF(data, users)
    message = str.encode(message)
    if not message:
        message = b"There are no users in the system."
    s.sendall(message)


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
        message += statusToStr(tnum)
        message += '\n'
    return message


def handleUDPClient(bytesAddressPair, s):
    msgFromServer = "Hello UDP Client"
    bytesToSend = str.encode(msgFromServer)

    message = bytesAddressPair[0]
    address = bytesAddressPair[1]
    print(f"Connected by {address} using UDP.")
    s.sendto(bytesToSend, address)


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
                handleList(data, connectedUsers, conn)
            elif comm == b"hall":
                handleHoF(data, users, conn)
            elif comm == b"out_":
                print("starting logout")
                handleLogout(connectedUsers, conn)
            elif comm == b"pass":
                handlePass(data, users, connectedUsers)
            else:
                print("not a command")
    # conn.sendall(data)


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


if len(sys.argv) == 2:
    port = (int)(sys.argv[1])
    print(port)
else:
    port = PORT
tcpT = Thread(target=listenTCP, args=(HOST, port, users,))
tcpT.start()
udpT = Thread(target=listenUDP, args=(HOST, port, BUFFERSIZE,))
udpT.start()
