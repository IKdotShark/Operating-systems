"""
Симулятор последовательного планировщика задач (FIFO)
Обрабатывает задачи в порядке их поступления в систему
"""

import random
import math
from collections import deque
from typing import List, Tuple


class Protsess:
    """Представление процесса в операционной системе"""

    def __init__(self, identifikator: int, harakteristiki: Tuple):
        self.nomer = identifikator
        self.cpu_srednee = harakteristiki[0]
        self.cpu_razbros = harakteristiki[1]
        self.io_srednee = harakteristiki[2]
        self.io_razbros = harakteristiki[3]

        # Накопленные показатели
        self.protsessornoe_vremya = 0.0
        self.period_ozhidaniya = 0.0
        self.period_obmena = 0.0
        self.otrabotannye_operatsii = 0

        # Текущие параметры
        self.planiiruemyj_cpu_interval = None
        self.moment_gotovnosti = 0.0
        self.zavershenie_io_vremya = None

    def sozdat_normalnoe_raspredelenie(self, srednee: float, razbros: float) -> float:
        """Создать значение по нормальному распределению"""
        # Применяем полярный метод для нормального распределения
        while True:
            u = 2.0 * random.random() - 1.0
            v = 2.0 * random.random() - 1.0
            s = u * u + v * v

            if 0 < s < 1:
                multiplier = math.sqrt(-2.0 * math.log(s) / s)
                z = u * multiplier
                break

        rezultat = srednee + z * razbros
        return max(0.001, rezultat)

    def opredelit_cpu_dlitelnost(self) -> float:
        """Определить длительность работы на процессоре"""
        self.planiiruemyj_cpu_interval = self.sozdat_normalnoe_raspredelenie(
            self.cpu_srednee, self.cpu_razbros
        )
        return self.planiiruemyj_cpu_interval

    def opredelit_io_dlitelnost(self) -> float:
        """Определить длительность операции ввода-вывода"""
        return self.sozdat_normalnoe_raspredelenie(
            self.io_srednee, self.io_razbros
        )


class OcheredVypolneniya:
    """Очередь процессов для выполнения"""

    def __init__(self):
        self._konteiner = deque()
        self._kolichestvo = 0

    def postavit_v_ochered(self, id_protsessa: int):
        """Добавить процесс в очередь"""
        self._konteiner.append(id_protsessa)
        self._kolichestvo += 1

    def vziat_iz_ocheredi(self) -> int:
        """Взять процесс из начала очереди"""
        if self._konteiner:
            self._kolichestvo -= 1
            return self._konteiner.popleft()
        raise RuntimeError("Очередь выполнения пуста")

    def imeet_elementy(self) -> bool:
        """Проверить наличие процессов в очереди"""
        return self._kolichestvo > 0

    def razmer(self) -> int:
        """Получить размер очереди"""
        return self._kolichestvo


