import math
import multiprocessing as mp
import matplotlib.pyplot as plt

DATA_CONFIG = {
    'start': -10.0,
    'end': 10.0,
    'step': 0.1
}


def calculate_points_count() -> int:
    start = DATA_CONFIG['start']
    end = DATA_CONFIG['end']
    step = DATA_CONFIG['step']
    return int((end - start) / step) + 1


class SharedData:
    def __init__(self, n_points: int):
        self.x_data = mp.Array('d', n_points)
        self.y_data = mp.Array('d', n_points)
        self.x_ready = mp.Value('i', 0)
        self.y_ready = mp.Value('i', 0)
        self.n_points = n_points


def process1(shared: SharedData, sem: mp.Semaphore):
    try:
        x = DATA_CONFIG['start']
        for i in range(shared.n_points):
            shared.x_data[i] = x
            x = round(x + DATA_CONFIG['step'], 1)
        shared.x_ready.value = 1
    except Exception as e:
        print(f"Process1 error: {e}")
    finally:
        sem.release()


def process2(shared: SharedData, sem: mp.Semaphore):
    try:
        while shared.x_ready.value == 0:
            pass

        for i in range(shared.n_points):
            x = shared.x_data[i]
            shared.y_data[i] = math.sin(x)
        shared.y_ready.value = 1
    except Exception as e:
        print(f"Process2 error: {e}")
    finally:
        sem.release()


def process3(shared: SharedData, sem: mp.Semaphore):
    try:
        while shared.y_ready.value == 0:
            pass

        xs = [shared.x_data[i] for i in range(shared.n_points)]
        ys = [shared.y_data[i] for i in range(shared.n_points)]

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
        sem.release()


def main():
    n_points = calculate_points_count()
    shared = SharedData(n_points)
    sem = mp.Semaphore(0)

    processes = [
        mp.Process(target=process1, args=(shared, sem)),
        mp.Process(target=process2, args=(shared, sem)),
        mp.Process(target=process3, args=(shared, sem))
    ]

    for p in processes:
        p.start()

    for _ in range(3):
        sem.acquire()


if __name__ == "__main__":
    main()