1. Найти способ определить количество запущенных задач на компьютере при помощи графического интерфейса и интерфейса командной строки
![image](https://github.com/IKdotShark/Operating-systems/blob/main/lab1/Pasted%20image%2020250911140204.png?raw=true)
2. Определить, за какие ресурсы приходится конкурировать таким программам, как:
	a.	MS Word и Блокнот
	b.Браузер и почтовый клиент
	c.	Менеджер файлов и браузер

| Название программы        | Конкурируемые ресурсы              |
| ------------------------- | ---------------------------------- |
| MS Word & Блокнот         | CPU, RAM,  дисковой ввод/вывод     |
| Браузер & Почтовый клиент | RAM, CPU, NIC (Сетевая карта)      |
| Менеджер файлов & Браузер | CPU, RAM, GPU, дисковой ввод/вывод |
3. `mkdir` and `touch`
`strace`
`strace -o mkdir_log.txt mkdir -p dir/subdir`
в логах все есть
4.
```bash
strace  -T -o echo_log.txt echo "Hello!"
strace -T -o cat_log.txt cat /etc/hosts
strace -T -o mkdir_log.txt mkdir test_dir
strace -T -o rmdir_log.txt rmdir test_dir
```
