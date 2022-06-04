from email import message
import select
import socket
import sys
from click import command

from psycopg2 import connect
from requests import request

bufferSize = 1024
HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 8000  # The port used by the server


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


def callOpponent(data, server, addr, connType):
    data = data.decode("ASCII").split(" ")
    host = data[0]
    port = int(data[1])
    print(f"HOST / PORT = {host} / {port}")
    opponent = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    opponent.connect((host, port+1))
    sendMessage(b"call", opponent, addr, "tcp")
    return opponent


def packNew(user, password):
    command = "newU"
    usernameLen = len(user)
    message = f"{command}{usernameLen:03d}{user}{password}"
    return message


def packGame(usr, opp):
    command = "game"
    usrLen = len(usr)
    message = f"{command}{usrLen:03d}{usr}{opp}"
    return message


def packPlay(x, y):
    message = f"play{x}{y}"
    return message


def packTable(state):
    table = state.tableToStr()
    message = f"tabl{table}"
    return message


def packTACK():
    return "tack"


def packPass(old, new, login):
    command = "pass"
    oldLen = len(old)
    newLen = len(new)
    message = f"{command}{oldLen:03d}{old}{newLen:03d}{new}{login.name}"
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


def packOut(login):
    usrLen = len(login.name)
    return f"out_{usrLen:03d}{login.name}{login.password}"


def packCall(opponent, login):
    command = "call"
    opponentLen = len(opponent)
    nameLen = len(login.name)
    message = f"{command}{opponentLen:03d}{opponent}{nameLen}{login.name}{login.password}"
    return message


class Login():
    def __init__(self) -> None:
        self.name = None
        self.opponent = None
        self.password = None
        self.state = 0
        self.game = 0
        self.marker = ""
        self.table = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.request = 0

    def login(self, name, password):
        self.name = name
        self.password = password
        self.state = 1

    def logout(self):
        self.name = None
        self.password = None
        self.state = 0
        self.game = 0

    def startgame(self, marker):
        self.game = 1
        self.waiting = 0
        if marker == "O":
            self.waiting = 1
        self.marker = marker

    def endgame(self):
        self.game = 0
        self.waiting = 0
        self.marker = "-"
        self.table = [0, 0, 0, 0, 0, 0, 0, 0, 0]

    def play(self, y, x, opponent):
        print("Play start. Table:", self.table)
        print("my marker: ", self.marker)
        marker = 1
        if self.marker == "O":
            marker = -1
        if opponent:
            marker *= -1
        self.table[3*y+x] = marker
        print("Play End. Table:", self.table)

    def tableToStr(self):
        message = ""
        for i in self.table:
            if i == 0:
                message += "-"
            if i == 1:
                message += "X"
            if i == -1:
                message += "O"
        return message

    # Soma as casas do tabuleiro (-1 para "0", 1 para "X", 0 para vazio) em
    # cada uma das possíveis direções de vitória. Se alguma somar 3 ou -3 houve
    # vitória. Adicionamente, determina empate se não houver casas vazias.
    def checkEnd(self):
        direction = [0, 0, 0, 0, 0, 0, 0, 0]
        for i in range(3):
            # linhas
            direction[0] += self.table[i]
            direction[1] += self.table[i+3]
            direction[2] += self.table[i+6]
            # colunas
            direction[3] += self.table[3*i]
            direction[4] += self.table[3*i + 1]
            # diagonais
            direction[5] += self.table[3*i + 2]
            direction[6] += self.table[3*i + i]
            direction[5] += self.table[3*i + (2 - i)]
        print(direction)
        for d in direction:
            if abs(d) == 3:
                if d == 3:
                    return 1
                else:
                    return -1
        draw = 9
        for i in range(9):
            if self.table[i] == 0:
                draw -= 1
        if draw == 0:
            return 0
        return None


