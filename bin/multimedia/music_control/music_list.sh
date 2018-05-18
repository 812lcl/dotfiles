#!/bin/sh
if [ $MUSIC_CONTROL_PATH ]
then
	music_list="$MUSIC_CONTROL_PATH/music_list"
else
	music_list=music_list
fi
awk -F/ '{print NR,$NF}' $music_list | less
