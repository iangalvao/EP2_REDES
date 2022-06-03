from threading import Thread


def readAndWrite():
    m = input("digite aqui")
    print(m)


t1 = Thread(target=readAndWrite)
t1.start()

readAndWrite()
