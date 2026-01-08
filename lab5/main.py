import os
import struct
import time
from datetime import datetime
from tkinter import *
from tkinter import ttk, filedialog, messagebox, simpledialog
from collections import deque


# ==================== ФАЙЛОВАЯ СИСТЕМА ====================

class SimpleFS:
    def __init__(self, filename=None):
        self.filename = filename
        self.cluster_size = 1  # 1 байт на кластер
        self.max_name_len = 16
        self.max_files_per_dir = 16
        self.dir_entry_size = 30  # 1 + 1 + 16 + 4 + 4 + 4 = 30 байт
        self.current_dir_cluster = None
        self.dir_stack = []  # стек для навигации по каталогам

    def create_image(self, total_clusters, filename):
        """Создание образа файловой системы"""
        with open(filename, 'wb') as f:
            # 1. Размер ФС в кластерах (4 байта)
            f.write(struct.pack('I', total_clusters))

            # 2. Размер битовой карты в байтах (4 байта)
            bitmap_bytes = (total_clusters + 7) // 8
            f.write(struct.pack('I', bitmap_bytes))

            # 3. Битовая карта свободных блоков
            bitmap = bytearray([255] * bitmap_bytes)

            # Пометить первые N кластеров как занятые
            header_size = 8
            clusters_for_header = (header_size + self.cluster_size - 1) // self.cluster_size

            clusters_for_bitmap = (bitmap_bytes + self.cluster_size - 1) // self.cluster_size

            root_dir_size = self.max_files_per_dir * self.dir_entry_size
            clusters_for_root = (root_dir_size + self.cluster_size - 1) // self.cluster_size

            total_used_clusters = clusters_for_header + clusters_for_bitmap + clusters_for_root

            for i in range(total_used_clusters):
                byte_idx = i // 8
                bit_idx = i % 8
                bitmap[byte_idx] &= ~(1 << bit_idx)

            f.write(bitmap)

            # 4. Корневой каталог
            root_dir = bytearray(self.max_files_per_dir * self.dir_entry_size)

            # Запись текущего каталога '.'
            root_dir[0] = 1  # занята
            root_dir[1] = 1  # каталог
            root_dir[2:18] = b'.' + b'\0' * 15
            root_dir_cluster = clusters_for_header + clusters_for_bitmap
            root_dir[18:22] = struct.pack('I', root_dir_cluster)
            root_dir[22:26] = struct.pack('I', root_dir_cluster + clusters_for_root - 1)
            root_dir[26:30] = struct.pack('I', 1)  # только запись '.'

            # Запись родительского каталога '..' (ссылка на себя для корня)
            root_dir[30:60] = bytearray(self.dir_entry_size)
            root_dir[30] = 1  # занята
            root_dir[31] = 1  # каталог
            root_dir[32:48] = b'..' + b'\0' * 14
            root_dir[48:52] = struct.pack('I', root_dir_cluster)  # тот же каталог
            root_dir[52:56] = struct.pack('I', root_dir_cluster + clusters_for_root - 1)
            root_dir[56:60] = struct.pack('I', 2)  # две записи: '.' и '..'

            f.write(root_dir)

            # 5. Заполнить оставшееся пространство нулями
            total_bytes = total_clusters * self.cluster_size
            current_pos = f.tell()
            remaining = total_bytes - current_pos
            if remaining > 0:
                f.write(b'\0' * remaining)

        self.filename = filename
        self.total_clusters = total_clusters
        self.bitmap_bytes = bitmap_bytes
        self.root_dir_cluster = root_dir_cluster
        self.current_dir_cluster = root_dir_cluster
        self.dir_stack = [(root_dir_cluster, "/")]
        return True

    def mount(self, filename):
        """Монтирование файловой системы"""
        self.filename = filename
        if not os.path.exists(filename):
            return False

        with open(filename, 'rb') as f:
            self.total_clusters = struct.unpack('I', f.read(4))[0]
            self.bitmap_bytes = struct.unpack('I', f.read(4))[0]

            # Пропускаем битовую карту
            f.seek(self.bitmap_bytes, 1)

            # Определяем положение корневого каталога
            first_entry = f.read(self.dir_entry_size)
            self.root_dir_cluster = struct.unpack('I', first_entry[18:22])[0]
            self.current_dir_cluster = self.root_dir_cluster
            self.dir_stack = [(self.root_dir_cluster, "/")]

        return True

    def read_bitmap(self):
        """Чтение битовой карты"""
        with open(self.filename, 'rb') as f:
            f.seek(8)
            bitmap = f.read(self.bitmap_bytes)
        return bitmap

    def find_free_clusters(self, count):
        """Поиск свободных кластеров"""
        bitmap = self.read_bitmap()
        free_clusters = []

        for byte_idx in range(len(bitmap)):
            byte = bitmap[byte_idx]
            for bit_idx in range(8):
                cluster_idx = byte_idx * 8 + bit_idx
                if cluster_idx >= self.total_clusters:
                    break
                if (byte >> bit_idx) & 1:
                    free_clusters.append(cluster_idx)
                    if len(free_clusters) >= count:
                        return free_clusters
        return None

    def allocate_clusters(self, clusters):
        """Выделение кластеров"""
        bitmap = bytearray(self.read_bitmap())
        for cluster in clusters:
            byte_idx = cluster // 8
            bit_idx = cluster % 8
            bitmap[byte_idx] &= ~(1 << bit_idx)

        with open(self.filename, 'r+b') as f:
            f.seek(8)
            f.write(bitmap)

    def free_clusters(self, clusters):
        """Освобождение кластеров"""
        bitmap = bytearray(self.read_bitmap())
        for cluster in clusters:
            byte_idx = cluster // 8
            bit_idx = cluster % 8
            bitmap[byte_idx] |= (1 << bit_idx)

        with open(self.filename, 'r+b') as f:
            f.seek(8)
            f.write(bitmap)

    def read_dir(self, dir_cluster=None):
        """Чтение содержимого каталога"""
        if dir_cluster is None:
            dir_cluster = self.current_dir_cluster

        entries = []

        with open(self.filename, 'rb') as f:
            f.seek(dir_cluster)

            for i in range(self.max_files_per_dir):
                entry_data = f.read(self.dir_entry_size)
                if not entry_data:
                    break

                is_occupied = entry_data[0]
                if not is_occupied:
                    continue

                entry_type = entry_data[1]
                name = entry_data[2:18].decode('ascii', errors='ignore').rstrip('\0')

                if not name or name == '.' or name == '..':
                    continue

                start_cluster = struct.unpack('I', entry_data[18:22])[0]
                end_cluster = struct.unpack('I', entry_data[22:26])[0]
                num_entries = struct.unpack('I', entry_data[26:30])[0] if entry_type == 1 else 0

                size = (end_cluster - start_cluster + 1) * self.cluster_size if start_cluster <= end_cluster else 0

                entries.append({
                    'name': name,
                    'is_dir': entry_type == 1,
                    'size': size,
                    'start_cluster': start_cluster,
                    'end_cluster': end_cluster,
                    'num_entries': num_entries,
                    'occupied': is_occupied
                })

        return entries

    def find_free_dir_entry(self, dir_cluster):
        """Поиск свободной записи в каталоге"""
        with open(self.filename, 'rb') as f:
            f.seek(dir_cluster)

            for i in range(self.max_files_per_dir):
                f.seek(dir_cluster + i * self.dir_entry_size)
                entry_data = f.read(self.dir_entry_size)

                if not entry_data or entry_data[0] == 0:
                    return i

        return None

    def update_dir_entry_count(self, dir_cluster, delta):
        """Обновление счетчика записей в каталоге"""
        with open(self.filename, 'r+b') as f:
            # Находим запись текущего каталога '.'
            f.seek(dir_cluster)
            for i in range(self.max_files_per_dir):
                f.seek(dir_cluster + i * self.dir_entry_size)
                entry_data = f.read(self.dir_entry_size)

                if entry_data[0] == 1 and entry_data[1] == 1:
                    name = entry_data[2:18].decode('ascii', errors='ignore').rstrip('\0')
                    if name == '.':
                        current_count = struct.unpack('I', entry_data[26:30])[0]
                        new_count = max(2, current_count + delta)  # минимум 2 ('.' и '..')

                        f.seek(dir_cluster + i * self.dir_entry_size + 26)
                        f.write(struct.pack('I', new_count))
                        break

    def copy_to_fs(self, src_path, dest_name, dest_dir_cluster=None):
        """Копирование файла в файловую систему"""
        if dest_dir_cluster is None:
            dest_dir_cluster = self.current_dir_cluster

        if len(dest_name) > self.max_name_len:
            return False, "Имя файла слишком длинное"

        # Проверить, существует ли уже файл с таким именем
        entries = self.read_dir(dest_dir_cluster)
        for entry in entries:
            if entry['name'] == dest_name:
                return False, "Файл с таким именем уже существует"

        # Прочитать исходный файл
        try:
            with open(src_path, 'rb') as f:
                data = f.read()
        except:
            return False, "Не удалось прочитать исходный файл"

        file_size = len(data)
        clusters_needed = (file_size + self.cluster_size - 1) // self.cluster_size

        # Найти свободные кластеры
        free_clusters = self.find_free_clusters(clusters_needed)
        if not free_clusters or len(free_clusters) < clusters_needed:
            return False, "Недостаточно свободного места"

        # Найти свободную запись в каталоге
        entry_idx = self.find_free_dir_entry(dest_dir_cluster)
        if entry_idx is None:
            return False, "Каталог полон"

        # Записать данные файла
        with open(self.filename, 'r+b') as f:
            for i in range(clusters_needed):
                cluster = free_clusters[i]
                f.seek(cluster)

                start_idx = i * self.cluster_size
                end_idx = min(start_idx + self.cluster_size, file_size)
                chunk = data[start_idx:end_idx]

                if len(chunk) < self.cluster_size:
                    chunk += b'\0' * (self.cluster_size - len(chunk))

                f.write(chunk)

            # Записать запись в каталог
            entry_pos = dest_dir_cluster + entry_idx * self.dir_entry_size
            f.seek(entry_pos)

            entry = bytearray(self.dir_entry_size)
            entry[0] = 1
            entry[1] = 0
            entry[2:18] = dest_name.ljust(16, '\0').encode('ascii')
            entry[18:22] = struct.pack('I', free_clusters[0])
            entry[22:26] = struct.pack('I', free_clusters[clusters_needed - 1])
            entry[26:30] = struct.pack('I', 0)

            f.write(entry)

        # Обновить битовую карту
        self.allocate_clusters(free_clusters[:clusters_needed])

        # Обновить счетчик записей в каталоге
        self.update_dir_entry_count(dest_dir_cluster, 1)

        return True, "Файл успешно скопирован"

    def copy_from_fs(self, src_name, dest_path, src_dir_cluster=None):
        """Копирование файла из файловой системы"""
        if src_dir_cluster is None:
            src_dir_cluster = self.current_dir_cluster

        entries = self.read_dir(src_dir_cluster)
        file_entry = None

        for entry in entries:
            if entry['name'] == src_name and not entry['is_dir']:
                file_entry = entry
                break

        if not file_entry:
            return False, "Файл не найден"

        # Прочитать данные файла
        data = bytearray()
        start_cluster = file_entry['start_cluster']
        end_cluster = file_entry['end_cluster']

        with open(self.filename, 'rb') as f:
            for cluster in range(start_cluster, end_cluster + 1):
                f.seek(cluster)
                chunk = f.read(self.cluster_size)
                data.extend(chunk)

        actual_size = file_entry['size']
        data = data[:actual_size]

        # Записать файл
        try:
            with open(dest_path, 'wb') as f:
                f.write(data)
            return True, "Файл успешно скопирован"
        except:
            return False, "Не удалось записать файл"

    def delete_item(self, name, is_dir=False):
        """Удаление файла или каталога"""
        entries = self.read_dir(self.current_dir_cluster)
        item_entry = None

        for entry in entries:
            if entry['name'] == name and entry['is_dir'] == is_dir:
                item_entry = entry
                break

        if not item_entry:
            return False, "Элемент не найден"

        if is_dir:
            # Рекурсивно удалить содержимое каталога
            success, message = self.delete_directory_contents(item_entry['start_cluster'])
            if not success:
                return False, message

        # Освободить кластеры
        clusters = list(range(item_entry['start_cluster'], item_entry['end_cluster'] + 1))
        self.free_clusters(clusters)

        # Найти и удалить запись в каталоге
        with open(self.filename, 'r+b') as f:
            f.seek(self.current_dir_cluster)

            for i in range(self.max_files_per_dir):
                f.seek(self.current_dir_cluster + i * self.dir_entry_size)
                entry_data = f.read(self.dir_entry_size)

                if entry_data[0] == 1:
                    entry_name = entry_data[2:18].decode('ascii', errors='ignore').rstrip('\0')

                    if entry_name == name:
                        # Пометить запись как свободную
                        f.seek(self.current_dir_cluster + i * self.dir_entry_size)
                        f.write(b'\0' * self.dir_entry_size)

                        # Обновить счетчик записей
                        self.update_dir_entry_count(self.current_dir_cluster, -1)

                        return True, f"{'Каталог' if is_dir else 'Файл'} успешно удален"

        return False, "Ошибка при удалении"

    def delete_directory_contents(self, dir_cluster):
        """Рекурсивное удаление содержимого каталога"""
        # Читаем записи каталога
        entries = []
        with open(self.filename, 'rb') as f:
            f.seek(dir_cluster)

            for i in range(self.max_files_per_dir):
                entry_data = f.read(self.dir_entry_size)
                if not entry_data or entry_data[0] == 0:
                    continue

                entry_type = entry_data[1]
                name = entry_data[2:18].decode('ascii', errors='ignore').rstrip('\0')

                if name in ('.', '..'):
                    continue

                start_cluster = struct.unpack('I', entry_data[18:22])[0]
                end_cluster = struct.unpack('I', entry_data[22:26])[0]

                entries.append({
                    'name': name,
                    'is_dir': entry_type == 1,
                    'start_cluster': start_cluster,
                    'end_cluster': end_cluster
                })

        # Рекурсивно удаляем содержимое
        for entry in entries:
            if entry['is_dir']:
                # Рекурсивно удаляем подкаталог
                success, message = self.delete_directory_contents(entry['start_cluster'])
                if not success:
                    return False, f"Ошибка при удалении каталога {entry['name']}: {message}"

            # Освобождаем кластеры
            clusters = list(range(entry['start_cluster'], entry['end_cluster'] + 1))
            self.free_clusters(clusters)

            # Помечаем запись как свободную
            with open(self.filename, 'r+b') as f:
                # Находим запись
                f.seek(dir_cluster)
                for i in range(self.max_files_per_dir):
                    f.seek(dir_cluster + i * self.dir_entry_size)
                    entry_data = f.read(self.dir_entry_size)

                    if entry_data[0] == 1:
                        entry_name = entry_data[2:18].decode('ascii', errors='ignore').rstrip('\0')
                        if entry_name == entry['name']:
                            f.seek(dir_cluster + i * self.dir_entry_size)
                            f.write(b'\0' * self.dir_entry_size)
                            break

        # Обновляем счетчик записей в каталоге
        self.update_dir_entry_count(dir_cluster, -len(entries))

        return True, "Содержимое каталога удалено"

    def rename_item(self, old_name, new_name):
        """Переименование файла или каталога"""
        if len(new_name) > self.max_name_len:
            return False, "Новое имя слишком длинное"

        # Проверить, существует ли уже элемент с таким именем
        entries = self.read_dir(self.current_dir_cluster)
        for entry in entries:
            if entry['name'] == new_name:
                return False, "Элемент с таким именем уже существует"

        with open(self.filename, 'r+b') as f:
            f.seek(self.current_dir_cluster)

            for i in range(self.max_files_per_dir):
                f.seek(self.current_dir_cluster + i * self.dir_entry_size)
                entry_data = f.read(self.dir_entry_size)

                if entry_data[0] == 1:
                    name = entry_data[2:18].decode('ascii', errors='ignore').rstrip('\0')

                    if name == old_name:
                        f.seek(self.current_dir_cluster + i * self.dir_entry_size + 2)
                        f.write(new_name.ljust(16, '\0').encode('ascii'))

                        return True, "Успешно переименовано"

        return False, "Элемент не найден"

    def create_directory(self, dir_name, parent_dir_cluster=None):
        """Создание каталога"""
        if parent_dir_cluster is None:
            parent_dir_cluster = self.current_dir_cluster

        if len(dir_name) > self.max_name_len:
            return False, "Имя каталога слишком длинное"

        # Проверить, существует ли уже каталог с таким именем
        entries = self.read_dir(parent_dir_cluster)
        for entry in entries:
            if entry['name'] == dir_name:
                return False, "Каталог с таким именем уже существует"

        # Найти свободные кластеры для нового каталога
        dir_size = self.max_files_per_dir * self.dir_entry_size
        clusters_needed = (dir_size + self.cluster_size - 1) // self.cluster_size

        free_clusters = self.find_free_clusters(clusters_needed)
        if not free_clusters or len(free_clusters) < clusters_needed:
            return False, "Недостаточно свободного места"

        # Найти свободную запись в родительском каталоге
        entry_idx = self.find_free_dir_entry(parent_dir_cluster)
        if entry_idx is None:
            return False, "Каталог полон"

        # Создать новый каталог
        new_dir = bytearray(clusters_needed * self.cluster_size)

        # Запись текущего каталога '.'
        new_dir[0] = 1
        new_dir[1] = 1
        new_dir[2:18] = b'.' + b'\0' * 15
        new_dir[18:22] = struct.pack('I', free_clusters[0])
        new_dir[22:26] = struct.pack('I', free_clusters[clusters_needed - 1])
        new_dir[26:30] = struct.pack('I', 2)  # '.' и '..'

        # Запись родительского каталога '..'
        new_dir[30] = 1
        new_dir[31] = 1
        new_dir[32:48] = b'..' + b'\0' * 14
        new_dir[48:52] = struct.pack('I', parent_dir_cluster)
        new_dir[52:56] = struct.pack('I', parent_dir_cluster +
                                     ((self.max_files_per_dir * self.dir_entry_size +
                                       self.cluster_size - 1) // self.cluster_size) - 1)
        new_dir[56:60] = struct.pack('I', 2)  # '.' и '..'

        # Записать каталог на диск
        with open(self.filename, 'r+b') as f:
            for i in range(clusters_needed):
                f.seek(free_clusters[i])
                start_idx = i * self.cluster_size
                end_idx = start_idx + self.cluster_size
                f.write(new_dir[start_idx:end_idx])

            # Записать запись в родительский каталог
            entry_pos = parent_dir_cluster + entry_idx * self.dir_entry_size
            f.seek(entry_pos)

            entry = bytearray(self.dir_entry_size)
            entry[0] = 1
            entry[1] = 1
            entry[2:18] = dir_name.ljust(16, '\0').encode('ascii')
            entry[18:22] = struct.pack('I', free_clusters[0])
            entry[22:26] = struct.pack('I', free_clusters[clusters_needed - 1])
            entry[26:30] = struct.pack('I', 2)

            f.write(entry)

        # Обновить битовую карту
        self.allocate_clusters(free_clusters[:clusters_needed])

        # Обновить счетчик записей в родительском каталоге
        self.update_dir_entry_count(parent_dir_cluster, 1)

        return True, "Каталог успешно создан"

    def change_directory(self, dir_name):
        """Смена текущего каталога"""
        if dir_name == "..":
            if len(self.dir_stack) > 1:
                # Возвращаемся на уровень выше
                self.dir_stack.pop()
                self.current_dir_cluster, _ = self.dir_stack[-1]
                return True, "Переход в родительский каталог"
            else:
                return False, "Уже в корневом каталоге"

        elif dir_name == "/":
            # Переход в корень
            self.dir_stack = [(self.root_dir_cluster, "/")]
            self.current_dir_cluster = self.root_dir_cluster
            return True, "Переход в корневой каталог"

        else:
            # Поиск каталога
            entries = self.read_dir(self.current_dir_cluster)
            target_dir = None

            for entry in entries:
                if entry['name'] == dir_name and entry['is_dir']:
                    target_dir = entry
                    break

            if not target_dir:
                return False, "Каталог не найден"

            # Добавляем в стек
            path = self.dir_stack[-1][1]
            if path == "/":
                new_path = f"/{dir_name}"
            else:
                new_path = f"{path}/{dir_name}"

            self.dir_stack.append((target_dir['start_cluster'], new_path))
            self.current_dir_cluster = target_dir['start_cluster']
            return True, f"Переход в каталог {dir_name}"

    def get_current_path(self):
        """Получить текущий путь"""
        return self.dir_stack[-1][1]

    def move_item(self, src_name, dest_dir_cluster, dest_name=None):
        """Перемещение файла или каталога"""
        if dest_name is None:
            dest_name = src_name

        if len(dest_name) > self.max_name_len:
            return False, "Имя файла слишком длинное"

        # Найти исходный элемент
        entries = self.read_dir(self.current_dir_cluster)
        src_entry = None

        for entry in entries:
            if entry['name'] == src_name:
                src_entry = entry
                break

        if not src_entry:
            return False, "Исходный элемент не найден"

        # Проверить, существует ли уже элемент с таким именем в целевом каталоге
        dest_entries = self.read_dir(dest_dir_cluster)
        for entry in dest_entries:
            if entry['name'] == dest_name:
                return False, "Элемент с таким именем уже существует в целевом каталоге"

        # Найти свободную запись в целевом каталоге
        entry_idx = self.find_free_dir_entry(dest_dir_cluster)
        if entry_idx is None:
            return False, "Целевой каталог полон"

        # Скопировать запись в целевой каталог
        with open(self.filename, 'r+b') as f:
            # Читаем исходную запись
            f.seek(self.current_dir_cluster)
            src_entry_pos = None
            src_entry_data = None

            for i in range(self.max_files_per_dir):
                f.seek(self.current_dir_cluster + i * self.dir_entry_size)
                entry_data = f.read(self.dir_entry_size)

                if entry_data[0] == 1:
                    name = entry_data[2:18].decode('ascii', errors='ignore').rstrip('\0')
                    if name == src_name:
                        src_entry_pos = self.current_dir_cluster + i * self.dir_entry_size
                        src_entry_data = bytearray(entry_data)
                        break

            if not src_entry_data:
                return False, "Не удалось найти исходную запись"

            # Записываем в целевой каталог
            dest_entry_pos = dest_dir_cluster + entry_idx * self.dir_entry_size
            f.seek(dest_entry_pos)

            # Обновляем имя если нужно
            if dest_name != src_name:
                src_entry_data[2:18] = dest_name.ljust(16, '\0').encode('ascii')

            f.write(src_entry_data)

            # Удаляем исходную запись
            f.seek(src_entry_pos)
            f.write(b'\0' * self.dir_entry_size)

        # Обновляем счетчики записей
        self.update_dir_entry_count(self.current_dir_cluster, -1)
        self.update_dir_entry_count(dest_dir_cluster, 1)

        return True, "Элемент успешно перемещен"

    def get_parent_directory(self, dir_cluster):
        """Получить кластер родительского каталога"""
        with open(self.filename, 'rb') as f:
            f.seek(dir_cluster)

            # Ищем запись '..'
            for i in range(self.max_files_per_dir):
                f.seek(dir_cluster + i * self.dir_entry_size)
                entry_data = f.read(self.dir_entry_size)

                if entry_data[0] == 1 and entry_data[1] == 1:
                    name = entry_data[2:18].decode('ascii', errors='ignore').rstrip('\0')
                    if name == '..':
                        return struct.unpack('I', entry_data[18:22])[0]

        return self.root_dir_cluster


# ==================== GUI ====================

class FSGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple File System Manager v2.0")
        self.root.geometry("1100x750")

        self.fs = SimpleFS()

        # Настройка стиля
        self.setup_style()

        # Создание виджетов
        self.create_widgets()

    def setup_style(self):
        """Настройка стилей виджетов"""
        style = ttk.Style()
        style.theme_use('clam')

        colors = {
            'bg': '#f5f5f5',
            'frame_bg': '#ffffff',
            'accent': '#4a86e8',
            'text': '#333333',
            'border': '#cccccc'
        }

        style.configure('TFrame', background=colors['bg'])
        style.configure('TLabel', background=colors['bg'], foreground=colors['text'])
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Treeview',
                        background=colors['frame_bg'],
                        fieldbackground=colors['frame_bg'],
                        foreground=colors['text'])
        style.configure('Treeview.Heading',
                        background=colors['accent'],
                        foreground='white',
                        font=('Arial', 10, 'bold'))

        self.root.configure(bg=colors['bg'])

    def create_widgets(self):
        # Главный контейнер
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Верхняя панель
        self.create_top_panel(main_container)

        # Область навигации
        self.create_navigation_panel(main_container)

        # Основная область
        main_panel = ttk.Frame(main_container)
        main_panel.pack(fill=BOTH, expand=True, pady=(10, 0))

        # Левая панель (операции)
        self.create_left_panel(main_panel)

        # Правая панель (файлы)
        self.create_right_panel(main_panel)

        # Статус бар
        self.create_status_bar()

    def create_top_panel(self, parent):
        """Создание верхней панели"""
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=X, pady=(0, 10))

        title_label = ttk.Label(top_frame, text="📁 Менеджер файловой системы",
                                style='Header.TLabel')
        title_label.pack(side=LEFT, padx=(0, 20))

        self.fs_info_label = ttk.Label(top_frame, text="ФС: не смонтирована")
        self.fs_info_label.pack(side=LEFT, padx=10)

        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=RIGHT)

        ttk.Button(btn_frame, text="🆕 Создать",
                   command=self.create_image).pack(side=LEFT, padx=2)
        ttk.Button(btn_frame, text="🔗 Монтировать",
                   command=self.mount_fs).pack(side=LEFT, padx=2)

    def create_navigation_panel(self, parent):
        """Создание панели навигации"""
        nav_frame = ttk.Frame(parent)
        nav_frame.pack(fill=X, pady=(0, 10))

        # Кнопки навигации
        ttk.Button(nav_frame, text="⬆️ Наверх",
                   command=self.go_up).pack(side=LEFT, padx=2)
        ttk.Button(nav_frame, text="🏠 В корень",
                   command=self.go_root).pack(side=LEFT, padx=2)

        # Поле текущего пути
        self.path_var = StringVar()
        self.path_var.set("/")

        path_label = ttk.Label(nav_frame, text="Текущий путь:")
        path_label.pack(side=LEFT, padx=(20, 5))

        path_entry = ttk.Entry(nav_frame, textvariable=self.path_var, width=50)
        path_entry.pack(side=LEFT, padx=(0, 10))

        ttk.Button(nav_frame, text="📂 Перейти",
                   command=self.change_directory).pack(side=LEFT)

    def create_left_panel(self, parent):
        """Создание левой панели с операциями"""
        left_frame = ttk.LabelFrame(parent, text="Операции с файлами", padding=10)
        left_frame.pack(side=LEFT, fill=Y, padx=(0, 10))

        # Группа файловых операций
        file_ops = [
            ("📥 Копировать в ФС", self.copy_to_fs_gui),
            ("📤 Копировать из ФС", self.copy_from_fs_gui),
            ("✏️ Переименовать", self.rename_gui),
            ("➡️ Переместить", self.move_item_gui),
            ("🗑️ Удалить файл", self.delete_file_gui),
            ("🔄 Обновить", self.refresh_list)
        ]

        for text, command in file_ops:
            btn = ttk.Button(left_frame, text=text, command=command, width=20)
            btn.pack(pady=3)

        # Разделитель
        ttk.Separator(left_frame, orient=HORIZONTAL).pack(fill=X, pady=10)

        # Группа операций с каталогами
        dir_ops = [
            ("📁 Создать каталог", self.create_directory),
            ("🗑️ Удалить каталог", self.delete_directory_gui),
            ("➡️ Переместить каталог", self.move_directory_gui)
        ]

        for text, command in dir_ops:
            btn = ttk.Button(left_frame, text=text, command=command, width=20)
            btn.pack(pady=3)

        # Информация о системе
        info_frame = ttk.LabelFrame(left_frame, text="Информация о ФС", padding=10)
        info_frame.pack(fill=X, pady=(20, 0))

        ttk.Label(info_frame, text="Размер кластера: 1 байт").pack(anchor=W)
        ttk.Label(info_frame, text="Имя: до 16 символов").pack(anchor=W)
        ttk.Label(info_frame, text="Файлов в каталоге: ≤16").pack(anchor=W)

    def create_right_panel(self, parent):
        """Создание правой панели со списком файлов"""
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True)

        # Заголовок
        header_frame = ttk.Frame(right_frame)
        header_frame.pack(fill=X, pady=(0, 10))

        self.dir_label = ttk.Label(header_frame, text="Содержимое: /",
                                   font=('Arial', 11, 'bold'))
        self.dir_label.pack(side=LEFT)

        # Дерево файлов
        tree_frame = ttk.Frame(right_frame)
        tree_frame.pack(fill=BOTH, expand=True)

        columns = ('name', 'type', 'size', 'clusters', 'status')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=25)

        self.tree.heading('name', text='Имя')
        self.tree.heading('type', text='Тип')
        self.tree.heading('size', text='Размер (байт)')
        self.tree.heading('clusters', text='Кластеры')
        self.tree.heading('status', text='Статус')

        self.tree.column('name', width=200)
        self.tree.column('type', width=100)
        self.tree.column('size', width=100)
        self.tree.column('clusters', width=100)
        self.tree.column('status', width=100)

        # Полосы прокрутки
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Привязка событий
        self.tree.bind('<Double-Button-1>', self.on_item_double_click)

    def create_status_bar(self):
        """Создание статус бара"""
        self.status_var = StringVar()
        self.status_var.set("Готов")

        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               relief=SUNKEN, anchor=W, padding=(10, 5))
        status_bar.pack(side=BOTTOM, fill=X)

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def update_path_display(self):
        """Обновление отображения текущего пути"""
        if self.fs.filename:
            path = self.fs.get_current_path()
            self.path_var.set(path)
            self.dir_label.config(text=f"Содержимое: {path}")

    def create_image(self):
        size = simpledialog.askinteger("Создание образа",
                                       "Введите размер файловой системы (в кластерах):",
                                       initialvalue=10240,
                                       minvalue=1024,
                                       maxvalue=1048576)
        if not size:
            return

        filename = filedialog.asksaveasfilename(
            title="Сохранить образ как",
            defaultextension=".fs",
            filetypes=[("Файлы ФС", "*.fs"), ("Все файлы", "*.*")]
        )

        if filename:
            try:
                success = self.fs.create_image(size, filename)
                if success:
                    self.fs_info_label.config(
                        text=f"ФС: {os.path.basename(filename)} ({size} кластеров)")
                    self.update_path_display()
                    self.refresh_list()
                    self.update_status(f"Образ создан: {filename}")
                    messagebox.showinfo("Успех", "Образ файловой системы создан")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать образ: {str(e)}")

    def mount_fs(self):
        filename = filedialog.askopenfilename(
            title="Выберите образ файловой системы",
            filetypes=[("Файлы ФС", "*.fs"), ("Все файлы", "*.*")]
        )

        if filename and self.fs.mount(filename):
            self.fs_info_label.config(
                text=f"ФС: {os.path.basename(filename)} ({self.fs.total_clusters} кластеров)")
            self.update_path_display()
            self.refresh_list()
            self.update_status(f"ФС смонтирована: {filename}")
        else:
            messagebox.showerror("Ошибка", "Не удалось смонтировать файловую систему")

    def refresh_list(self):
        if not self.fs.filename:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            entries = self.fs.read_dir()

            for entry in entries:
                if entry['name'] in ('.', '..'):
                    continue

                item_type = "📁 Каталог" if entry['is_dir'] else "📄 Файл"
                size = entry['size'] if not entry['is_dir'] else f"{entry['num_entries']} зап."
                clusters_info = f"{entry['start_cluster']}-{entry['end_cluster']}"
                status = "Занят"

                tags = ('directory',) if entry['is_dir'] else ('file',)

                self.tree.insert('', END,
                                 values=(entry['name'], item_type, size, clusters_info, status),
                                 tags=tags)

            self.tree.tag_configure('directory', foreground='#0066cc')
            self.tree.tag_configure('file', foreground='#333333')

            self.update_status(f"Записей: {len(entries)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать каталог: {str(e)}")

    def on_item_double_click(self, event):
        """Обработка двойного клика - переход в каталог"""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        name = item['values'][0]

        if "Каталог" in item['values'][1]:
            success, message = self.fs.change_directory(name)
            if success:
                self.update_path_display()
                self.refresh_list()
                self.update_status(message)
            else:
                messagebox.showwarning("Внимание", message)
        else:
            # Для файлов - предложить копирование
            self.copy_from_fs_gui()

    def go_up(self):
        """Переход на уровень выше"""
        if self.fs.filename:
            success, message = self.fs.change_directory("..")
            if success:
                self.update_path_display()
                self.refresh_list()
                self.update_status(message)
            else:
                messagebox.showinfo("Информация", message)

    def go_root(self):
        """Переход в корневой каталог"""
        if self.fs.filename:
            success, message = self.fs.change_directory("/")
            if success:
                self.update_path_display()
                self.refresh_list()
                self.update_status(message)

    def change_directory(self):
        """Переход в каталог по пути"""
        if not self.fs.filename:
            messagebox.showwarning("Внимание", "Сначала смонтируйте файловую систему")
            return

        path = self.path_var.get().strip()
        if not path:
            return

        # Простой парсинг пути
        if path.startswith("/"):
            # Абсолютный путь - сначала идем в корень
            self.fs.change_directory("/")
            path = path[1:]

        # Разбиваем путь на компоненты
        components = [c for c in path.split("/") if c]

        for component in components:
            success, message = self.fs.change_directory(component)
            if not success:
                messagebox.showerror("Ошибка", f"Не удалось перейти в {component}: {message}")
                self.update_path_display()
                return

        self.update_path_display()
        self.refresh_list()
        self.update_status(f"Переход в {path}")

    def copy_to_fs_gui(self):
        if not self.fs.filename:
            messagebox.showwarning("Внимание", "Сначала смонтируйте файловую систему")
            return

        src_file = filedialog.askopenfilename(title="Выберите файл для копирования в ФС")
        if not src_file:
            return

        dest_name = simpledialog.askstring("Имя файла",
                                           "Введите имя файла в файловой системе:",
                                           initialvalue=os.path.basename(src_file))

        if dest_name:
            self.update_status("Копирование...")
            success, message = self.fs.copy_to_fs(src_file, dest_name)
            if success:
                messagebox.showinfo("Успех", message)
                self.refresh_list()
            else:
                messagebox.showerror("Ошибка", message)
            self.update_status("Готов")

    def copy_from_fs_gui(self):
        if not self.fs.filename:
            messagebox.showwarning("Внимание", "Сначала смонтируйте файловую систему")
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите файл для копирования")
            return

        item = self.tree.item(selection[0])
        filename = item['values'][0]

        if "Каталог" in item['values'][1]:
            messagebox.showwarning("Внимание", "Нельзя скопировать каталог")
            return

        dest_path = filedialog.asksaveasfilename(
            title="Куда сохранить файл",
            initialfile=filename
        )

        if dest_path:
            self.update_status("Копирование...")
            success, message = self.fs.copy_from_fs(filename, dest_path)
            if success:
                messagebox.showinfo("Успех", message)
                self.update_status(f"Файл скопирован: {dest_path}")
            else:
                messagebox.showerror("Ошибка", message)
            self.update_status("Готов")

    def delete_file_gui(self):
        if not self.fs.filename:
            messagebox.showwarning("Внимание", "Сначала смонтируйте файловую систему")
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите файл для удаления")
            return

        item = self.tree.item(selection[0])
        filename = item['values'][0]

        if "Каталог" in item['values'][1]:
            messagebox.showwarning("Внимание", "Для удаления каталога используйте 'Удалить каталог'")
            return

        if messagebox.askyesno("Подтверждение",
                               f"Удалить файл '{filename}'?"):
            self.update_status("Удаление...")
            success, message = self.fs.delete_item(filename, is_dir=False)
            if success:
                messagebox.showinfo("Успех", message)
                self.refresh_list()
            else:
                messagebox.showerror("Ошибка", message)
            self.update_status("Готов")

    def delete_directory_gui(self):
        if not self.fs.filename:
            messagebox.showwarning("Внимание", "Сначала смонтируйте файловую систему")
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите каталог для удаления")
            return

        item = self.tree.item(selection[0])
        dirname = item['values'][0]

        if "Каталог" not in item['values'][1]:
            messagebox.showwarning("Внимание", "Выбранный элемент не является каталогом")
            return

        if messagebox.askyesno("Подтверждение",
                               f"Удалить каталог '{dirname}' со всем содержимым?\n"
                               "Это действие нельзя отменить!"):
            self.update_status("Удаление каталога...")
            success, message = self.fs.delete_item(dirname, is_dir=True)
            if success:
                messagebox.showinfo("Успех", message)
                self.refresh_list()
            else:
                messagebox.showerror("Ошибка", message)
            self.update_status("Готов")

    def rename_gui(self):
        if not self.fs.filename:
            messagebox.showwarning("Внимание", "Сначала смонтируйте файловую систему")
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите элемент для переименования")
            return

        item = self.tree.item(selection[0])
        old_name = item['values'][0]

        new_name = simpledialog.askstring("Переименование",
                                          f"Введите новое имя для '{old_name}':",
                                          initialvalue=old_name)

        if new_name and new_name != old_name:
            success, message = self.fs.rename_item(old_name, new_name)
            if success:
                messagebox.showinfo("Успех", message)
                self.refresh_list()
            else:
                messagebox.showerror("Ошибка", message)

    def create_directory(self):
        if not self.fs.filename:
            messagebox.showwarning("Внимание", "Сначала смонтируйте файловую систему")
            return

        dir_name = simpledialog.askstring("Создание каталога",
                                          "Введите имя нового каталога:")

        if dir_name:
            self.update_status("Создание каталога...")
            success, message = self.fs.create_directory(dir_name)
            if success:
                messagebox.showinfo("Успех", message)
                self.refresh_list()
            else:
                messagebox.showerror("Ошибка", message)
            self.update_status("Готов")

    def move_item_gui(self):
        """Перемещение файла в другой каталог"""
        if not self.fs.filename:
            messagebox.showwarning("Внимание", "Сначала смонтируйте файловую систему")
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите файл для перемещения")
            return

        item = self.tree.item(selection[0])
        item_name = item['values'][0]
        is_dir = "Каталог" in item['values'][1]

        # Запрос целевого каталога
        target_dir = simpledialog.askstring("Перемещение",
                                            f"Введите путь целевого каталога для '{item_name}':\n"
                                            "(используйте '/' для корня, '..' для родителя)",
                                            initialvalue=self.fs.get_current_path())

        if not target_dir:
            return

        # Сохраняем текущий каталог
        current_cluster = self.fs.current_dir_cluster

        # Переходим в целевой каталог
        if target_dir != self.fs.get_current_path():
            if target_dir.startswith("/"):
                self.fs.change_directory("/")
                target_dir = target_dir[1:]

            components = [c for c in target_dir.split("/") if c]

            for component in components:
                success, message = self.fs.change_directory(component)
                if not success:
                    messagebox.showerror("Ошибка", f"Не удалось перейти в {component}: {message}")
                    self.fs.current_dir_cluster = current_cluster
                    self.update_path_display()
                    return

        target_cluster = self.fs.current_dir_cluster

        # Возвращаемся в исходный каталог
        self.fs.current_dir_cluster = current_cluster
        self.update_path_display()

        # Запрос нового имени (опционально)
        new_name = simpledialog.askstring("Перемещение",
                                          f"Введите новое имя для '{item_name}' (оставьте пустым для сохранения):",
                                          initialvalue=item_name)

        if new_name == "":
            new_name = item_name

        # Выполняем перемещение
        self.update_status("Перемещение...")
        success, message = self.fs.move_item(item_name, target_cluster, new_name)

        if success:
            messagebox.showinfo("Успех", message)
            self.refresh_list()
        else:
            messagebox.showerror("Ошибка", message)

        self.update_status("Готов")

    def move_directory_gui(self):
        """Перемещение каталога"""
        self.move_item_gui()  # Используем ту же логику


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == "__main__":
    root = Tk()
    app = FSGUI(root)

    # Центрирование окна
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()