def processOpponent(opponent, login: Login, inputs: list, s, addr: tuple, connType):
    message = opponent.recv(1024)
    if not message:
        inputs.remove(opponent)
        opponent.close()
        opponent = None
        print("Opponent closed connection.")
        login.endgame()
    else:
        # message = message.decode('ASCII')
        print("RECIEVED: ", message.decode('ASCII'))
        if message == b"call":
            if login.state == 1:
                print(
                    "NEW PLAY REQUEST. TYPE yes TO ACCEPT OR OTHER TO REFUSE.")
                print("JogoDaVelha >", end="")
                login.request = 1
            else:
                pass
        elif message == b"callACK":
            if login.state == 1:
                message = packGame(login.name, login.opponent)
                sendMessage(bytes(message, encoding="ASCII"),
                            s, addr, connType)
            else:
                print(
                    "You need to execute login. Use in <usr> <pass>.")
        elif message[0:4] == b"play":
            message = message.decode("ASCII")
            print("message:", message)
            x = int(message[4])
            y = int(message[5])
            print("x / y: ", x, " / ", y)
            login.play(x, y, True)
            sendMessage(b"pACK", opponent, addr, "tcp")

        elif message[0:4] == b"tabl":
            message = message.decode("ASCII")
            print(message[4:7])
            print(message[7:10])
            print(message[10:13])
            # jogo não terminou
            if len(message) == 13:
                login.waiting = 0
            # jogo terminou. resultado na posição 20 da mensagem.
            else:
                winner = message[20]
                if winner == "D":
                    result = 0
                elif winner == "X":
                    result = 1
                elif winner == "O":
                    result = -1
                else:
                    print("FAILED TO PARSE RESULT")
                printResult(result, login)
                login.endgame()
            message = packTACK()
            sendMessage(bytes(message, encoding="ASCII"),
                        opponent, addr, "tcp")

        elif message[0:4] == b"tACK":
            pass
        elif message[0:4] == b"pACK":
            message = packTable(login)
            result = login.checkEnd()
            if result:
                message += packEnd(result)
                sendMessage(bytes(message, encoding="ASCII"),
                            opponent, addr, "tcp")
                message = packResult(result, login)
                sendMessage(bytes(message, encoding="ASCII"),
                            s, addr, connType)
                printResult(result, login)
                login.endgame()
            else:
                sendMessage(bytes(message, encoding="ASCII"),
                            opponent, addr, "tcp")


def printResult(result, login):
    winner = "X"
    if result == -1:
        winner = "O"
    if result == 0:
        winner = "D"
    usr = login.name
    opp = login.opponent
    print("Winner and marker: ", winner, login.marker)
    if winner == login.marker:
        print("You Won!!")
    elif winner == "D":
        print("Draw.")
    else:
        print("You Lose.")


def packResult(result: int, login: Login):
    winner = "X"
    if result == -1:
        winner = "O"
    if result == 0:
        winner = "D"
    usr = login.name
    opp = login.opponent
    if winner == login.marker:
        res = "V"
    elif winner == "D":
        res = "E"
    else:
        res = "D"
    message = f"endG{res}{len(usr):03d}{usr}{opp}"
    return message


def packEnd(result):
    winner = "X"
    if result == -1:
        winner = "O"
    if result == 0:
        winner = "D"
    print("Pack end Winner:", winner)
    return f"endGame{winner}"


