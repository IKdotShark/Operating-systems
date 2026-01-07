"""
Симулятор планировщика процессов с приоритетом кратких операций
Алгоритм: Shortest Job First (невытесняющий)
"""

import random
import math
from typing import List, Tuple

class Zadanije:
    """Класс, представляющий задачу в системе"""

    def __init__(self, identifikator: int, parametri: Tuple):
        self.id = identifikator
        self.srednee_cpu = parametri[0]
        self.otklonenie_cpu = parametri[1]
        self.srednee_io = parametri[2]
        self.otklonenie_io = parametri[3]

        # Статистика выполнения
        self.vremya_cpu = 0.0
        self.vremya_ozhidaniya = 0.0
        self.vremya_vvoda_vyvoda = 0.0
        self.zavershennye_cikly = 0

        # Текущее состояние
        self.vremya_gotovnosti = 0.0
        self.vremya_okonchaniya_io = None
        self.sledushij_interval_cpu = 0.0

    def poluchit_sluchajnoe_znachenie(self, srednee: float, otklonenie: float) -> float:
        """Генерация случайного значения по нормальному распределению"""
        # Используем метод Бокса-Мюллера для нормального распределения
        u1 = 1.0 - random.random()
        u2 = 1.0 - random.random()
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

        result = srednee + z * otklonenie
        return max(0.001, result)  # Гарантируем положительное значение

    def sgenerirovat_interval_cpu(self) -> float:
        """Сгенерировать время выполнения на процессоре"""
        self.sledushij_interval_cpu = self.poluchit_sluchajnoe_znachenie(
            self.srednee_cpu, self.otklonenie_cpu
        )
        return self.sledushij_interval_cpu

    def sgenerirovat_interval_io(self) -> float:
        """Сгенерировать время операции ввода-вывода"""
        return self.poluchit_sluchajnoe_znachenie(
            self.srednee_io, self.otklonenie_io
        )

class OcheredPrioritetov:
    """Очередь с приоритетом по времени выполнения"""

    def __init__(self):
        self._kucha = []
        self._schetchik = 0

    def dobavit_element(self, dlitelnost: float, id_zadachi: int):
        """Добавить элемент в очередь приоритетов"""
        # Используем кортеж (приоритет, порядок добавления, id)
        self._kucha.append((dlitelnost, self._schetchik, id_zadachi))
        self._schetchik += 1
        self._vospitat_kuchu_vverh(len(self._kucha) - 1)

    def izvlech_minimum(self) -> Tuple[float, int]:
        """Извлечь элемент с минимальным временем выполнения"""
        if not self._kucha:
            raise ValueError("Очередь пуста")

        # Первый элемент - минимальный
        minimum = self._kucha[0]

        # Перемещаем последний элемент в начало и восстанавливаем кучу
        poslednij = self._kucha.pop()
        if self._kucha:
            self._kucha[0] = poslednij
            self._prosest_kuchu_vniz(0)

        dlitelnost, _, id_zadachi = minimum
        return dlitelnost, id_zadachi

    def pusta(self) -> bool:
        """Проверить, пуста ли очередь"""
        return len(self._kucha) == 0

    def _vospitat_kuchu_vverh(self, indeks: int):
        """Восстановить свойство кучи снизу вверх"""
        while indeks > 0:
            roditel = (indeks - 1) // 2
            if self._kucha[indeks][0] < self._kucha[roditel][0]:
                self._kucha[indeks], self._kucha[roditel] = self._kucha[roditel], self._kucha[indeks]
                indeks = roditel
            else:
                break

    def _prosest_kuchu_vniz(self, indeks: int):
        """Восстановить свойство кучи сверху вниз"""
        razmer = len(self._kucha)
        while True:
            minimalnyj = indeks
            levyj = 2 * indeks + 1
            pravyj = 2 * indeks + 2

            if levyj < razmer and self._kucha[levyj][0] < self._kucha[minimalnyj][0]:
                minimalnyj = levyj
            if pravyj < razmer and self._kucha[pravyj][0] < self._kucha[minimalnyj][0]:
                minimalnyj = pravyj

            if minimalnyj == indeks:
                break

            self._kucha[indeks], self._kucha[minimalnyj] = self._kucha[minimalnyj], self._kucha[indeks]
            indeks = minimalnyj

