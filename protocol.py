import json
import socket
import struct

HOST = "localhost"
PORT = 9999
ENCODING = "utf-8"
HEADER = struct.Struct("!I")
MAX_MESSAGE_SIZE = 10 * 1024 * 1024


class ProtocolError(Exception):
    pass


def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
    chunks = []
    received = 0
    while received < n:
        chunk = sock.recv(n - received)
        if not chunk:
            if received == 0:
                return None
            raise ProtocolError("З'єднання розірвано посеред повідомлення")
        chunks.append(chunk)
        received += len(chunk)
    return b"".join(chunks)


def send_message(sock: socket.socket, obj: dict) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode(ENCODING)
    if len(body) > MAX_MESSAGE_SIZE:
        raise ProtocolError(f"Повідомлення завелике ({len(body)} байт)")
    sock.sendall(HEADER.pack(len(body)) + body)


def recv_message(sock: socket.socket) -> dict | None:
    header = _recv_exact(sock, HEADER.size)
    if header is None:
        return None
    (length,) = HEADER.unpack(header)
    if length > MAX_MESSAGE_SIZE:
        raise ProtocolError(f"Заявлена довжина повідомлення {length} перевищує ліміт")
    body = _recv_exact(sock, length) if length else b""
    if body is None:
        raise ProtocolError("З'єднання розірвано посеред повідомлення")
    try:
        obj = json.loads(body.decode(ENCODING))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ProtocolError(f"Некоректне тіло повідомлення: {e}") from e
    if not isinstance(obj, dict):
        raise ProtocolError("Тіло повідомлення має бути JSON-об'єктом")
    return obj
