import flet as ft
import sys
import time 
import os
import socket
import threading
import json

# Menambahkan jalur ke sys.path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from chatcli import ChatClient

TARGET_IP = os.getenv("SERVER_IP") or "127.0.0.1"
TARGET_PORT = os.getenv("SERVER_PORT") or "8889"
ON_WEB = os.getenv("ONWEB") or "0"

class Message():
    def __init__(self, username: str, text: str, message_type: str ="chat_message"):
        self.username = username
        self.text = text
        self.message_type = message_type

class GroupMessage():
    def __init__(self, groupname: str, username: str, text: str, message_type: str ="group_message"):
        self.groupname = groupname
        self.username = username
        self.text = text
        self.message_type = message_type

class ChatMessage(ft.Row):
    def __init__(self, message: Message):
        super().__init__()
        self.vertical_alignment = ft.CrossAxisAlignment.START
        self.controls=[
            ft.CircleAvatar(
                content=ft.Text(self.get_initials(message.username)),
                color=ft.colors.WHITE,
                bgcolor=self.get_avatar_color(message.username),
            ),
            ft.Column(
                [
                    ft.Text(message.username, weight="bold"),
                    ft.Text(message.text, selectable=True),
                ],
                tight=True,
                spacing=5,
            ),
        ]

    def get_initials(self, user_name: str):
        return user_name[:1].capitalize()

    def get_avatar_color(self, user_name: str):
        colors_lookup = [
            ft.colors.AMBER,
            ft.colors.BLUE,
            ft.colors.BROWN,
            ft.colors.CYAN,
            ft.colors.GREEN,
            ft.colors.INDIGO,
            ft.colors.LIME,
            ft.colors.ORANGE,
            ft.colors.PINK,
            ft.colors.PURPLE,
            ft.colors.RED,
            ft.colors.TEAL,
            ft.colors.YELLOW,
        ]
        return colors_lookup[hash(user_name) % len(colors_lookup)]

class GroupChatMessage(ft.Row):
    def __init__(self, message: GroupMessage):
        super().__init__()
        self.vertical_alignment = ft.CrossAxisAlignment.START
        self.controls=[
            ft.CircleAvatar(
                content=ft.Text(self.get_initials(message.groupname)),
                color=ft.colors.WHITE,
                bgcolor=self.get_avatar_color(message.groupname),
            ),
            ft.Column(
                [
                    ft.Text(message.groupname, weight="bold"),
                    ft.Text(message.text, selectable=True),
                ],
                tight=True,
                spacing=5,
            ),
        ]

    def get_initials(self, group_name: str):
        return group_name[:1].capitalize()

    def get_avatar_color(self, group_name: str):
        colors_lookup = [
            ft.colors.AMBER,
            ft.colors.BLUE,
            ft.colors.BROWN,
            ft.colors.CYAN,
            ft.colors.GREEN,
            ft.colors.INDIGO,
            ft.colors.LIME,
            ft.colors.ORANGE,
            ft.colors.PINK,
            ft.colors.PURPLE,
            ft.colors.RED,
            ft.colors.TEAL,
            ft.colors.YELLOW,
        ]
        return colors_lookup[hash(group_name) % len(colors_lookup)]