class PlanirovshikKorotkihZadach:
    """Планировщик, отдающий приоритет задачам с меньшим временем выполнения"""

    def __init__(self, konfiguracii_zadach: List[Tuple]):
        """
        Инициализация планировщика

        Args:
            konfiguracii_zadach: Список конфигураций задач в формате
                (среднее_CPU, отклонение_CPU, среднее_IO, отклонение_IO)
        """
        self.tekushchee_vremya = 0.0
        self.zadachi = []
        self.ochered_gotovnosti = OcheredPrioritetov()

        # Создаем задачи на основе конфигураций
        for nomer, konfig in enumerate(konfiguracii_zadach):
            novaia_zadacha = Zadanije(nomer, konfig)
            self.zadachi.append(novaia_zadacha)

        # Отслеживаем оставшиеся циклы выполнения
        self.ostalos_ciklov = []

    def podgotovit_k_vypolneniu(self, kolichestvo_ciklov: int):
        """Подготовить систему к выполнению заданного количества циклов"""
        self.ostalos_ciklov = [kolichestvo_ciklov] * len(self.zadachi)

        # Инициализируем все задачи
        for zadacha in self.zadachi:
            if self.ostalos_ciklov[zadacha.id] > 0:
                interval_cpu = zadacha.sgenerirovat_interval_cpu()
                self.ochered_gotovnosti.dobavit_element(interval_cpu, zadacha.id)
                zadacha.vremya_gotovnosti = 0.0

    def zapustit_modelirovanie(self, kolichestvo_ciklov: int):
        """Запустить процесс моделирования"""
        self.podgotovit_k_vypolneniu(kolichestvo_ciklov)

        print("Запуск моделирования SJF планировщика...")
        shag = 0

        # Главный цикл выполнения
        while any(ost > 0 for ost in self.ostalos_ciklov):
            shag += 1

            if not self.ochered_gotovnosti.pusta():
                self._obrabotat_ochered_gotovnosti()
            else:
                self._perejti_k_sleduyushemu_io()

            self._proverit_zavershenie_io()

            # Вывод прогресса каждые 10000 шагов
            if shag % 10000 == 0:
                vsego_ostalos = sum(self.ostalos_ciklov)
                print(f"Шаг {shag}: осталось циклов - {vsego_ostalos}")

    def _obrabotat_ochered_gotovnosti(self):
        """Обработать задачи из очереди готовности"""
        dlitelnost_cpu, id_zadachi = self.ochered_gotovnosti.izvlech_minimum()
        zadacha = self.zadachi[id_zadachi]

        if self.ostalos_ciklov[id_zadachi] <= 0:
            return

        # Учитываем время ожидания
        vremya_ozhidaniya = self.tekushchee_vremya - zadacha.vremya_gotovnosti
        zadacha.vremya_ozhidaniya += vremya_ozhidaniya

        # Выполняем на процессоре
        self.tekushchee_vremya += dlitelnost_cpu
        zadacha.vremya_cpu += dlitelnost_cpu
        zadacha.zavershennye_cikly += 1
        self.ostalos_ciklov[id_zadachi] -= 1

        # Если задача еще не завершена, планируем ввод-вывод
        if self.ostalos_ciklov[id_zadachi] > 0:
            dlitelnost_io = zadacha.sgenerirovat_interval_io()
            zadacha.vremya_vvoda_vyvoda += dlitelnost_io
            zadacha.vremya_okonchaniya_io = self.tekushchee_vremya + dlitelnost_io

    def _perejti_k_sleduyushemu_io(self):
        """Перейти ко времени завершения ближайшей операции ввода-вывода"""
        spisok_io = [
            z.vremya_okonchaniya_io for z in self.zadachi
            if z.vremya_okonchaniya_io is not None
        ]

        if spisok_io:
            self.tekushchee_vremya = min(spisok_io)

    def _proverit_zavershenie_io(self):
        """Проверить завершение операций ввода-вывода"""
        for zadacha in self.zadachi:
            if (zadacha.vremya_okonchaniya_io is not None and
                zadacha.vremya_okonchaniya_io <= self.tekushchee_vremya + 1e-9):

                zadacha.vremya_okonchaniya_io = None

                if self.ostalos_ciklov[zadacha.id] > 0:
                    # Генерируем новый CPU интервал
                    novyj_interval = zadacha.sgenerirovat_interval_cpu()
                    self.ochered_gotovnosti.dobavit_element(novyj_interval, zadacha.id)
                    zadacha.vremya_gotovnosti = self.tekushchee_vremya

    def vivesti_rezultaty(self):
        """Вывести результаты моделирования"""
        print("\n" + "═" * 65)
        print("ИТОГИ МОДЕЛИРОВАНИЯ: SJF ПЛАНИРОВЩИК")
        print("═" * 65)

        obshchee_vremya_cpu = 0.0
        obshchee_vremya_ozhidaniya = 0.0

        for i, zadacha in enumerate(self.zadachi):
            print(f"\nЗадача #{i+1} (ID: {zadacha.id}):")
            print(f"  ├─ Время работы на CPU:    {zadacha.vremya_cpu:10.3f}")
            print(f"  ├─ Время ожидания:         {zadacha.vremya_ozhidaniya:10.3f}")
            print(f"  ├─ Время ввода-вывода:     {zadacha.vremya_vvoda_vyvoda:10.3f}")
            print(f"  └─ Выполнено циклов:       {zadacha.zavershennye_cikly}")

            obshchee_vremya_cpu += zadacha.vremya_cpu
            obshchee_vremya_ozhidaniya += zadacha.vremya_ozhidaniya

        print("=" * 60)
        print("СВОДНЫЕ ПОКАЗАТЕЛИ:")
        print(f"  ├─ Общее время CPU:           {obshchee_vremya_cpu:10.3f}")
        print(f"  ├─ Среднее время ожидания:    {obshchee_vremya_ozhidaniya/len(self.zadachi):10.3f}")
        print(f"  ├─ Общее время моделирования: {self.tekushchee_vremya:10.3f}")
        print(f"  └─ КПД системы:               {(obshchee_vremya_cpu/self.tekushchee_vremya)*100:9.1f}%")

# Демонстрационный запуск
if __name__ == "__main__":
    # Установка seed для воспроизводимости
    random.seed(2024)

    # Конфигурация задач
    konfiguracii = [
        (5.0, 1.0, 1.0, 0.3),   # Короткие задачи
        (8.0, 1.5, 1.2, 0.4),   # Средние задачи
        (12.0, 2.0, 1.5, 0.5),  # Длительные задачи
    ]

    print("Начало работы SJF планировщика...")
    print(f"Количество задач: {len(konfiguracii)}")
    print(f"Циклов на задачу: 1000")

    # Создание и запуск планировщика
    planirovshik = PlanirovshikKorotkihZadach(konfiguracii)
    planirovshik.zapustit_modelirovanie(1000)
    planirovshik.vivesti_rezultaty()