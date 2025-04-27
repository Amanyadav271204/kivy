from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.list import TwoLineListItem, MDList
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.textfield import MDTextField
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
import psutil, socket
from kivy.core.clipboard import Clipboard
from threading import Thread
from kivy.core.window import Window

Window.size = (300, 600)

KV = '''
ScreenManager:
    ConnectionScreen:
    PacketShareScreen:

<ConnectionScreen>:
    name: 'connections'
    BoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            title: "Connection Monitor"
            md_bg_color: app.theme_cls.primary_color

        # ── SEARCH BAR ───────────────────────────────
        MDTextField:
            id: search_bar
            hint_text: "Search…"
            mode: "rectangle"
            size_hint_y: None
            height: "44dp"
            on_text: app.filter_connections(self.text)

        MDRaisedButton:
            text: "Refresh Connection List"
            size_hint_y: None
            height: "44dp"
            pos_hint: {"center_x": .5}
            on_release: app.refresh_connections()

        ScrollView:
            MDList:
                id: connection_list

        MDRaisedButton:
            text: "Go to Packet Sharing"
            size_hint_y: None
            height: "44dp"
            pos_hint: {"center_x": .5}
            on_release: app.change_screen('packet_share')


<PacketShareScreen>:
    name: 'packet_share'
    BoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            title: "Packet Sharing"
            md_bg_color: app.theme_cls.primary_color

        MDTextField:
            id: ip_input
            hint_text: "Enter IP Address"
            size_hint_y: None; height: "44dp"

        MDTextField:
            id: port_input
            hint_text: "Enter Port Number"
            size_hint_y: None; height: "44dp"

        MDTextField:
            hint_text: "Search…"
            size_hint_y: None
            height: "44dp"

        MDRaisedButton:
            text: "Send Packets"
            size_hint_y: None; height: "44dp"
            pos_hint: {"center_x": .5}
            on_release: app.send_packet()

        MDRaisedButton:
            text: "Go to Connections"
            size_hint_y: None; height: "44dp"
            pos_hint: {"center_x": .5}
            on_release: app.change_screen('connections')

        MDLabel:
            id: result_label
            text: ""
            halign: "center"
            size_hint_y: None; height: "44dp"
'''

class ConnectionScreen(Screen):
    pass

class PacketShareScreen(Screen):
    pass

class ConnectionMonitorApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.all_connections = []      # store full list for searching
        return Builder.load_string(KV)

    # ────────── CONNECTION LIST HANDLING ──────────
    def refresh_connections(self):
        Thread(target=self.fetch_connections).start()

    def fetch_connections(self):
        conns = list_applications_with_connections()
        Clock.schedule_once(lambda dt: self.update_connection_list(conns))

    def update_connection_list(self, connections):
        self.all_connections = connections          # keep a copy
        self.populate_list(connections)

    def populate_list(self, connections):
        clist = self.root.get_screen('connections').ids.connection_list
        clist.clear_widgets()
        if not connections:
            clist.add_widget(TwoLineListItem(text="No Connections Found"))
            return
        for conn in connections:
            item = TwoLineListItem(
                text=f"App: {conn['Application']}",
                secondary_text=f"{conn['Protocol']} | {conn['Local Address']} → {conn['Remote Address']}",
                on_release=lambda x, addr=conn['Local Address']: self.copy_ip(addr)
            )
            item.ids._lbl_primary.font_size = '14sp'
            item.ids._lbl_secondary.font_size = '12sp'
            clist.add_widget(item)

    # ────────── SEARCH / FILTER ──────────
    def filter_connections(self, query):
        query = query.lower()
        if not query:
            self.populate_list(self.all_connections)
            return
        filtered = [c for c in self.all_connections
                    if query in c['Application'].lower()
                    or query in c['Local Address'].lower()
                    or query in c['Remote Address'].lower()]
        self.populate_list(filtered)

    # ────────── OTHER UTILS ──────────
    def copy_ip(self, addr):
        Clipboard.copy(addr.split(':')[0])  # copy only IP part
        print("Copied:", addr)

    def send_packet(self):
        scr = self.root.get_screen('packet_share')
        ip   = scr.ids.ip_input.text
        port = scr.ids.port_input.text
        cnt  = scr.ids.packet_count_input.text
        lbl  = scr.ids.result_label

        if self.valid_ip(ip) and port.isdigit() and cnt.isdigit():
            port, cnt = int(port), int(cnt)
            try:
                for _ in range(cnt):
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.sendto(b"Hello", (ip, port))
                lbl.text = f"Sent {cnt} packets to {ip}:{port}"
                lbl.theme_text_color = "Custom"; lbl.text_color = (0,1,0,1)
            except Exception as e:
                lbl.text = f"Error: {e}"
                lbl.theme_text_color = "Custom"; lbl.text_color = (1,0,0,1)
        else:
            lbl.text = "Invalid input!"
            lbl.theme_text_color = "Custom"; lbl.text_color = (1,0,0,1)

    def valid_ip(self, ip):
        try: socket.inet_pton(socket.AF_INET, ip); return True
        except socket.error: return False

    def change_screen(self, scr): self.root.current = scr

# ────────── HELPERS ──────────
def get_process_name(pid):
    try: return psutil.Process(pid).name()
    except: return None

def list_applications_with_connections():
    out=[]
    for c in psutil.net_connections(kind='inet'):
        if c.pid and (name:=get_process_name(c.pid)):
            out.append(dict(
                Application=name,
                Protocol='TCP' if c.type==socket.SOCK_STREAM else 'UDP',
                Local_Address=f"{c.laddr.ip}:{c.laddr.port}",
                Remote_Address=f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else 'N/A'
            ))
    return out

if __name__ == "__main__":
    ConnectionMonitorApp().run()
