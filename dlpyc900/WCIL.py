import serial
import struct
import time
from typing import Tuple, Optional

class RS485Device:
    def __init__(self, port: str, baudrate: int = 38400, timeout: float = 1.0):
        """Initialize RS485 device with serial port settings."""
        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )
        self.frame_header = bytes([0x55, 0xAA])
        self.frame_tail = bytes([0xDA, 0xC3])
        self.address = 0x01

    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate checksum (sum of bytes from function code to reserved byte)."""
        return sum(data) & 0xFF

    def _build_frame(self, func_code: int, data: bytes) -> bytes:
        """Build a complete frame with header, address, data, checksum, and tail."""
        frame = self.frame_header + bytes([self.address, func_code]) + data
        checksum = self._calculate_checksum(frame[3:-2])  # From func_code to reserved byte
        return frame + bytes([checksum]) + self.frame_tail

    def _validate_response(self, response: bytes, expected_func_code: int) -> bool:
        """Validate the response frame."""
        if len(response) < 8:
            return False
        if response[:2] != self.frame_header or response[-2:] != self.frame_tail:
            return False
        if response[2] != self.address or response[3] != expected_func_code:
            return False
        checksum = self._calculate_checksum(response[3:-3])
        return checksum == response[-3]

    def _send_and_receive(self, frame: bytes, expected_func_code: int) -> Optional[bytes]:
        """Send frame and receive response."""
        try:
            self.serial.write(frame)
            time.sleep(0.05)  # Small delay for device response
            response = self.serial.read(10)  # Adjust based on expected response length
            if self._validate_response(response, expected_func_code):
                return response
            else:
                print("Invalid response received")
                return None
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            return None

    def reset_output(self) -> bool:
        """Function code 0x02: Reset output (turn off)."""
        data = bytes([0x01, 0x00, 0x00])  # byte0, byte1, reserved
        frame = self._build_frame(0x02, data)
        response = self._send_and_receive(frame, 0x02)
        if response and response[4:7] == data:
            print("Output reset successfully")
            return True
        print("Failed to reset output")
        return False

    def set_output_current(self, current_ma: int) -> bool:
        """Function code 0x03: Set output current (max 3500mA)."""
        if current_ma > 3500:
            print("Current exceeds 3500mA limit")
            return False
        byte0 = (current_ma >> 8) & 0xFF
        byte1 = current_ma & 0xFF
        data = bytes([byte0, byte1, 0x00])  # byte0, byte1, reserved
        frame = self._build_frame(0x03, data)
        response = self._send_and_receive(frame, 0x03)
        if response and response[4:7] == data:
            print(f"Current set to {current_ma}mA")
            return True
        print("Failed to set current or current > 3500mA")
        return False

    def get_device_status(self) -> Optional[Tuple[str, float]]:
        """Function code 0x05: Get device status and laser temperature."""
        data = bytes([0x01, 0x00, 0x00])  # byte0, byte1, reserved
        frame = self._build_frame(0x05, data)
        response = self._send_and_receive(frame, 0x05)
        if response and len(response) >= 8:
            status_byte = response[4]
            byte1, byte2 = response[5], response[6]
            temperature = (byte1 * 256 + byte2) * 0.1  # Temperature in °C

            if status_byte == 0x00:
                status = "Normal"
            elif status_byte & 0x01:
                status = "Over-temperature alarm"
            elif status_byte & 0x02:
                status = "Over-current alarm"
            elif status_byte & 0x04:
                status = "Under-current alarm"
            else:
                status = "Unknown status"

            print(f"Status: {status}, Temperature: {temperature:.1f}°C")
            return status, temperature
        print("Failed to get device status")
        return None

    def clear_fault(self) -> bool:
        """Function code 0x06: Clear fault codes."""
        data = bytes([0x01, 0x00, 0x00])  # byte0, byte1, reserved
        frame = self._build_frame(0x06, data)
        response = self._send_and_receive(frame, 0x06)
        if response and response[4:7] == data:
            print("Fault cleared successfully")
            return True
        print("Failed to clear fault")
        return False

    def close(self):
        """Close the serial port."""
        if self.serial.is_open:
            self.serial.close()
            print("Serial port closed")

# Example usage
if __name__ == "__main__":
    try:
        device = RS485Device(port="COM1")  # Replace with your serial port
        device.reset_output()
        device.set_output_current(2000)  # Set 2000mA
        device.get_device_status()
        device.clear_fault()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        device.close()