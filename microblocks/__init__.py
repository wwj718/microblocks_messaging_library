# John Maloney, October 2022
# Revised by Wenjie Wu, October 2022

__version__ = "0.5.0"

import uuid
import threading

import serial

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_ble.uuid import VendorUUID
from adafruit_ble.characteristics.stream import StreamOut, StreamIn


class MicroBlocksBase:

    def __del__(self):
        self.disconnect()

    def _generate_broadcast_message(self, aString):
        if type(aString) != str:
            raise TypeError("must be string")
        utf8 = aString.encode("utf-8")
        length = len(utf8) + 1
        bytes = (
            bytearray([251, 27, 0, length % 256, int(length / 256)]) + utf8 + b"\xfe"
        )
        return bytes

    def _decode_broadcast_message(self, data):
        result = []
        if data:
            self._buffer = self._buffer + data
            for msgBytes in self._match(27):
                result.append(msgBytes[4:].decode("utf-8").replace("\x00", ""))
        if result == []:
            return None
        else:
            return "".join(result)

    def _match(self, filter="*"):
        buf = self._buffer
        result = []
        bytesRemaining = None
        cmd = None
        msgLen = None
        end = None
        length = len(buf)
        i = 0
        while True:
            while not ((i >= length) or (buf[i] == 250) or (buf[i] == 251)):
                i += 1  # skip to start of next message
            bytesRemaining = length - i
            if bytesRemaining < 1:  # nothing to process
                self._buffer = buf[i:]
                return result
            cmd = buf[i]
            if (cmd == 250) and (bytesRemaining >= 3):  # short message (3 bytes)
                if (filter == "*") or (filter == buf[i + 1]):
                    result.append(buf[i : i + 3])
                i += 3
            elif (cmd == 251) and (bytesRemaining >= 5):  # long message (>= 5 bytes)
                msgLen = (256 * buf[i + 4]) + buf[i + 3]
                end = i + 5 + msgLen
                if end > length:  # long message is not yet complete
                    self._buffer = buf[i:]
                    return result
                if (filter == "*") or (filter == buf[i + 1]):
                    result.append(buf[i:end])
                i = end
            else:
                self._buffer = buf[i:]
                return result

    def send(self, aString):
        self.sendBroadcast(aString)

    def receive(self):
        return self.receiveBroadcasts()

    def _processReceiveBroadcasts(self):
        while True:
            message = self.receiveBroadcasts()
            if callable(self.on_message):
                self.on_message(message)

    def loopForever(self):
        # blocking
        # self.on_message = on_message
        self._processReceiveBroadcasts()

    def loopStart(self):
        # non-blocking
        # https://stackoverflow.com/questions/70625801/threading-reading-a-serial-port-in-python-with-a-gui
        thread = threading.Thread(target=self._processReceiveBroadcasts, args=())
        thread.start()


class MicroblocksSerialMessage(MicroBlocksBase):
    def __init__(self, port=None, verbose=False):
        self._buffer = bytearray()
        self._verbose = verbose  # verbose: Print various debugging information
        self.ser = None
        self.on_message = None  # paho style:  https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php

        if port:
            self.connect(port)

    def connect(self, port):
        self.ser = serial.Serial(port, 115200)

    def disconnect(self):
        self.ser.close()

    def sendBroadcast(self, aString):
        bytes = self._generate_broadcast_message(aString)
        self.ser.write(bytes)

    def receiveBroadcasts(self):
        data = self.ser.read()
        return self._decode_broadcast_message(data)


# ref: https://github.com/adafruit/Adafruit_CircuitPython_BLE/blob/744933f3061ce1d4007cb738737c66f19ebfcd27/examples/ble_uart_echo_client.py


class MicroBlocksIDEService(UARTService):
    """
    Provide UART-like(Nordic NUS service) functionality via the MicroBlocks IDE service.
    """

    uuid = VendorUUID("BB37A001-B922-4018-8E74-E14824B3A638")
    _server_tx = StreamOut(
        uuid=VendorUUID("BB37A003-B922-4018-8E74-E14824B3A638"),
        timeout=1.0,
        buffer_size=64,
    )
    _server_rx = StreamIn(
        uuid=VendorUUID("BB37A002-B922-4018-8E74-E14824B3A638"),
        timeout=1.0,
        buffer_size=64,
    )


class MicroblocksBLEMessage(MicroBlocksBase):
    """
    only supports connecting to one device
    todo: supports connecting multiple devices
    """

    def __init__(self, device_name=None, verbose=False):
        self._ble = BLERadio()
        self.connection = None
        self._buffer = bytearray()
        self._verbose = verbose  # verbose: Print various debugging information
        self.on_message = None  # paho style:  https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php

        if device_name:
            self.connect(device_name)

    def connect(self, device_name, timeout=3):
        # MicroBlocks KCY
        # assert len(self._ble.connections) == 0
        for advertisement in self._ble.start_scan(
            ProvideServicesAdvertisement, timeout=timeout
        ):  # timeout=1
            # if MicroBlocksIDEService not in advertisement.services:
            if MicroBlocksIDEService in advertisement.services:
                if device_name == advertisement.complete_name:
                    self.connection = self._ble.connect(advertisement)
                    print(f"{advertisement.complete_name} is connected")
                    break

    def discover(self, timeout=3):
        found_devices = set()
        for advertisement in self._ble.start_scan(
            ProvideServicesAdvertisement, timeout=timeout
        ):
            if MicroBlocksIDEService in advertisement.services:
                if advertisement.complete_name not in found_devices:
                    print(advertisement.complete_name)
                    found_devices.add(advertisement.complete_name)
                    # from IPython import embed; embed()
        return list(found_devices)

    def disconnect(self):
        pass
        # print("connected:", self.connection.connected)
        
        '''
        if self.connection:
            self.connection.disconnect()
        else:
            raise ValueError("Device not connected.")
        '''

    def sendBroadcast(self, aString):
        """
        if len(self._ble.connections) == 0:
            raise ValueError(f"Device not connected.")
        for connection in self._ble.connections:
            bytes = self._generate_broadcast_message(aString)
            # from IPython import embed; embed()
            uart = connection[MicroBlocksIDEService]
            uart.write(bytes)
        """
        if self.connection.connected:
            bytes = self._generate_broadcast_message(aString)
            self.connection[MicroBlocksIDEService].write(bytes)
        else:
            raise ValueError("Device not connected.")

    def receiveBroadcasts(self):
        """
        if len(self._ble.connections) == 0:
            raise ValueError(f"Device not connected.")
        assert len(self._ble.connections) == 1
        uart = self._ble.connections[0][MicroBlocksIDEService]
        # data = self.ser.read() # 从 buffer 里读取
        data = uart.read(4)
        """
        if self.connection.connected:
            data = self.connection[MicroBlocksIDEService].read(4)
            return self._decode_broadcast_message(data)
        else:
            raise ValueError("Device not connected.")

    def command(self, functionName, parameterList, callType="call"):
        assert type(parameterList) == list
        msgID = f"python-{uuid.uuid4().hex[:8]}"
        parameterList = [f'"{i}"' if type(i) == str else i for i in parameterList]
        msg = [callType, msgID, functionName] + parameterList
        msg_string = ",".join([str(i) for i in msg])
        # print("msg_string:", msg_string)
        self.sendBroadcast(msg_string)

    def debug(self):
        from IPython import embed; embed()
        pass
        # self._ble.connections

SerialMessage = MicroblocksSerialMessage
Message = MicroblocksBLEMessage
