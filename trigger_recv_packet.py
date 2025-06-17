import contextlib
import socket

UNIQUE_STRING: str = "FINDME!"
TARGET_ADDR: tuple = ("127.0.0.1", 8080)

@contextlib.contextmanager
def setup_sock():
    sock = socket.socket()
    sock.connect(TARGET_ADDR)
    try:
        yield sock
    finally:
        sock.close()

def trigger_recv(sock: socket.socket):
    sock.send(UNIQUE_STRING.encode())
    recvd = sock.recv(1024)
    print(f"{recvd.decode()=}")

def main():
    with setup_sock() as sock:
        trigger_recv(sock)

if __name__ == "__main__":
    main()