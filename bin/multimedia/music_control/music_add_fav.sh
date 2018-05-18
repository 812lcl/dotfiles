#!/bin/sh

if [ $MUSIC_CONTROL_PATH ]
then
    file_favourite="$MUSIC_CONTROL_PATH/favourite"
else
    file_favourite="favourite"
fi

if [ $1x != x ]
then
    grep $1 $file_favourite > /dev/null
    if [ $? != 0 ]
    then
        echo $1 >> $file_favourite
    else
        echo "$1 is exist"
    fi
else
    echo "no parameter"
fi
