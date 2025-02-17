import sys
import asyncio
from constants import *
import json
import os
"""
{
type: LOGIN
username:
password:
}
"""

class user:
    def __init__(self = None, username=None):
        self.username = username
        self.status = FREE
        self.group_id = None
        self.peer = None


usr = user()

def clear_screen():
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For Linux/macOS
    else:
        os.system('clear')


async def write_messages(writer):
    msg = {}
    while usr.status == IN_PVT:
        message = await asyncio.to_thread(sys.stdin.readline)

        if usr.status == FREE:
            break
        if message.strip() == 'QUIT':
            msg_to_send = {'type': DISCONNECT}
            msg_string = json.dumps(msg_to_send)
            msg_string += '\n'
            msg_bytes = msg_string.encode()
            break

        msg['type'] = CHAT
        msg['message'] = message
        msg_string = json.dumps(msg)
        msg_string += '\n'
        msg_bytes = msg_string.encode()
        writer.write(msg_bytes)
        await writer.drain()
    print('Quitting...')

async def write_grp_messages(writer):
    msg = {'group_id': usr.group_id}
    while usr.status == IN_GRP:
        message = await asyncio.to_thread(sys.stdin.readline)

        if usr.status == FREE:
            break
        if message.strip() == 'QUIT':
            msg_to_send = {'type': DISCONNECT}
            msg_string = json.dumps(msg_to_send)
            msg_string += '\n'
            msg_bytes = msg_string.encode()
            break

        msg['type'] = GROUP_CHAT
        msg['message'] = message
        # msg['from'] = 
        msg['group_id'] = usr.group_id
        msg_string = json.dumps(msg)
        msg_string += '\n'
        msg_bytes = msg_string.encode()
        writer.write(msg_bytes)
        await writer.drain()
    print('Quitting...')


async def read_messages(reader, writer):
    while True:
        msg = {}
        result_bytes = await reader.readline()
        response = result_bytes.decode()
        msg = json.loads(response)
        print(msg)
        service_type = msg['type']
        if service_type ==  CHAT:
            await asyncio.to_thread(sys.stdout.write, f'{msg["from"]}: {msg["message"]}')
        elif service_type ==  CHAT_REQUEST:
            if usr.status == IN_PVT or usr.status == IN_GRP:
                s = json.dumps({'type': REQ_DEN})
                s += '\n'
                writer.write(s.encode())
                await writer.drain()
            else :
                print(f'{msg["from"]} wants to chat with you. Do you accept? (yes/no)')
                choice = input()
                if choice == 'yes':
                    s = json.dumps({'type': REQ_ACC, "to": msg["from"], "from": usr.username})
                    s += '\n'
                    print(s)
                    usr.status = IN_PVT
                    writer.write(s.encode())
                    await writer.drain()
                else:
                    s = json.dumps({'type': REQ_DEN, "to": msg["from"], "from": usr.username})
                    s += '\n'
                    print(s)
                    writer.write(s.encode())
                    await writer.drain()
        
        
        elif service_type == GROUP_REQ:
            if usr.status == IN_PVT or usr.status == IN_GRP:
                s = json.dumps({'type': REQ_DEN})
                s += '\n'
                writer.write(s.encode())
                await writer.drain()
            else :
                print(f'{msg["from"]} wants to chat with you. Do you accept? (yes/no)')
                choice = input()
                if choice == 'yes':
                    s = json.dumps({'type': GROUP_REQ_ACC, "to": msg["from"], "from": usr.username, 'group_id': msg['group_id']})
                    s += '\n'
                    print(s)
                    usr.status = IN_GRP
                    usr.group_id = msg['group_id']
                    writer.write(s.encode())
                    await writer.drain()
                else:
                    s = json.dumps({'type': GROUP_REQ_DEN, "to": msg["from"], "from": usr.username})
                    s += '\n'
                    print(s)
                    writer.write(s.encode())
                    await writer.drain()
        elif service_type == GROUP_REQ_ACC:
            print(msg['message'])
        elif service_type == GROUP_CHAT:
            print("HEHE")
            await asyncio.to_thread(sys.stdout.write, f'{msg["from"]}: {msg["message"]}')
        elif service_type == CHAT_OK:
            print('Chat request accepted.')
            usr.status = IN_PVT     
        elif service_type == DISCONNECT:
            print('Quitting...')
            usr.status = FREE
        elif service_type == REQ_ACC:
            print('Request accepted.')
            usr.status = IN_PVT
        else:
            print('Invalid message type.')


 


