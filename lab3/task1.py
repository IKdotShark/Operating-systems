import math
import os
import socket
import struct
import multiprocessing as mp
import matplotlib.pyplot as plt
from typing import List

SOCKET_PATHS = {
    'p1_to_p2': '/tmp/proc1_to_proc2.sock',
    'p2_to_p3': '/tmp/proc2_to_proc3.sock'
}

DATA_CONFIG = {
    'start': -10.0,
    'end': 10.0,
    'step': 0.1
}


def cleanup_sockets():
    for path in SOCKET_PATHS.values():
        if os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


def create_server_socket(path: str) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    if os.path.exists(path):
        os.unlink(path)
    sock.bind(path)
    sock.listen(1)
    return sock


def generate_x_values() -> List[float]:
    values = []
    x = DATA_CONFIG['start']
    while x <= DATA_CONFIG['end'] + 1e-9:
        values.append(x)
        x = round(x + DATA_CONFIG['step'], 1)
    return values


def process1(semaphore: mp.Semaphore):
    try:
        sock = create_server_socket(SOCKET_PATHS['p1_to_p2'])
        conn, _ = sock.accept()

        with conn:
            for x in generate_x_values():
                conn.sendall(struct.pack('d', x))

    except Exception as e:
        print(f"Process1 error: {e}")
    finally:
        sock.close()
        semaphore.release()


def process2(semaphore: mp.Semaphore):
    try:
        sock_in = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock_in.connect(SOCKET_PATHS['p1_to_p2'])

        sock_out = create_server_socket(SOCKET_PATHS['p2_to_p3'])
        conn_out, _ = sock_out.accept()

        with conn_out:
            while True:
                data = sock_in.recv(8)
                if not data:
                    break
                x = struct.unpack('d', data)[0]
                y = math.sin(x)
                conn_out.sendall(struct.pack('dd', x, y))

    except Exception as e:
        print(f"Process2 error: {e}")
    finally:
        sock_in.close()
        semaphore.release()


def process3(semaphore: mp.Semaphore):
    points = []
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATHS['p2_to_p3'])

        with sock:
            while True:
                data = sock.recv(16)
                if not data:
                    break
                x, y = struct.unpack('dd', data)
                points.append((x, y))

        if points:
            xs, ys = zip(*points)
            plt.figure(figsize=(10, 5))
            plt.plot(xs, ys, label='y = sin(x)')
            plt.title('График функции y = sin(x)')
            plt.xlabel('x')
            plt.ylabel('y')
            plt.grid(True)
            plt.legend()
            plt.show()

    except Exception as e:
        print(f"Process3 error: {e}")
    finally:
        semaphore.release()


def main():
    cleanup_sockets()

    sem = mp.Semaphore(0)
    processes = [
        mp.Process(target=process1, args=(sem,)),
        mp.Process(target=process2, args=(sem,)),
        mp.Process(target=process3, args=(sem,))
    ]

    for p in processes:
        p.start()

    for _ in range(3):
        sem.acquire()

    cleanup_sockets()


if __name__ == "__main__":
    main()