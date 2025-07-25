from __future__ import annotations
from cts602 import CTS602
from flask import Flask, request, jsonify
import socket

# Serial port name (e.g., "/dev/ttyUSB0")
# Can be obtained from 'dmesg | grep "ch341-uart converter now attached to"'
PORT = str("/dev/ttyUSB0")

# Slave address of the device
ADDRESS = 30

app = Flask(__name__)
cts602 = CTS602(portname=PORT, address=ADDRESS)


def parse_function_code(input: str | None) -> int:
    # Parse and validate the function code
    try:
        function_code = int(input)
    except TypeError:
        raise ValueError("Missing function code")
    except ValueError:
        raise ValueError("Cannot parse function code as integer")
    if function_code not in (3, 4, 16):
        raise ValueError("Function code not 3, 4, or 16")
    return function_code


def parse_address(input: str | None) -> int:
    # Parse and validate the address
    try:
        address = int(input)
    except TypeError:
        raise ValueError("Missing address")
    except ValueError:
        raise ValueError("Cannot parse address as integer")
    if address not in range(5001):
        raise ValueError("Address not in range <0; 5000>")
    return address


def parse_value(input: str | None, function_code: int) -> int | float | None:
    # Parse and validate the value based on the function code
    try:
        value_int = int(input)
        value_float = float(input)
    except TypeError:
        if function_code == 16:
            raise ValueError("Missing value for function code 16")
        else:
            return None
    except ValueError:
        raise ValueError("Cannot parse value as a number")

    value = value_int if value_int == value_float else value_float

    if function_code != 16 and value is not None:
        raise ValueError("Value is only allowed for function code 16")

    if value not in range(65536):
        raise ValueError("Value not in range <0; 65535>")

    return value


def parse_signed(input: str | None) -> bool:
    # Parse and validate the signed flag
    if input is None:
        return False
    elif input.lower() in ("true", "1"):
        return True
    elif input.lower() in ("false", "0"):
        return False
    else:
        raise ValueError("Cannot parse signed as boolean")


def process_single_command(command: dict[str, str | None]):
    """Process a single command and send it to the device.
    Raises:
        ValueError: If there is an error in the command parameters.
        ConnectionError: If there is a connection issue with the device.
    """
    function_code = parse_function_code(command.get("function_code"))
    address = parse_address(command.get("address"))
    value = parse_value(command.get("value"), function_code)
    signed = parse_signed(command.get("signed"))

    return cts602.send_command(function_code, address, value, signed)


@app.route("/single_command", methods=["POST"])
def handle_single_command():
    # Extract the command parameters from the HTTP request
    function_code = request.form.get("function_code")
    address = request.form.get("address")
    value = request.form.get("value")
    signed = request.form.get("signed")

    # Prepare the command dictionary
    command = {
        "function_code": function_code,
        "address": address,
        "value": value,
        "signed": signed,
    }

    # Process the single command
    try:
        result = process_single_command(command)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"result": result}), 200


@app.route("/batch_command", methods=["POST"])
def handle_batch_command():
    # Process a batch of commands
    commands = request.get_json()

    responses = []
    for command in commands:
        try:
            response = process_single_command(command)
        except (ValueError, ConnectionError) as e:
            response = {"error": str(e)}
        else:
            response = {"result": response}
        responses.append(response)

    # Send the responses over HTTP
    return jsonify(responses), 200


@app.route("/test", methods=["POST"])
def handle_test():
    # Perform a test of the Modbus communication
    if cts602.test():
        return jsonify({"result": "Modbus communication test passed."}), 200
    else:
        return (
            jsonify(
                {
                    "error": """Modbus communication test failed.
                    This means a cable is unplugged, the AC unit is powered down,
                    a communication error happened, or the AC firmware has changed."""
                }
            ),
            500,
        )


@app.route('/wake_desktop', methods=['POST'])
def wake_desktop():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto( b'\xff\xff\xff\xff\xff\xff' + b'\x18\x31\xbf\x25\x26\xb1' * 16, ('10.0.0.255', 9))
        return jsonify({'message': 'Magic packet sent.'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.errorhandler(404)
def page_not_found(error):
    return "Ahoj, ja jsem tvoje klimatizace. Pouzij appku prosim.", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
