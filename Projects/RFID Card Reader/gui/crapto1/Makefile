CC      = gcc
CFLAGS  = -O2 -Wall
LDFLAGS = -lm
COMMON  = crapto1.c crypto1.c

all: mfkey32.exe nested.exe

mfkey32.exe: mfkey32.c $(COMMON) crapto1.h parity.h
	$(CC) $(CFLAGS) -o $@ mfkey32.c $(COMMON) $(LDFLAGS)

nested.exe: nested.c $(COMMON) crapto1.h parity.h
	$(CC) $(CFLAGS) -o $@ nested.c $(COMMON) $(LDFLAGS)

clean:
	rm -f mfkey32.exe nested.exe

.PHONY: all clean
