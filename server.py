
import socket
from threading import Thread

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
BUFFERSIZE = 1024


def handleUDPClient(bytesAddressPair, s):
    msgFromServer = "Hello UDP Client"
    bytesToSend = str.encode(msgFromServer)

    message = bytesAddressPair[0]
    address = bytesAddressPair[1]
    clientMsg = "Message from Client:{}".format(message)
    clientIP = "Client IP Address:{}".format(address)
    print(clientMsg)
    print(clientIP)
    s.sendto(bytesToSend, address)


def listenUDP(host, port, bufferSize):
    threadsUDP = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, port))
        print("bind")
        while(True):
            print("listening UDP")
            bytesAddressPair = s.recvfrom(bufferSize)
            print("Received UDP message")
            t = Thread(target=handleUDPClient, args=(bytesAddressPair, s,))
            threadsUDP.append(t)
            t.start()


def listenTCP(host, port):
    threadsTCP = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            t = Thread(target=handleTCPClient, args=(conn, addr,))
            threadsTCP.append(t)
            t.start()


def handleTCPClient(conn, addr):
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            conn.sendall(data)


tcpT = Thread(target=listenTCP, args=(HOST, PORT,))
tcpT.start()
udpT = Thread(target=listenUDP, args=(HOST, PORT, BUFFERSIZE,))
udpT.start()
