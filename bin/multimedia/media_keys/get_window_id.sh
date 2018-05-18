#!/bin/sh
if [ $1x != x ]
then
    file_window_id="$1"
else
    file_window_id='file_window_id'
fi
process_name='music_play'
process_pid=`ps -ef | grep $process_name | grep -v "grep" | awk '{print $2}'`
process_ppid=`ps lp $process_pid | awk 'NR>1{print $4}'`
process_pppid=`ps lp $process_ppid | awk 'NR>1{print $4}'`
xdotool search --pid $process_pppid > $file_window_id
window_id=`cat $file_window_id`
echo "window id: $window_id"