class ChatApp():
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (TARGET_IP, int(TARGET_PORT))
        try:
            self.sock.connect(self.server_address)
            print(f"Connected to server at {self.server_address}")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
        
        self.cc = ChatClient()
        self.tokenid = self.cc.tokenid
        self.username_dest = None
        self.groupname_dest = None
        self.update = None
        self.chat = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
        )
        
    def main(self, page: ft.Page):
        print("main")
        
        def on_message(message: Message):
            if message.message_type == "chat_message":
                m = ChatMessage(message)
            elif message.message_type == "login_message":
                m = ft.Text(message.text, italic=True, color=ft.colors.BLACK45, size=12)
            self.chat.controls.append(m)
            self.page.update()

        self.page = page
        self.page.title = "Chat Application"

        self.navigation_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self.on_navigation_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.icons.CHAT, label="Chats"),
                ft.NavigationBarDestination(icon=ft.icons.GROUP, label="Groups"),
                ft.NavigationBarDestination(icon=ft.icons.GROUP, label="Add Group"),
                ft.NavigationBarDestination(icon=ft.icons.GROUP, label="Add Realm"),
                ft.NavigationBarDestination(icon=ft.icons.GROUP, label="Chat Realm"),
                ft.NavigationBarDestination(icon=ft.icons.PERSON, label="Profile")
            ],
        )
        
        print("tokenid check", self.cc.tokenid)
        if self.cc.tokenid:
            print("tokenid woy", self.cc.tokenid)
            self.page.add(self.navigation_bar)
            self.page.add(self.chats_page())
        else:
            self.page.add(self.login_page())
            self.page.add(self.navigation_bar)

        self.page.pubsub.subscribe(on_message)
        self.page.update()

    def start_receiving_messages(self, inboxType="personal"):
        print("start_receiving_messages")
        def receive_messages():
            print("Thread started")
            while True:
                # if inboxType == "personal":
                response = self.cc.proses("inbox " + self.username_dest)
                print("response inbox", response)
                self.display_message(response)

                time.sleep(1)

        threading.Thread(target=receive_messages, daemon=True).start()

    def start_receiving_group_messages(self):
        print("start_receiving_group_messages")
        
        def receive_group_messages():
            print("Thread started")
            while True:
                response = self.cc.proses("group inbox " + self.groupname_dest)
                print("response group inbox", response)
                self.display_group_message(response)
                time.sleep(1)

        threading.Thread(target=receive_group_messages, daemon=True).start()
    

    def display_message(self, message):
        if message['status']:
            if message['status'] == "OK":
                # clear chat
                self.chat.controls.clear()
                for chat_message in message['messages']:
                    self.chat.controls.append(ChatMessage(Message(chat_message['msg_from'], chat_message['msg'])))
                
        self.page.update()

    def display_group_message(self, message):
        if message['status'] == "OK":
            # clear chat
            self.chat.controls.clear()
            for chat_message in message['messages']:
                self.chat.controls.append(
                    GroupChatMessage(
                        GroupMessage(self.groupname_dest, chat_message['msg_from'], chat_message['msg'])
                    )
                )
        self.page.update()

    def register_page(self):
        register = ft.Column()
        username_input = ft.TextField(label="Username")
        register.controls.append(username_input)
        email_input = ft.TextField(label="Email")
        register.controls.append(email_input)
        password_input = ft.TextField(label="Password")
        register.controls.append(password_input)
        register_button = ft.ElevatedButton(text="Register")

        register_rows = ft.Row()
        register_rows.controls.append(register_button)
        login_redirect = ft.TextButton("Already have an account? Login here.")
        register_rows.controls.append(login_redirect)
        register.controls.append(register_rows)

        def on_register_click(e):
            username = username_input.value
            password = password_input.value
            email = email_input.value
            string_send = f"register {username} {email} {password}"
            response = self.cc.proses(string_send)
            self.tokenid = self.cc.tokenid
            if self.tokenid is None:
                print("Register failed")
                return
            print(response)
            self.page.controls.clear()
            self.page.controls.append(self.navigation_bar)
            self.page.update()

        def login_page_redirect(e):
            self.page.controls.clear()
            self.page.controls.append(self.login_page())
            self.page.update()        
          
        register_button.on_click = on_register_click
        login_redirect.on_click = login_page_redirect
        return register
    
    def login_page(self):
        login = ft.Column()
        username_input = ft.TextField(label="Username")
        login.controls.append(username_input)
        password_input = ft.TextField(label="Password")
        login.controls.append(password_input)
        login_rows = ft.Row()

        login_button = ft.ElevatedButton(text="Login")
        register_redirect = ft.TextButton("Don't have an account? Register here.")
        login_rows.controls.append(login_button)
        login_rows.controls.append(register_redirect)

        login.controls.append(login_rows)

        def on_login_click(e):
            username = username_input.value
            password = password_input.value
            string_send = f"auth {username} {password}"
            response = self.cc.proses(string_send)
            self.tokenid = self.cc.tokenid
            if self.tokenid is None:
                print("Login failed")
                return
            print(response)
            self.page.controls.clear()
            self.page.controls.append(self.navigation_bar)
            self.page.update()
          
        def register_page_redirect(e):
            self.page.controls.clear()
            self.page.controls.append(self.register_page())
            self.page.update()

        login_button.on_click = on_login_click
        register_redirect.on_click = register_page_redirect
        return login

    def on_navigation_change(self, e):
        if e.control.selected_index == 0:
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.chats_page())
        elif e.control.selected_index == 1:
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.groups_page())
        elif e.control.selected_index == 2:
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.button_add_group())
        elif e.control.selected_index == 3:
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.button_add_realm())
        elif e.control.selected_index == 4:
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.inbox_realm())
        elif e.control.selected_index == 5:
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.profile_page())
        self.page.update()

    def chats_page(self):
        users = self.cc.proses("users")
        print("USERS", users)

        listuser = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
        )

        for user in list(users.keys()):
            user = users[user]
            chat_message = ChatMessage(Message(user['nama'], user['email']))
            print(user['nama'])
            container = ft.Container(
                content=chat_message,
                on_click=lambda e, username_dest=user['nama']: self.dlg_modal(e, username_dest),
            )
            listuser.controls.append(container)

        return listuser

    def inbox_realm(self):
        add_group = ft.Column()
        realm_id_input = ft.TextField(label="Realm ID")
        add_group.controls.append(realm_id_input)
        add_group_button = ft.ElevatedButton(text="get all inbox")
        
        add_group_rows = ft.Row()
        add_group_rows.controls.append(add_group_button)
        add_group.controls.append(add_group_rows)
        
        def on_add_realm_click(e):
            realm_id = realm_id_input.value
            send_string = f"inboxrealm {realm_id}"
            print(send_string)
            results = self.cc.proses(send_string)
            print("this is result", results)
            self.chat.controls.clear()
            self.page.clean()
            self.page.add(self.dlg_realm_modal(results))

        add_group_button.on_click = on_add_realm_click
        
        return add_group
    
    def dlg_realm_modal(self, messages):
        # Membuat container untuk menampung kontrol chat
        chat_container = ft.Column()
        
        print("this is messages", messages)
        for chat_message in messages:
            print('this is chat message', chat_message)
            if 'msg_from' in chat_message and 'msg' in chat_message:
                chat_container.controls.append(
                    ChatMessage(Message(chat_message['msg_from'], chat_message['msg']))
                )

        # Inisialisasi kontrol
        realm_id = ft.TextField(label="Realm ID", hint_text="Masukkan ID Realm")
        dest_user = ft.TextField(label="Destination User", hint_text="Masukkan Nama Pengguna")
        new_message = ft.TextField(label="Message", hint_text="Masukkan Pesan")

        def send_click(e):
            if not realm_id.value or not dest_user.value or not new_message.value:
                return  # Jika salah satu field kosong, tidak melakukan apapun

            send_string = f"sendrealm {realm_id.value} {dest_user.value} {new_message.value}"
            print("sendrealm", send_string)
            response = self.cc.proses(send_string)
            print("THIS IS RESPONSE", response)

            if response:  # Pastikan response tidak None
                chat_container.controls.append(
                    ChatMessage(Message(self.cc.username, new_message.value))
                )

            new_message.value = ""  # Kosongkan pesan setelah pengiriman
            realm_id.value = ""
            dest_user.value = ""
            e.page.update()  # Perbarui halaman untuk menampilkan perubahan

        # Layout untuk form input dan tombol
        input_row = ft.Row(
            controls=[
                realm_id,
                dest_user,
                new_message,
                ft.ElevatedButton("Send", on_click=send_click)
            ]
        )

        # Buat tampilan utama yang akan dikembalikan
        main_layout = ft.Column(
            controls=[
                chat_container,
                input_row,
                self.navigation_bar if hasattr(self, 'navigation_bar') and self.navigation_bar else ft.Divider()  # Tambahkan navigation_bar jika ada
            ]
        )

        return main_layout

        

    def groups_page(self):
        groups = self.cc.proses("group get")
        print("GROUPS", groups)

        list_groups = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
        )

        for group in list(groups.keys()):
            group = groups[group]
            print("TEST GROUP", group)
            group_message = GroupChatMessage(GroupMessage(group['nama'], group['nama'], group['password']))
            container = ft.Container(
                content=group_message,
                on_click=lambda e, groupname_dest=group['nama']: self.join_group_dialog(e, groupname_dest),
            )
            list_groups.controls.append(container)

        return list_groups
    
    def profile_page(self):
            user = ft.Column()
        
        # Fetch profile data
            profile = self.cc.proses("getme")
            print("User Profile:", profile)
        
        # Check if profile and userdetail are not None
            if profile and profile.get('userdetail'):
                profile_data = profile.get('userdetail').get('nama')  # Assuming 'nama' is the key for name in your profile data
                print("Profile Data: ", profile_data)
                email = profile.get('userdetail').get('email')
            
            # Check if profile_data is not None
            if profile_data:
                username = ft.Text(f"name: {profile_data}")
                email = ft.Text(f"email: {email}")
            else:
                username = ft.Text("No name available")
        
            user.controls.append(username)
            user.controls.append(email)
            
            def on_logout_click(e):
                    string_send = f"logout"
                    response = self.cc.proses(string_send)
                    self.tokenid = None
                    print(response)
                    self.page.controls.clear()
                    self.page.add(self.login_page())
                    self.page.update()
            logout_button = ft.ElevatedButton(text="Logout", on_click=on_logout_click)
            user.controls.append(logout_button)
            return user

    def dlg_modal(self, e, username_dest):
        self.username_dest = username_dest
        
        response = self.cc.proses(f"inbox {self.username_dest}")
        print("chats", response)
        
        for chat_message in response['messages']:
            self.chat.controls.append(ChatMessage(Message(chat_message['msg_from'], chat_message['msg'])))

        new_message = ft.TextField()

        def send_click(e):
            if new_message.value == "":
                return
            response = self.cc.proses(f"send {self.username_dest} {new_message.value}")
            print(response)
            self.chat.controls.append(ChatMessage(Message(self.cc.username, new_message.value)))

            new_message.value = ""
            self.page.update()

        self.page.clean()
        self.page.add(
            self.chat, ft.Row(controls=[new_message, ft.ElevatedButton("Send", on_click=send_click)])
        )
        self.page.add(self.navigation_bar)
        self.start_receiving_messages("personal")


    def join_group_dialog(self, e, groupname):
        self.groupname_dest = groupname
        
        response = self.cc.proses(f"group inbox {self.groupname_dest}")
        print("group inbox", response['messages'])
    
        for i in range(len(response['messages'])):
            print("group message", response['messages'][i])
            self.chat.controls.append(
                GroupChatMessage(
                    GroupMessage(self.groupname_dest, response['messages'][i]['msg_from'], response['messages'][i]['msg'])
                )
            )

        new_message = ft.TextField()

        def send_click(e):
            if new_message.value == "":
                return
            response = self.cc.proses(f"group send {self.groupname_dest} {new_message.value}")
            print(response)
            self.chat.controls.append(
                GroupChatMessage(
                    GroupMessage(self.groupname_dest, self.cc.username, new_message.value)
                )
            )
            new_message.value = ""
            self.page.update()

        self.page.clean()
        self.page.add(
            self.chat, ft.Row(controls=[new_message, ft.ElevatedButton("Send", on_click=send_click)])
        )
        self.page.add(self.navigation_bar)
        self.start_receiving_group_messages()

    def button_add_group(self):
        add_group = ft.Column()
        groupname_input = ft.TextField(label="Group Name")
        add_group.controls.append(groupname_input)
        password_input = ft.TextField(label="Password")
        add_group.controls.append(password_input)
        add_group_button = ft.ElevatedButton(text="Add Group")

        add_group_rows = ft.Row()
        add_group_rows.controls.append(add_group_button)
        add_group.controls.append(add_group_rows)

        def on_add_group_click(e):
            groupname = groupname_input.value
            password = password_input.value
            string_send = f"group add {groupname} {password}"
            response = self.cc.proses(string_send)
            print(response)
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.groups_page())
            self.page.update()

        add_group_button.on_click = on_add_group_click
        return add_group


    def button_add_realm(self):
        add_group = ft.Column()
        realm_id_input = ft.TextField(label="Realm ID")
        add_group.controls.append(realm_id_input)
        address_input = ft.TextField(label="Address")
        add_group.controls.append(address_input)
        port_input = ft.TextField(label="Port")
        add_group.controls.append(port_input)
        add_group_button = ft.ElevatedButton(text="Add Realm")

        add_group_rows = ft.Row()
        add_group_rows.controls.append(add_group_button)
        add_group.controls.append(add_group_rows)

        def on_add_realm_click(e):
            realm_id = realm_id_input.value
            address = address_input.value
            port = port_input.value
            string_send = f"addrealm {realm_id} {address} {port}"
            print("string send", string_send)
            response = self.cc.proses(string_send)
            print(response)
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            # self.page.add(self.groups_page())
            self.page.update()

        add_group_button.on_click = on_add_realm_click
        return add_group

if __name__ == "__main__":
    print("trying to connect ..")
    if (ON_WEB=="1"):
        ft.app(target=ChatApp().main,view=ft.WEB_BROWSER,port=8550)
    else:
        print("connecting")
        ft.app(target=ChatApp().main)
        print("connected")