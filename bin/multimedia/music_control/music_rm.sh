#!/bin/sh
if [ $MUSIC_CONTROL_PATH ]
then
    music_list="$MUSIC_CONTROL_PATH/music_list"
else
    music_list=music_list
fi

if [ $1x != x ]
then
    rm -i `grep "$1" $music_list`
else
    echo "no parameter"
fi
