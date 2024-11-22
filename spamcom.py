import asyncio
import os
import json
from datetime import datetime, timedelta
from pystyle import *
from telethon.sync import TelegramClient
from telethon.events import NewMessage
from telethon.tl.functions.channels import LeaveChannelRequest

# Archivos JSON para almacenamiento
EXONERATED_FILE = "exonerated_groups.json"
PROGRESS_FILE = "progress.json"
INTERACTED_USERS_FILE = "interacted_users.json"
NEW_USERS_FILE = "new_users.json"
LAST_SERVICES_REQUEST_FILE = "last_services_request.json"

# Variables globales
exonerated_groups = set()
current_message_index = 0
interacted_users = set()
new_users = {}
last_services_request = {}
start_time = datetime.now()
cycles_completed = 0
messages_sent = 0

# Credenciales fijas
API_ID = 9161657
API_HASH = "400dafb52292ea01a8cf1e5c1756a96a"
PHONE_NUMBER = "+51981119038"

# Función para limpiar la consola
def cls():
    os.system("cls" if os.name == "nt" else "clear")

# Cargar datos desde archivos JSON
def load_json(filename, default_value):
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return default_value

def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file)

# Inicializar datos
exonerated_groups = set(load_json(EXONERATED_FILE, []))
current_message_index = load_json(PROGRESS_FILE, {}).get("current_message_index", 0)
interacted_users = set(load_json(INTERACTED_USERS_FILE, []))
new_users = load_json(NEW_USERS_FILE, {})
last_services_request = load_json(LAST_SERVICES_REQUEST_FILE, {})

async def send_welcome_message(client, user_id, responded_message=None):
    """
    Envía un mensaje de bienvenida único a un nuevo usuario y reenvía los mensajes del bot.
    """
    if user_id in new_users:
        last_interaction = datetime.fromisoformat(new_users[user_id])
        if datetime.now() - last_interaction < timedelta(weeks=1):
            return

    new_users[user_id] = datetime.now().isoformat()
    save_json(NEW_USERS_FILE, new_users)

    welcome_message = (
        "¡Hola! 😊\n\n"
        "Soy el administrador oficial de **PerúAyuda**. Trabajo exclusivamente con canales legales "
        "y soy el único responsable de las cuentas:\n"
        "- Canal de Arte: @Asteriscomedits\n"
        "- Canal de Sistemas: @Asteriscomsistem\n\n"
        "Estoy aquí para ayudarte con cualquiera de nuestros servicios. A continuación, te muestro "
        "un resumen de lo que ofrecemos. Por favor, revisa los mensajes y dime en cuál estás interesado. "
        "¡Estaré encantado de ayudarte!"
    )
    await client.send_message(user_id, welcome_message)

    # Reenviar los mensajes del "spam bot"
    spam_messages = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group and dialog.name == 'spam bot':
            async for message in client.iter_messages(dialog, limit=None):
                if message.text:
                    spam_messages.append(message)

    for spam_message in spam_messages:
        await client.send_message(user_id, spam_message)
        await asyncio.sleep(4)

    # Reenviar el mensaje específico al que respondió (si aplica)
    if responded_message:
        response_message = (
            f"Veo que respondiste a este post:\n\n"
            f"{responded_message.text}\n\n"
            f"¿Estás interesado en este servicio? Puedes escribirme con total confianza "
            f"para resolver cualquier duda. ¡Estoy aquí para ayudarte!"
        )
        await client.send_message(user_id, response_message)

