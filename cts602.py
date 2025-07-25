from __future__ import annotations
import minimalmodbus


class CTS602(minimalmodbus.Instrument):
    def __init__(self, portname="/dev/ttyUSB0", address=30):
        minimalmodbus.Instrument.__init__(
            self,
            port=portname,
            slaveaddress=address,
            mode=minimalmodbus.MODE_RTU,
            close_port_after_each_call=False,
            debug=False,
        )
        self.serial.baudrate = 19200
        self.serial.bytesize = 8
        self.serial.parity = minimalmodbus.serial.PARITY_EVEN
        self.serial.stopbits = 1
        self.serial.timeout = 0.5  # seconds
        self.serial.write_timeout = 0.5  # seconds

    def test(self) -> bool:
        try:
            ret = self.read_register(
                registeraddress=0, number_of_decimals=0, functioncode=4, signed=False
            )
        except (minimalmodbus.ModbusException, minimalmodbus.serial.SerialException):
            return False
        else:
            return ret == 22

    def send_command(
        self, function_code: int, address: int, value: int | float, signed: bool
    ) -> int | float:
        """Throws: ValueError, ConnectionError"""
        try:
            if function_code == 3:
                result = self.read_register(
                    registeraddress=address,
                    number_of_decimals=0,
                    functioncode=3,
                    signed=signed,
                )
            elif function_code == 4:
                result = self.read_register(
                    registeraddress=address,
                    number_of_decimals=0,
                    functioncode=4,
                    signed=signed,
                )
            elif function_code == 16:
                self.write_register(
                    registeraddress=address,
                    value=value,
                    number_of_decimals=0,
                    functioncode=16,
                    signed=signed,
                )
                result = value

        except (minimalmodbus.ModbusException, minimalmodbus.serial.SerialException):
            raise ConnectionError("Modbus or communication error")
        except (TypeError, ValueError):
            raise ValueError("Invalid command parameters")

        return result
