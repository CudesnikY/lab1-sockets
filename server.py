import re
import socket
import sys
import threading

from protocol import HOST, PORT, ProtocolError, recv_message, send_message


def replace_brackets(text: str) -> str:
    return text.translate(str.maketrans("[]", "()"))


def collapse_spaces(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text)


HANDLERS = {
    1: replace_brackets,
    2: collapse_spaces,
}


def process_request(request: dict) -> dict:
    variant = request.get("variant")
    text = request.get("text")

    if not isinstance(variant, int) or isinstance(variant, bool):
        return {"status": "error", "message": "Поле 'variant' має бути цілим числом"}
    if variant not in HANDLERS:
        supported = ", ".join(map(str, sorted(HANDLERS)))
        return {"status": "error",
                "message": f"Варіант {variant} не підтримується (доступні: {supported})"}
    if not isinstance(text, str):
        return {"status": "error", "message": "Поле 'text' має бути рядком"}

    return {"status": "ok", "variant": variant, "result": HANDLERS[variant](text)}


def handle_client(conn: socket.socket, addr) -> None:
    print(f"[+] Підключено клієнта {addr[0]}:{addr[1]}")
    with conn:
        while True:
            try:
                request = recv_message(conn)
            except ProtocolError as e:
                print(f"[!] {addr}: помилка протоколу: {e}")
                try:
                    send_message(conn, {"status": "error", "message": str(e)})
                except OSError:
                    pass
                break
            except OSError as e:
                print(f"[!] {addr}: мережева помилка: {e}")
                break

            if request is None:
                break
            if request.get("command") == "quit":
                send_message(conn, {"status": "ok", "result": "bye"})
                break

            preview = str(request.get("text", ""))[:60].replace("\n", "\\n")
            print(f"> {addr[1]} варіант={request.get('variant')} текст='{preview}'")

            try:
                response = process_request(request)
            except Exception as e:
                response = {"status": "error", "message": f"Внутрішня помилка сервера: {e}"}

            try:
                send_message(conn, response)
            except (OSError, ProtocolError) as e:
                print(f"[!] {addr}: не вдалося надіслати відповідь: {e}")
                break
    print(f"[-] Клієнт {addr[0]}:{addr[1]} відключився")


def main() -> None:
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Некоректний номер порту: {sys.argv[1]}")
            sys.exit(1)

    print("Socket Server Application")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ss:
            ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            ss.bind((HOST, port))
            ss.listen()
            print(f"Сервер слухає {HOST}:{port}. Ctrl+C — зупинка.")
            ss.settimeout(1.0)
            while True:
                try:
                    conn, addr = ss.accept()
                except socket.timeout:
                    continue
                conn.settimeout(None)
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except OSError as e:
        print(f"Не вдалося запустити сервер: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nTerminate application.")


if __name__ == "__main__":
    main()