def runClient(addr, s, connType):
    name = s.getsockname()
    myHost = name[0]
    myPort = name[1]
    print(f"my Host: {myHost} my Port: {myPort}")

    listenConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listenConn.bind((myHost, myPort+1))
    listenConn.listen()
    inputs = [s, sys.stdin, listenConn]
    opponent = None
    running = 1
    login = Login()
    print("JogoDaVelha >", end="")
    sys.stdout.flush()
    while running:
        inputready, outputready, exceptready = select.select(
            inputs, [], [])
        for x in inputready:
            if x.fileno() == sys.stdin.fileno():
                comm = sys.stdin.readline().strip().split(" ")
                if login.request == 1:
                    if comm[0] == "yes":
                        print("ACCEPTED CALL")
                        sendMessage(b"callACK", opponent, addr, "tcp")
                        comm = None
                    else:
                        login.request == 0
                if comm:
                    if (login.game == 0):
                        if comm[0] == "new":
                            if len(comm) != 3:
                                print("uso: new <usuario> <senha>")
                            else:
                                message = packNew(comm[1], comm[2])
                                sendMessage(
                                    bytes(message, encoding="ASCII"), s, addr, connType)
                        elif comm[0] == "in":
                            if len(comm) != 3:
                                print("uso: in <usuario> <senha>")
                            else:
                                # alterar para inAck
                                login.login(comm[1], comm[2])
                                message = packIn(comm[1], comm[2])
                                sendMessage(
                                    bytes(message, encoding="ASCII"), s, addr, connType)
                        elif comm[0] == "list":
                            message = packList()
                            message = str.encode(message)
                            sendMessage(message, s, addr, connType)
                        #  message = s.recv(1024)
                        # print(message.decode('utf-8'))
                        elif comm[0] == "hall":
                            message = packHall()
                            sendMessage(
                                bytes(message, encoding="ASCII"), s, addr, connType)
                            # message = s.recv(1024)

                        elif comm[0] == "out":
                            if login.state == 1:
                                login.logout
                                message = packOut(login)
                                sendMessage(
                                    bytes(message, encoding="ASCII"), s, addr, connType)
                            else:
                                print(
                                    "You need to execute login. Use in <usr> <pass>.")
                        elif comm[0] == "pass":
                            if len(comm) != 3:
                                print("uso: pass <senha> <nova_senha>")
                            else:
                                if login.state == 1:
                                    message = packPass(
                                        comm[1], comm[2], login)
                                    login.password = comm[2]
                                    sendMessage(
                                        bytes(message, encoding="ASCII"), s, addr, connType)
                                else:
                                    print(
                                        "You need to execute login. Use in <usr> <pass>.")
                        elif comm[0] == "bye":
                            running = 0
                        elif comm[0] == "call":
                            if login.state == 1:
                                if len(comm) != 2:
                                    print("uso: call <oponent>")
                                else:
                                    message = packCall(comm[1], login)
                                    sendMessage(
                                        bytes(message, encoding="ASCII"), s, addr, connType)
                                    message = s.recv(1024)
                                    opponent = callOpponent(
                                        message, s, addr, connType)
                                    login.opponent = comm[1]
                                    inputs.append(opponent)
                                    print(message)
                            else:
                                print(
                                    "You need to execute login. Use in <usr> <pass>.")
                        else:
                            print(f"Comando não reconhecido:{comm}.")
                    # commando a serem executados durante uma partida
                    else:
                        if login.waiting == 0:
                            if comm[0] == "play":
                                print("DEBUG play")
                                if len(comm) != 3:
                                    print("Uso: play <linha> <coluna>")
                                else:
                                    message = packPlay(comm[1], comm[2])
                                    login.play(
                                        int(comm[1]), int(comm[2]), False)
                                    sendMessage(
                                        bytes(message, encoding="ASCII"), opponent, addr, "tcp")

                                    login.waiting = 1
                            if comm[0] == "over":
                                if login.marker == "X":
                                    result = -1
                                else:
                                    result = 1
                                message = packTable(login)
                                message += packEnd(result)
                                sendMessage(
                                    bytes(message, encoding="ASCII"), opponent, addr, "tcp")
                                message = packResult(result, login)
                                sendMessage(
                                    bytes(message, encoding="ASCII"), s, addr, connType)
                                printResult(result, login)
                                login.endgame()

                    print("JogoDaVelha >", end="")
                    sys.stdout.flush()

            # Trata de leituras no socket que conecta com o servidor.
            elif x.fileno() == s.fileno():
                processServer(login, s, addr, connType)

            # Trata de leituras no socket que escuta requesições de partidas.
            elif x.fileno() == listenConn.fileno():
                opponent, addr = listenConn.accept()
                inputs.append(opponent)

            elif (opponent and x.fileno() == opponent.fileno()):
                processOpponent(opponent, login, inputs, s, addr, connType)


def processServer(login, s, addr, connType):
    message = s.recv(1024)
    # print(message.decode('ASCII'))
    #print("JogoDaVelha >", end="")
    comm = message[0:4]
    if comm[0:4] == b"game":
        message = message.decode("ASCII")
        print(f"Starting Game. You are {message[4]}.")
        login.startgame(message[4])
    if comm[0:4] == b"HRTB":
        sendMessage(b"HACK", s, addr, connType)


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
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', 0))
    runClient(serverAddressPort, s, "udp")
elif method == "tcp":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    s.connect((host, port))
    runClient(serverAddressPort, s, "tcp")
