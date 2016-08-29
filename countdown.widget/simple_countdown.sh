#!/bin/bash
#
# Author: Jody Foo, 2013-06-04
#
# Modified version of Countdown Timer 4
# http://www.macosxtips.co.uk/geeklets/productivity/countdown-timer-4-1/

# Set $FILENAME to the file you store your countdowns in.
# Separate your countdowns using a space of a newline. Each countdown
# consists of two values, the time of the event, and the name of the event.
# Neither may contain a whitespace. Use '_' instead and use a whitespeace to
# separate time and name. See example below.
#
# yyyy-mm-dd_hh:mm countdown_title_with_no_spaces
#
# In the example above, the first pair of "m"s in the date are two digits
# that represent the month (01-12). The second pair of "m"s are two digits
# that represent the minutes (01-59).
FILENAME="/Users/yina/Dropbox/Backups/geektool/simple_countdowns.txt"

# Load countdown file and sort entries
DATES=( $(sort $FILENAME) )

# This function parses the datetime string and returns the time left
function countdown {
CURRENT=$(date +%s)
TARGET=$(date -j -f %Y-%m-%d_%H:%M $1 +%s)
LEFT=$((TARGET-CURRENT))
WEEKS=$((LEFT/604800))
DAYS=$(( (LEFT%604800)/86400))
HOURS=$(( (LEFT%86400)/3600))
MINS=$(( (LEFT%3600)/60))
SECS=$((LEFT%60))

# labels
lblWEEKS="w"
lblDAYS="d"
lblHOURS="h"
lblMINS="m"

# only weeks (+ days) left
if ( [ "$WEEKS" -gt "0" ] ) ; then
 if ( [ "$WEEKS" -lt "9" ] ) ; then
  WEEKS="0$WEEKS"
 fi
 if ( [ "$DAYS" -gt "0" ] ) ; then
  if ( [ "$DAYS" -lt "9" ] ) ; then
   DAYS="0$DAYS"
  fi
  echo $WEEKS$lblWEEKS $DAYS$lblDAYS
  return
 fi
 echo $WEEKS$lblWEEKS 00d
 return
# only days (+ hours) left
elif ( [ "$DAYS" -gt "0" ] ) ; then
 if ( [ "$DAYS" -lt "9" ] ) ; then
   DAYS="0$DAYS"
 fi
 if ( [ "$HOURS" -gt "0" ]) ; then
  if ( [ "$HOURS" -lt "9" ] ) ; then
   HOURS="0$HOURS"
  fi
  echo $DAYS$lblDAYS $HOURS$lblHOURS
  return
 fi
 echo $DAYS$lblDAYS 00h
 return
# down to only hours + (minutes) left
elif ( [ "$HOURS" -gt "0" ] ) ; then
 if ( [ "$HOURS" -lt "9" ] ) ; then
   HOURS="0$HOURS"
 fi
 if ( [ "$MINS" -gt "0" ]) ; then
  if ( [ "$MINS" -lt "9" ] ) ; then
   MINS="0$MINS"
  fi
  echo $HOURS$lblHOURS $MINS$lblMINS
  return
 fi
 echo $HOURS$lblHOURS 00m
 return
# only minutes left
elif ( [ "$MINS" -gt "0" ] ) ; then
 echo $MINS$lblMINS
 return
# If 0 minutes left it's NOW.
elif ( [ "$MINS" == "0" ] ) ;  then
 echo "NOW"
 return
fi

# otherwise the event has passed
echo "passed"
return
}

# Print message if no countdowns are available.
if [ ${#DATES[@]} == "0" ] ; then
echo "No countdowns available."
return
fi

printf "<div id="container">"

# Print time left for each countdown
#for (( i = 0 ; i < ${#DATES[@]} ; i+=2 )) ; do
for (( i = 0 ; i < 40 ; i+=2 )) ; do
# if title starts with a #, skip line
if [[ ${DATES[i]} == \#* ]] ; then
 :
else
 # title
 x=$(countdown ${DATES[i]})

 # time
 y=${DATES[i+1]}
 y=$(echo $y|sed 's/_/ /g')

 case $y in
  *C*) printf "<div style="color:green">%7s: %s</div>" "$x" "$y" ;;
  *R*) printf "<div style="color:white">%7s: %s</div>" "$x" "$y" ;;
  *W*) printf "<div style="color:white">%7s: %s</div>" "$x" "$y" ;;
  *C*) printf "<div style="color:red">%7s: %s</div>" "$x" "$y" ;;
  *L*) printf "<div style="color:brown">%7s: %s</div>" "$x" "$y" ;;
  *) printf "<div style="color:blue">%7s: %s</div>" "$x" "$y" ;;
 esac
 # switch color depending on what y is
# if ($y == "C") ; then
#   printf "<div style="color:green">%7s: %s</div>" "$x" "$y"
# else
   #printf "<div style="color:white">%7s: %s</div>" "$x" "$y"
# fi
fi
done

printf "</div>"
