#!/bin/sh
if [ $1x != x ]
then
    file_window_id="$1"
else
    file_window_id='file_window_id'
fi
if [ -f $MEDIA_KEYS_PATH/$file_window_id ]
then
    rm -f $MEDIA_KEYS_PATH/$file_window_id
else
    echo "no such file"
fi
