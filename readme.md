# readme

MicroBlocks and Python Communication with Messages.

# Install

```bash
# Python3
python -m pip install microblocks_messaging_library
```

# Usage

```python
import time
from microblocks_messaging_library import MicroblocksMessage

m = MicroblocksMessage()
m.connect('/dev/tty.usbmodem1402') # replace the string with micro:bit port

# broadcast message from Python to MicroBlocks
m.sendBroadcast('happy')
time.sleep(1)
m.sendBroadcast('sad')

# receive broadcasts from MicroBlocks
while True:
    message = m.receiveBroadcasts()
    print(message)
```

Work with the MicroBlocks code (you can save this PNG file, then drag it into MicroBlocks to load the scripts):

![](./allScripts147900.png)

## MicroBlocks interoperability
- [MicroBlocks and Snap! Communication with Messages](https://wiki.microblocks.fun/snap/microblocks_snap_messaging)
- [Microblocks Serial Protocol (version 2.09)](https://bitbucket.org/john_maloney/smallvm/src/master/misc/SERIAL_PROTOCOL.md)