async def send_services(client, user_id):
    """
    Envía los servicios disponibles al usuario si no se le ha enviado ya en el día.
    """
    global last_services_request

    # Verificar la última vez que el usuario solicitó servicios
    if user_id in last_services_request:
        last_request_date = datetime.fromisoformat(last_services_request[user_id])
        if datetime.now() - last_request_date < timedelta(days=1):
            await client.send_message(
                user_id,
                "Hola 😊, ya te envié los servicios hoy. Podrás volver a solicitarlos mañana. "
                "¡Gracias por tu interés!"
            )
            return

    # Registrar la solicitud de servicios
    last_services_request[user_id] = datetime.now().isoformat()
    save_json(LAST_SERVICES_REQUEST_FILE, last_services_request)

    # Enviar los servicios disponibles
    message = (
        "Estos son los servicios que tengo actualmente disponibles. ¡Siempre los estoy actualizando! 😊\n\n"
        "Por favor, revisa la lista y dime si estás interesado en alguno. Si es así, "
        "espera que ya me conecto para responderte de inmediato."
    )
    await client.send_message(user_id, message)

    # Reenviar los mensajes del "spam bot"
    spam_messages = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group and dialog.name == 'spam bot':
            async for message in client.iter_messages(dialog, limit=None):
                if message.text:
                    spam_messages.append(message)

    for spam_message in spam_messages:
        await client.send_message(user_id, spam_message)
        await asyncio.sleep(4)

async def handle_new_message(client, event):
    """
    Maneja mensajes nuevos, incluyendo el comando '/servicios'.
    """
    global new_users
    user_id = event.sender_id

    if event.is_private:
        # Verificar si el mensaje es el comando '/servicios'
        if event.text == "/servicios":
            await send_services(client, user_id)
        else:
            # Saludo personalizado si es un mensaje normal
            if user_id not in new_users or datetime.now() - datetime.fromisoformat(new_users.get(user_id, "1970-01-01")) > timedelta(days=1):
                new_users[user_id] = datetime.now().isoformat()
                save_json(NEW_USERS_FILE, new_users)
                await client.send_message(
                    user_id,
                    "¡Hola de vuelta! 😊\n\n"
                    "¿Quieres saber lo que tengo disponible? Escribe /servicios y te enviaré toda la información."
                )

async def send_messages_to_groups(client):
    """
    Enviar mensajes del "spam bot" a los grupos en ciclos.
    También elimina grupos donde no se pueden enviar mensajes.
    """
    global current_message_index, cycles_completed, messages_sent
    group_ids = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group and dialog.name != 'spam bot':
            group_ids.append(dialog)

    message_list = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group and dialog.name == 'spam bot':
            async for message in client.iter_messages(dialog, limit=None):
                if message.text:
                    message_list.append(message)

    if not message_list:
        Write.Print("\nNo messages found in 'spam bot' group.", Colors.red, interval=0)
        return

    while True:
        try:
            current_message = message_list[current_message_index]
            for dialog in group_ids:
                if dialog.name in exonerated_groups:
                    continue
                try:
                    await client.forward_messages(dialog.id, messages=[current_message])
                    messages_sent += 1
                    Write.Print(f"Message sent to {dialog.name}: {current_message.text[:50]}...", Colors.green)
                    await asyncio.sleep(4)
                except Exception as e:
                    # Si no se puede enviar mensajes, salir del grupo
                    if "not enough rights" in str(e).lower() or "you cannot send messages" in str(e).lower():
                        await client(LeaveChannelRequest(dialog))
                        Write.Print(f"Left group {dialog.name} due to insufficient rights.", Colors.yellow)
                    else:
                        Write.Print(f"Failed to send message to {dialog.name}: {str(e)}", Colors.red)

            current_message_index = (current_message_index + 1) % len(message_list)
            save_json(PROGRESS_FILE, {"current_message_index": current_message_index})
            cycles_completed += 1
            await asyncio.sleep(300)

        except ConnectionError:
            Write.Print("\nInternet connection lost. Retrying in 10 seconds...", Colors.red, interval=0)
            await asyncio.sleep(10)

async def main():
    cls()
    Write.Print("Starting bot with refined handling of commands...", Colors.green, interval=0)

    async with TelegramClient("session", API_ID, API_HASH) as client:
        @client.on(NewMessage(incoming=True))
        async def handle_event(event):
            await handle_new_message(client, event)

        await send_messages_to_groups(client)

asyncio.run(main())
