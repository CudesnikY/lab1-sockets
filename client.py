import argparse
import socket
import sys
from datetime import datetime

from protocol import HOST, PORT, ENCODING, ProtocolError, recv_message, send_message

SUPPORTED_VARIANTS = (1, 2)
VARIANT_NAMES = {
    1: "Заміна квадратних дужок на круглі",
    2: "Заміна ланцюжка пропусків на один пропуск",
}


def request(sock: socket.socket, variant: int, text: str) -> str:
    send_message(sock, {"variant": variant, "text": text})
    response = recv_message(sock)
    if response is None:
        raise ConnectionError("Сервер закрив з'єднання")
    if response.get("status") != "ok":
        raise RuntimeError(response.get("message", "Невідома помилка сервера"))
    return response["result"]


def say_goodbye(sock: socket.socket) -> None:
    try:
        send_message(sock, {"command": "quit"})
        recv_message(sock)
    except (OSError, ProtocolError):
        pass


def interactive(sock: socket.socket, variant: int) -> None:
    print("Socket Client Application")
    print("Введіть текст, '/v N' для зміни варіанту або 'quit' для виходу.")
    print(f"Поточний варіант: {variant} — {VARIANT_NAMES.get(variant, '?')}")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if line.strip() == "quit":
            break
        if not line:
            continue
        if line.startswith("/v"):
            try:
                variant = int(line[2:].strip())
                print(f"Варіант змінено на {variant} — {VARIANT_NAMES.get(variant, 'невідомий')}")
            except ValueError:
                print("Використання: /v <номер варіанту>")
            continue
        try:
            print(">> " + request(sock, variant, line))
        except RuntimeError as e:
            print(f"Помилка сервера: {e}")
    say_goodbye(sock)


def file_mode(sock: socket.socket, in_path: str, out_path: str, variants) -> None:
    try:
        with open(in_path, encoding=ENCODING) as f:
            text = f.read()
    except FileNotFoundError:
        raise SystemExit(f"Файл не знайдено: {in_path}")
    except (OSError, UnicodeDecodeError) as e:
        raise SystemExit(f"Не вдалося прочитати файл {in_path}: {e}")

    report = [
        f"Дата: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"Вхідний файл: {in_path}",
        "",
        "===== Вихідний текст =====",
        text,
    ]
    for v in variants:
        try:
            result = request(sock, v, text)
        except RuntimeError as e:
            result = f"ПОМИЛКА: {e}"
        report += ["", f"===== Варіант {v}: {VARIANT_NAMES.get(v, '?')} =====", result]
        print(f"Варіант {v} оброблено.")

    try:
        with open(out_path, "w", encoding=ENCODING) as f:
            f.write("\n".join(report) + "\n")
    except OSError as e:
        raise SystemExit(f"Не вдалося записати файл {out_path}: {e}")
    print(f"Результат збережено у {out_path}")
    say_goodbye(sock)


def main() -> None:
    parser = argparse.ArgumentParser(description="Клієнт ЛР №1 (сокети)")
    parser.add_argument("-f", "--file", help="вхідний текстовий файл")
    parser.add_argument("-o", "--output", default="output.txt", help="файл результатів")
    parser.add_argument("-v", "--variant", type=int, help="номер варіанту (1 або 2)")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    try:
        sock = socket.create_connection((args.host, args.port), timeout=10)
    except OSError as e:
        print(f"Не вдалося підключитися до сервера {args.host}:{args.port}: {e}")
        sys.exit(1)

    with sock:
        try:
            if args.file:
                variants = [args.variant] if args.variant is not None else SUPPORTED_VARIANTS
                file_mode(sock, args.file, args.output, variants)
            else:
                interactive(sock, args.variant or 1)
        except (ConnectionError, ProtocolError, socket.timeout) as e:
            print(f"Помилка зв'язку з сервером: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print()
    print("Terminate application.")


if __name__ == "__main__":
    main()