def display_menu():
    print("Welcome to my Chat Server")
    print("1. New User?")
    print("2. Existing User?")
    print("3. Quit")
    try:
        choice = int(input("Enter your choice: "))
        return choice
    except ValueError:
        print("Invalid choice. Please enter a number.")
        return 0

async def sign_up(reader, writer):
    data = {}
    data['type'] = SIGNUP
    data['username'] = input('Enter username: ')
    data['password'] = input('Enter password: ')
    msg = json.dumps(data)
    print(msg)
    msg += '\n'
    writer.write(msg.encode())
    await writer.drain()


    response = await reader.readline()
    response = json.loads(response.decode())
    print(response)
    if response['status'] == OK:
        print('Signup successful.')
        usr.username = data['username']
        return True
    else:
        print(response['message'])
        return False


async def login(reader, writer):
    data = {}
    data['type'] = LOGIN
    data['username'] = input('Enter username: ')
    data['password'] = input('Enter password: ')
    msg = json.dumps(data)
    msg += '\n'
    writer.write(msg.encode())
    await writer.drain()

    response = await reader.readline()
    response = json.loads(response.decode())
    print(response)
    if response['status'] == OK:
        print('Login successful.')
        usr.username = data['username']
        return True
    else:
        print(response['message'])
        return False


async def choose_service(reader, writer):
    print("1. Send Chat Request")
    print("2. Create a group")
    print("3. Quit")
    try:
        choice = await asyncio.to_thread(sys.stdin.readline)
        choice = int(choice)
        return choice
    except:
        return 0

async def send_chat_request(reader, writer, read_task):
    usr.status = REQUESTING
    data = {}
    data['type'] = CHAT_REQUEST
    data['username'] = input('Enter username: ')
    msg = json.dumps(data)
    msg += '\n'
    writer.write(msg.encode())
    await writer.drain()


async def send_group_creation_request(reader, writer):
    data = {}
    data['type'] = GROUP_REQ
    usr.status = IN_GRP
    data['group_id'] = input('Enter group name: ')
    data['users'] = input('Enter usernames separated by comma: ').split(',')
    data['from'] = usr.username
    usr.group_id  = data['group_id']
    msg = json.dumps(data)
    msg += '\n'
    writer.write(msg.encode())
    await writer.drain()

async def initiate_private_chat(reader, writer):
    clear_screen()
    usr.status = IN_PVT
    await write_messages(writer)

async def initiate_group_chat(reader, writer):
    clear_screen()
    usr.status = IN_GRP
    await write_grp_messages(writer)
async def main():
    server_address, server_port = '127.0.0.1', 8888
    print(f'Connecting to {server_address}:{server_port}...')
    reader, writer = await asyncio.open_connection(server_address, server_port)
    print('Connected.')
    ch = display_menu()
    while True:
        if ch == 1:
            if await sign_up(reader, writer):
                break

        elif ch == 2:
            if await login(reader, writer):
                break
        elif ch == 3:
            exit(0)
        ch = display_menu()
    print("Authentication part successfull")

    read_task = asyncio.create_task(read_messages(reader, writer))
    while usr.status != IN_PVT or usr.status != IN_GRP:
        if usr.status == IN_PVT:
            print("HI1")
            await initiate_private_chat(reader, writer)
        elif usr.status == IN_GRP:
            await initiate_group_chat(reader, writer)
        ch = await choose_service(reader, writer)
        if ch == 1:
            if await send_chat_request(reader, writer, read_task):
                
                break
        elif ch == 3:
            exit(0)
        elif ch == 2:
            await send_group_creation_request(reader, writer)
        
        
        
        else:
            continue
    if usr.status == IN_PVT:
        print("HI2")
        await initiate_private_chat(reader, writer)
    elif usr.status == IN_GRP:
        await initiate_group_chat(reader, writer)

        
    read_task.cancel()

    
    print('Disconnecting from server...')
    writer.close()
    await writer.wait_closed()
    print('Done.')
 

asyncio.run(main())