# !/bin/bash

# Lab 1 ex.3: Using strace to monitor system calls for mkdir and touch commands, and saving the output to log files.
# chmod 777 lab1.sh
# ./lab1.sh

strace -o mkdir_log.txt mkdir -p dir/subdir
strace -o mkdir2_log.txt mkdir dir2
strace -o touch_log.txt touch dir/subdir/file.txt
strace -o touch2_log.txt touch dir2/file2.txt

strace -T -o echo_log.txt echo "Hello!"
strace -T -o cat_log.txt cat /etc/hosts
strace -T -o mkdir_log.txt mkdir test_dir
strace -T -o rmdir_log.txt rmdir test_dir