class UpravitelPosledovatelnogoPlan:
    """Управляющий последовательным выполнением процессов"""

    def __init__(self, spisok_parametrov: List[Tuple]):
        self.sistemnaya_datasha = 0.0
        self.vse_protsessy = []
        self.ochered_dostupnyh = OcheredVypolneniya()

        # Инициализация всех процессов
        for idx, parametry in enumerate(spisok_parametrov):
            novy_protsess = Protsess(idx, parametry)
            self.vse_protsessy.append(novy_protsess)

        # Счетчик оставшихся операций
        self.ostavshiesya_deistviya = []

    def podgotovit_sistemu(self, tselevoe_kolichestvo: int):
        """Подготовить систему к работе"""
        self.ostavshiesya_deistviya = [tselevoe_kolichestvo] * len(self.vse_protsessy)

        # Постановка всех процессов в очередь
        for protsess in self.vse_protsessy:
            if self.ostavshiesya_deistviya[protsess.nomer] > 0:
                protsess.opredelit_cpu_dlitelnost()
                protsess.moment_gotovnosti = 0.0
                self.ochered_dostupnyh.postavit_v_ochered(protsess.nomer)

    def osushestvit_modelirovanie(self, tselevoe_kolichestvo: int):
        """Осуществить процесс моделирования"""
        self.podgotovit_sistemu(tselevoe_kolichestvo)

        schetchik_iteratsiy = 0
        print("Инициализация FIFO планировщика...")

        # Основной рабочий цикл
        while any(ost > 0 for ost in self.ostavshiesya_deistviya):
            schetchik_iteratsiy += 1

            if self.ochered_dostupnyh.imeet_elementy():
                self._obslujit_sleduyuschiy()
            else:
                self._sdelat_skachok_vremeni()

            self._obnovit_sostoyaniya()

            # Индикация прогресса
            if schetchik_iteratsiy % 10000 == 0:
                summa_ostavshihsya = sum(self.ostavshiesya_deistviya)
                print(f"Итерация {schetchik_iteratsiy}: осталось задач - {summa_ostavshihsya}")

    def _obslujit_sleduyuschiy(self):
        """Обслужить следующий процесс в очереди"""
        id_zahvachennogo = self.ochered_dostupnyh.vziat_iz_ocheredi()
        tekuschiy = self.vse_protsessy[id_zahvachennogo]

        if self.ostavshiesya_deistviya[id_zahvachennogo] <= 0:
            return

        # Фиксация времени ожидания
        ozhidanie = self.sistemnaya_datasha - tekuschiy.moment_gotovnosti
        tekuschiy.period_ozhidaniya += ozhidanie

        # Исполнение на центральном процессоре
        trebuemoe_vremya = tekuschiy.planiiruemyj_cpu_interval
        self.sistemnaya_datasha += trebuemoe_vremya
        tekuschiy.protsessornoe_vremya += trebuemoe_vremya
        tekuschiy.otrabotannye_operatsii += 1
        self.ostavshiesya_deistviya[id_zahvachennogo] -= 1

        # Организация операции обмена
        if self.ostavshiesya_deistviya[id_zahvachennogo] > 0:
            dlitelnost_obmena = tekuschiy.opredelit_io_dlitelnost()
            tekuschiy.period_obmena += dlitelnost_obmena
            tekuschiy.zavershenie_io_vremya = self.sistemnaya_datasha + dlitelnost_obmena
            tekuschiy.planiiruemyj_cpu_interval = None

    def _sdelat_skachok_vremeni(self):
        """Совершить скачок времени к ближайшему событию"""
        aktivnye_momenty = [
            p.zavershenie_io_vremya for p in self.vse_protsessy
            if p.zavershenie_io_vremya is not None
        ]

        if aktivnye_momenty:
            self.sistemnaya_datasha = min(aktivnye_momenty)

    def _obnovit_sostoyaniya(self):
        """Обновить состояния завершенных операций"""
        for protsess in self.vse_protsessy:
            if (protsess.zavershenie_io_vremya is not None and
                    protsess.zavershenie_io_vremya <= self.sistemnaya_datasha + 1e-9):

                protsess.zavershenie_io_vremya = None

                if self.ostavshiesya_deistviya[protsess.nomer] > 0:
                    # Подготовка к следующему выполнению
                    protsess.opredelit_cpu_dlitelnost()
                    protsess.moment_gotovnosti = self.sistemnaya_datasha
                    self.ochered_dostupnyh.postavit_v_ochered(protsess.nomer)

    def predostavit_otchet(self):
        """Предоставить отчет о работе системы"""
        zagolovok = "ФИНАЛЬНЫЙ ОТЧЕТ: ПОСЛЕДОВАТЕЛЬНОЕ ПЛАНИРОВАНИЕ"

        sovokupnoe_cpu = 0.0
        sovokupnoe_ozhidanie = 0.0

        for index, protsess in enumerate(self.vse_protsessy):
            print(f"\nПроцесс №{index + 1} (идентификатор {protsess.nomer}):")
            print(f"  ┌─ Активное время ЦП: {protsess.protsessornoe_vremya:12.3f}")
            print(f"  ├─ Время в ожидании:   {protsess.period_ozhidaniya:12.3f}")
            print(f"  ├─ Время ввода-вывода: {protsess.period_obmena:12.3f}")
            print(f"  └─ Исполнено операций: {protsess.otrabotannye_operatsii}")

            sovokupnoe_cpu += protsess.protsessornoe_vremya
            sovokupnoe_ozhidanie += protsess.period_ozhidaniya

        print("=" * 60)
        print("АНАЛИТИКА РАБОТЫ СИСТЕМЫ:")
        print(f"  ┌─ Совокупное время ЦП:     {sovokupnoe_cpu:12.3f}")
        print(f"  ├─ Среднее время ожидания:  {sovokupnoe_ozhidanie / len(self.vse_protsessy):12.3f}")
        print(f"  ├─ Полное время работы:     {self.sistemnaya_datasha:12.3f}")
        print(f"  └─ Утилизация ресурсов:     {(sovokupnoe_cpu / self.sistemnaya_datasha) * 100:11.1f}%")



# Пример использования
def demonstrirovat_rabotu_fifo():
    """Продемонстрировать работу FIFO планировщика"""
    # Настройки для тестирования
    random.seed(42)

    # Параметры процессов
    parametry_protsessov = [
        (4.8, 0.9, 0.9, 0.2),  # Быстрые процессы
        (7.5, 1.3, 1.1, 0.3),  # Процессы средней длительности
        (11.8, 1.9, 1.4, 0.5),  # Медленные процессы
    ]

    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ FIFO ПЛАНИРОВЩИКА".center(60))
    print("=" * 60)
    print(f"Количество процессов: {len(parametry_protsessov)}")
    print(f"Операций на процесс:  1000")
    print("=" * 60)

    # Создание и запуск
    upravlyayuschiy = UpravitelPosledovatelnogoPlan(parametry_protsessov)
    upravlyayuschiy.osushestvit_modelirovanie(1000)
    upravlyayuschiy.predostavit_otchet()


if __name__ == "__main__":
    demonstrirovat_rabotu_fifo()