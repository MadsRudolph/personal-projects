CC      = gcc
CFLAGS  = -O2 -Wall
LDFLAGS = -lm
SRCS    = mfkey32.c crapto1.c crypto1.c
TARGET  = mfkey32.exe

all: $(TARGET)

$(TARGET): $(SRCS) crapto1.h parity.h
	$(CC) $(CFLAGS) -o $@ $(SRCS) $(LDFLAGS)

clean:
	rm -f $(TARGET)

.PHONY: all clean
