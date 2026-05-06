import socket
import http.client
import ssl
from sys import platform
import time
import os
import json
import urllib.parse
import xml.etree.ElementTree as ET

class RecieverManager:
    def __init__(self, ip=None):
        self.ip = ip
        self.port_https = 10443
        self.port_telnet = 23
        self.telnet_timeout = 5.0
        self.context = ssl._create_unverified_context()
        self.headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "text/plain, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }

        self.INDEX_MAP = {
            "Front L":      {"lvl": "0",  "dst": "0",  "sz": "0",  "xo": "0"},
            "Front R":      {"lvl": "2",  "dst": "1",  "sz": "0",  "xo": "0"},
            "Center":       {"lvl": "1",  "dst": "2",  "sz": "1",  "xo": "1"},
            "Subwoofer 1":  {"lvl": "30", "dst": "3",  "sz": "2",  "xo": None},
            "Subwoofer 2":  {"lvl": "31", "dst": "4",  "sz": "2",  "xo": None},
            "Sub1 + Sub2":  {"lvl": "32", "dst": None, "sz": None, "xo": None},
            "Surround L":   {"lvl": "8",  "dst": "7",  "sz": "3",  "xo": "2"},
            "Surround R":   {"lvl": "4",  "dst": "8",  "sz": "3",  "xo": "2"},
            "Surr Back L":  {"lvl": "7",  "dst": "9",  "sz": "4",  "xo": "3"},
            "Surr Back R":  {"lvl": "5",  "dst": "10", "sz": "4",  "xo": "3"},
            "Surr Back":    {"lvl": "6",  "dst": "11", "sz": "4",  "xo": "3"},
            "Back Sp cnt":  {"lvl": None, "dst": None, "sz": "5",  "xo": None}, # Not needed for purpose of script, but included for completeness
            "Fr Wide L":    {"lvl": "9",  "dst": "12", "sz": "6",  "xo": "4"},
            "Fr Wide R":    {"lvl": "3",  "dst": "13", "sz": "6",  "xo": "4"},
            "Top Front L":  {"lvl": "25", "dst": "18", "sz": "9",  "xo": "7"},
            "Top Front R":  {"lvl": "12", "dst": "19", "sz": "9",  "xo": "7"},
            "Top Middle L": {"lvl": "24", "dst": "20", "sz": "10", "xo": "8"},
            "Top Middle R": {"lvl": "13", "dst": "21", "sz": "10", "xo": "8"},
            "Top Rear L":   {"lvl": "22", "dst": "24", "sz": "12", "xo": "10"},
            "Top Rear R":   {"lvl": "15", "dst": "25", "sz": "12", "xo": "10"},
            "Top Surround": {"lvl": "29", "dst": "33", "sz": "17", "xo": "15"},
            "Fr Height L":  {"lvl": "27", "dst": "14", "sz": "7",  "xo": "5"},
            "Fr Height R":  {"lvl": "10", "dst": "15", "sz": "7",  "xo": "5"},
            "Sr Height L":  {"lvl": "21", "dst": "26", "sz": "13", "xo": "11"},
            "Sr Height R":  {"lvl": "16", "dst": "27", "sz": "13", "xo": "11"},
            "R Height L":   {"lvl": "20", "dst": "28", "sz": "14", "xo": "12"},
            "R Height R":   {"lvl": "17", "dst": "29", "sz": "14", "xo": "12"},
            "Cntr Height":  {"lvl": "28", "dst": "32", "sz": "16", "xo": "14"},
            "Fr Dolby L":   {"lvl": "26", "dst": "16", "sz": "8",  "xo": "6"},
            "Fr Dolby R":   {"lvl": "11", "dst": "17", "sz": "8",  "xo": "6"},
            "Sr Dolby L":   {"lvl": "23", "dst": "22", "sz": "11", "xo": "9"},
            "Sr Dolby R":   {"lvl": "14", "dst": "23", "sz": "11", "xo": "9"},
            "Bk Dolby L":   {"lvl": "19", "dst": "30", "sz": "15", "xo": "13"},
            "Bk Dolby R":   {"lvl": "18", "dst": "31", "sz": "15", "xo": "13"}
        }

# Still missing index 5, 6 (distances) might be taken by speaker count and sub 1+2     

    # --- DISCOVERY ---
    def discover(self):
        print("[*] Searching for Denon AVR...")
        ssdp_msg = ('M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 3\r\nST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n\r\n')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(3)
        sock.sendto(ssdp_msg.encode(), ('239.255.255.250', 1900))
        try:
            while True:
                data, addr = sock.recvfrom(1024)
                if "Denon" in data.decode() or "AVR" in data.decode():
                    self.ip = addr[0]
                    print(f" [!] Found AVR at: {self.ip}")
                    return True
        except socket.timeout:
            return False

    # --- COMMS HELPERS ---
    def get_https_xml(self, path, referer_type="speakers"):
        headers = self.headers.copy()
        headers["Referer"] = f"https://{self.ip}:10443/{referer_type}/{referer_type}.html"
        try:
            conn = http.client.HTTPSConnection(self.ip, self.port_https, context=self.context, timeout=5)
            conn.request("GET", path, headers=headers)
            return ET.fromstring(conn.getresponse().read())
        except: return None

    def set_config_https(self, type_id, xml_payload, referer="speakers"):
        ts = int(time.time() * 1000)
        encoded = urllib.parse.quote(xml_payload)
        url = f"/ajax/{referer}/set_config?type={type_id}&data={encoded}&_={ts}"
        headers = self.headers.copy()
        headers["Referer"] = f"https://{self.ip}:10443/{referer}/{referer}.html"
        try:
            conn = http.client.HTTPSConnection(self.ip, self.port_https, context=self.context, timeout=5)
            conn.request("GET", url, headers=headers)
            return conn.getresponse().status == 200
        except: return False

    # --- TELNET (PORT 23) HELPERS ---
    def _telnet_exchange(self, commands, post_send_wait=1.2):
        """Open a port-23 session, send each command (with `post_send_wait`s
        between sends), read response, and cleanly shut down + close the socket.
        Returns response as a list of stripped lines."""
        chunks = []
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.telnet_timeout)
        try:
            s.connect((self.ip, self.port_telnet))
            time.sleep(0.3)
            for cmd in commands:
                s.sendall(cmd.encode("ascii") + b"\r")
                time.sleep(post_send_wait)
            try:
                while True:
                    data = s.recv(4096)
                    if not data:
                        break
                    chunks.append(data)
            except socket.timeout:
                pass
        finally:
            try: s.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            s.close()
        raw = b"".join(chunks).decode("ascii", errors="ignore")
        return [ln.strip() for ln in raw.split("\r") if ln.strip()]

    def _parse_surround_mode(self, lines):
        """Extract the surround mode code from an MS? response (ignores MSV volume line)."""
        for line in lines:
            if line.startswith("MS") and len(line) > 2 and not line.startswith("MSV"):
                return line[2:]
        return None

    def query_surround_mode(self):
        """Query and return the current surround mode code, or None on failure."""
        try:
            return self._parse_surround_mode(self._telnet_exchange(["MS?"]))
        except OSError:
            return None

    def set_surround_mode(self, mode_cmd):
        """Send a mode-change command (e.g. 'MSSTEREO') and re-query in the same
        session to confirm. Returns the new mode code, or None on failure."""
        try:
            # 2.0s after set so the AVR settles before we query.
            lines = self._telnet_exchange([mode_cmd, "MS?"], post_send_wait=2.0)
            return self._parse_surround_mode(lines)
        except OSError as exc:
            print(f"  [!] Telnet error setting surround mode: {exc}")
            return None

    # --- VOLUME & MUTE ---
    def set_volume(self, val):
        """
        Set master volume via AJAX globals set_config (type 12, raw 0-980).
        Values >  20 are treated as the linear/absolute scale (0-98).
        Values <= 20 are treated as dB (e.g. -40.0 or -12.5).
        """
        try:
            target = float(val)
            abs_val = target if target > 20 else (target + 80)

            # Round to nearest 0.5 step, then convert to raw 0-980 scale
            abs_val = round(abs_val * 2) / 2
            raw = max(0, min(980, int(abs_val * 10)))

            return self.set_config_https("12", f"<MainZone><Volume>{raw}</Volume></MainZone>", "globals")
        except:
            return False

    def toggle_mute(self, current_mute):
        """Toggle mute on/off via AJAX globals set_config (type 12). 1=ON, 2=OFF."""
        new_val = "2" if current_mute.upper() == "ON" else "1"
        return self.set_config_https("12", f"<MainZone><Mute>{new_val}</Mute></MainZone>", "globals")

    def toggle_power(self, current_power):
        """Toggle power on/off via AJAX globals set_config (type 4). 1=ON, 3=OFF."""
        new_val = "3" if current_power.upper() == "ON" else "1"
        return self.set_config_https("4", f"<MainZone><Power>{new_val}</Power></MainZone>", "globals")

    def _set_2ch_field(self, tag, value):
        """Write a single 2-channel Playback field (speakers type 9). The web UI
        sends bare elements with no outer <Playback2Ch> wrapper, e.g.
        <SubwooferMode>2</SubwooferMode>. Valid tags: Setting (1=Auto, 2=Manual),
        Front (2=Small, 3=Large), SubwooferMode (1=LFE, 2=LFE+Main)."""
        return self.set_config_https("9", f"<{tag}>{value}</{tag}>", "speakers")

    def ensure_power_on(self, state):
        """If the AVR is off, power it on and wait 10s for network services."""
        if (state['audio'].get('power') or 'off').upper() == "ON":
            return state
        print("[!] Main Zone is OFF. Powering ON...")
        self.toggle_power("OFF")
        print("[*] System booting... Waiting 10 seconds for network services.")
        time.sleep(10)
        return state


    # --- DATA AGGREGATION ---
    def fetch_full_state(self):
        print("[*] Gathering full system state...")
        state = {"audio": {}, "speakers": {}}

        # 0. Model name (10443 AJAX Globals type 3)
        model = self.get_https_xml("/ajax/globals/get_config?type=3", "globals")
        state['audio']['model'] = (model.text if model.tag == "FriendlyName" else model.findtext(".//FriendlyName")) if model is not None else "Unknown"
        
        # 1. Volume & Mute (10443 AJAX Globals type 12, MainZone)
        vm = self.get_https_xml("/ajax/globals/get_config?type=12", "globals")
        if vm is not None:
            vol_raw = vm.findtext("./MainZone/Volume")
            mute_raw = vm.findtext("./MainZone/Mute")
            try:
                state['audio']['vol_db'] = f"{(int(vol_raw) / 10) - 80:.1f}"
            except (TypeError, ValueError):
                state['audio']['vol_db'] = None
            state['audio']['mute'] = "ON" if mute_raw == "1" else "OFF"

        # 2. Power (10443 AJAX Globals type 4, MainZone: 1=ON, 3=OFF)
        pw = self.get_https_xml("/ajax/globals/get_config?type=4", "globals")
        if pw is not None:
            pwr_raw = pw.findtext("./MainZone/Power")
            state['audio']['power'] = "ON" if pwr_raw == "1" else "OFF"

        # 3. Source Name (10443 AJAX type 1, current Rename)
        src = self.get_https_xml("/ajax/home/get_config?type=1", "home")
        state['audio']['display_name'] = src.findtext(".//MainZone/SourceName") if src is not None else "Unknown"

        # 4. Input Default name (10443 AJAX inputs type 3, matched by Rename)
        inputs = self.get_https_xml("/ajax/inputs/get_config?type=3", "inputs")
        raw_input = None
        if inputs is not None:
            current = state['audio'].get('display_name')
            for s in inputs.findall(".//Source"):
                if s.findtext("Rename") == current:
                    raw_input = s.findtext("Default")
                    break
        state['audio']['raw_input'] = raw_input or state['audio'].get('display_name')

        # 5. Audyssey (10443 Type 9)
        aud = self.get_https_xml("/ajax/audio/get_config?type=9", "audio")
        state['audio']['audyssey'] = aud.findtext(".//MultEQ") if aud is not None else "0"

        # 5b. Surround Mode (Port 23 Telnet, MS? -> e.g. 'STEREO', 'DIRECT', 'MOVIE')
        state['audio']['surround_mode'] = self.query_surround_mode()

        # 5c. ECO Mode (10443 general type 3): 1=On, 2=Auto, 3=Off
        # Response shape: <ECO><Mode display="3">2</Mode>...</ECO>
        eco = self.get_https_xml("/ajax/general/get_config?type=3", "general")
        state['audio']['eco'] = (eco.findtext("Mode") or "0").strip() if eco is not None else "0"

        # 5d. Subwoofer LPF for LFE (10443 speakers type 7), e.g. <LPFforLFE>120</LPFforLFE>
        lpf = self.get_https_xml("/ajax/speakers/get_config?type=7", "speakers")
        state['audio']['lpf_lfe'] = (lpf.findtext(".//LPFforLFE") or "120").strip() if lpf is not None else "120"

        # 6. 2-Channel Playback (10443 speakers type 9): Setting (1=Auto/2=Manual),
        #    Front (2=Small/3=Large), SubwooferMode (1=LFE/2=LFE+Main). Also
        #    capture L/R distance (cm) and level (dB) from DistanceList/LevelList
        #    where index 0 = Front L, index 1 = Front R.
        ch2 = self.get_https_xml("/ajax/speakers/get_config?type=9", "speakers")
        if ch2 is not None:
            def _ch2_find(list_tag, idx):
                node = ch2.find(f"./{list_tag}/Speaker[@index='{idx}']")
                return node.text if node is not None else None
            state['audio']['2ch'] = {
                'setting':  ch2.findtext("./Setting")        or "1",
                'front':    ch2.findtext("./Front")          or "2",
                'sub_mode': ch2.findtext("./SubwooferMode")  or "1",
                'xover':    ch2.findtext("./Crossover")      or "0",
                'dist_l':   _ch2_find("DistanceList", "0")   or "0",
                'dist_r':   _ch2_find("DistanceList", "1")   or "0",
                'lvl_l':    _ch2_find("LevelList",    "0")   or "0",
                'lvl_r':    _ch2_find("LevelList",    "1")   or "0",
            }
        else:
            state['audio']['2ch'] = {'setting': '1', 'front': '2', 'sub_mode': '1',
                                     'xover': '0',
                                     'dist_l': '0', 'dist_r': '0', 'lvl_l': '0', 'lvl_r': '0'}

        # 7. Speaker Blocks (10443)
        blocks = {3: self.get_https_xml("/ajax/speakers/get_config?type=3"),
                  4: self.get_https_xml("/ajax/speakers/get_config?type=4"),
                  5: self.get_https_xml("/ajax/speakers/get_config?type=5"),
                  6: self.get_https_xml("/ajax/speakers/get_config?type=6")}

        for name, ids in self.INDEX_MAP.items():
            # Presence filter: the speaker is configured iff its level index
            # is actually present in the Level block (type 5).
            if ids['lvl'] is None or blocks[5] is None:
                continue
            lvl_node = blocks[5].find(f".//*[@index='{ids['lvl']}']")
            if lvl_node is None:
                continue

            spk = {'lvl_raw': lvl_node.text or "0"}
            # Size
            if ids['sz'] is not None and blocks[3] is not None:
                node = blocks[3].find(f".//*[@index='{ids['sz']}']")
                if node is not None:
                    v = node.findtext("Value") or node.text
                    spk['size_raw'] = v.strip()
            # Distance
            if ids['dst'] is not None and blocks[4] is not None:
                node = blocks[4].find(f".//*[@index='{ids['dst']}']")
                spk['dst_raw'] = node.text if node is not None else "0"
            # Crossover
            if ids['xo'] is not None and blocks[6] is not None:
                node = blocks[6].find(f".//*[@index='{ids['xo']}']")
                spk['xo_raw'] = node.text if node is not None else "0"

            state['speakers'][name] = spk

        return state

    def display_audit(self, state):
        os.system('cls' if os.name == 'nt' else 'clear')
        aud_modes = {"1": "Reference", "2": "L/C/R Bypass", "3": "Flat", "4": "Off"}
        print("=" * 54)
        a = state['audio']
        power_state = (a.get('power') or 'off').upper()
        power_color = "\033[92m" if power_state == "ON" else "\033[91m"
        power_display = f"{power_color}{power_state}\033[0m"
        print(f" {a.get('model')} | IP: {self.ip} | POWER: {power_display}")
        print("-" * 54)
        # Show volume in both dB and linear/absolute (0-98) scale
        try:
            vol_abs = float(a.get('vol_db', 0)) + 80
            vol_line = f"{a.get('vol_db')} dB  ({vol_abs:.1f})"
        except:
            vol_line = f"{a.get('vol_db')} dB"
        print(f" AUDYSSEY: {aud_modes.get(a.get('audyssey'), 'Unknown')} | VOL: {vol_line}")
        mute_state = (a.get('mute') or 'off').upper()
        mute_display = "[ MUTED ]" if mute_state == "ON" else "off"
#        print(f" SOURCE: {a.get('display_name')} ({a.get('raw_input')}) | MUTE: {mute_display}")
        eco_modes = {"1": "On", "2": "Auto", "3": "Off"}
        eco_lbl = eco_modes.get(a.get('eco'), "Unknown")
        print(f" SOURCE: {a.get('display_name')} ({a.get('raw_input')}) | ECO: {eco_lbl}")
        surround_code = a.get('surround_mode') or ''
        surround_label = {"DIRECT": "Direct", "PURE DIRECT": "Pure Direct",
                          "STEREO": "Stereo"}.get(surround_code, surround_code or "Unknown")
        print(f" SURROUND: {surround_label}")
        print("-" * 54)

        rows = []
        for name, data in state['speakers'].items():
            ids = self.INDEX_MAP.get(name, {})

            # Size: — when the speaker has no size index (virtual/combined entries)
            if ids.get('sz') is None:
                sz = "—"
            elif name in ("Subwoofer 1", "Subwoofer 2"):
                sz = "—"
#                sz = "1 Sub" if data.get('size_raw') == "6" else "2 Subs"
            else:
                sz = "Small" if data.get('size_raw') == "2" else "Large"
            # Level: show in dB with sign, e.g. -12.5 dB or +3.0 dB
            lvl = f"{float(data.get('lvl_raw', 0))/10:+.1f} dB"

            # Distance: — when no distance index
            if ids.get('dst') is None:
                dst = "—"
            else:
                m = float(data.get('dst_raw', 0))/100
                dst = f"{m*3.28084:.1f} ft"

            # Crossover: subs show LPF for LFE; others show their per-speaker xover
            if name.startswith("Subwoofer"):
                lpf = a.get('lpf_lfe')
                xo = f"{lpf} Hz" if lpf else "—"
            elif ids.get('xo') is None:
                xo = "—"
            else:
                xo = f"{data.get('xo_raw')} Hz" if data.get('xo_raw') else "N/A"
                if sz == "Large":
                    xo = "Full Band"

            rows.append([name, sz, lvl, dst, xo])

        headers = ["Speaker", "Size", "Level", "Distance", "Crossover"]
        widths = [max(len(str(r[i])) for r in ([headers] + rows)) for i in range(len(headers))]
        fmt = "  ".join(f"{{:<{w}}}" for w in widths)
        print(" " + fmt.format(*headers))
        print(" " + fmt.format(*["-" * w for w in widths]))
        for r in rows:
            print(" " + fmt.format(*r))

        # 2-Channel Mode (dedicated section)
        ch2 = a.get('2ch', {})
        setting_lbl  = {"1": "Auto",  "2": "Manual"  }.get(ch2.get('setting'),  "?")
        front_lbl    = {"2": "Small", "3": "Large"   }.get(ch2.get('front'),    "?")
        sub_mode_lbl = {"1": "LFE",   "2": "LFE+Main"}.get(ch2.get('sub_mode'), "?")
        try:
            lvl_l = f"{float(ch2.get('lvl_l', 0))/10:+.1f} dB"
            lvl_r = f"{float(ch2.get('lvl_r', 0))/10:+.1f} dB"
        except (TypeError, ValueError):
            lvl_l = lvl_r = "?"
        try:
            dst_l = f"{float(ch2.get('dist_l', 0))/100*3.28084:.1f} ft"
            dst_r = f"{float(ch2.get('dist_r', 0))/100*3.28084:.1f} ft"
        except (TypeError, ValueError):
            dst_l = dst_r = "?"
        print("-" * 54)
        print(f" 2-CHANNEL MODE | Setting: {setting_lbl} | SW Mode: {sub_mode_lbl}")
        print("-" * 54)
        xo = "Full Band" if front_lbl == "Large" else (f"{ch2.get('xover')} Hz" if ch2.get('xover') else "N/A")
        ch2_headers = ["Speaker", "Size", "Level", "Distance", "Crossover"]
        ch2_rows = [["Front L", front_lbl, lvl_l, dst_l, xo],
                    ["Front R", front_lbl, lvl_r, dst_r, xo]]
        ch2_widths = [max(len(str(r[i])) for r in ([ch2_headers] + ch2_rows)) for i in range(len(ch2_headers))]
        ch2_fmt = " ".join(f"{{:<{w}}}" for w in ch2_widths)
        print(" " + ch2_fmt.format(*ch2_headers))
        print(" " + ch2_fmt.format(*["-" * w for w in ch2_widths]))
        for r in ch2_rows:
            print(" " + ch2_fmt.format(*r))
        print("=" * 54)

    # --- ACTION MACROS ---
    def apply_state(self, target_state):
        print("[*] Applying configuration payload...")
        # Master Volume
        self.set_volume(target_state['audio'].get('vol_db', -40.0))

        # Audyssey
        print("  [+] Setting Audyssey...")
        self.set_config_https("9", f"<MultEQ>{target_state['audio']['audyssey']}</MultEQ>", "audio")

        # 2-Channel Playback (speakers type 9). Front + SubwooferMode and the
        # L/R distance/level lists are read-only while Setting=Auto, so enter
        # Manual, write all fields, then apply target Setting last.
        ch2 = target_state['audio'].get('2ch')
        if ch2:
            print("  [+] Setting 2-Channel Playback config...")
            self._set_2ch_field('Setting', '2'); time.sleep(0.3)
            if ch2.get('front'):
                self._set_2ch_field('Front', ch2['front']); time.sleep(0.3)
            if ch2.get('sub_mode'):
                self._set_2ch_field('SubwooferMode', ch2['sub_mode']); time.sleep(0.3)
            # Web UI sends one request per speaker (per the Set button), so
            # write L and R distance/level individually.
            if ch2.get('dist_l') is not None:
                self._set_2ch_field('DistanceList', f'<Speaker index="0">{ch2["dist_l"]}</Speaker>'); time.sleep(0.3)
            if ch2.get('dist_r') is not None:
                self._set_2ch_field('DistanceList', f'<Speaker index="1">{ch2["dist_r"]}</Speaker>'); time.sleep(0.3)
            if ch2.get('lvl_l') is not None:
                self._set_2ch_field('LevelList',    f'<Speaker index="0">{ch2["lvl_l"]}</Speaker>');  time.sleep(0.3)
            if ch2.get('lvl_r') is not None:
                self._set_2ch_field('LevelList',    f'<Speaker index="1">{ch2["lvl_r"]}</Speaker>');  time.sleep(0.3)
            self._set_2ch_field('Setting', ch2.get('setting','2'))

        # Batch Levels (Type 5) - only speakers with a level index
        print("  [+] Setting Speaker Levels...")
        lvl_xml = "".join(f'<Speaker index="{self.INDEX_MAP[n]["lvl"]}">{d["lvl_raw"]}</Speaker>'
                          for n, d in target_state['speakers'].items()
                          if self.INDEX_MAP[n].get("lvl") is not None and 'lvl_raw' in d)
        if lvl_xml:
            self.set_config_https("5", f"<List>{lvl_xml}</List>")

        # Batch Distances (Type 4) - only speakers with a distance index
        print("  [+] Setting Speaker Distances...")
        dst_xml = "".join(f'<Speaker index="{self.INDEX_MAP[n]["dst"]}">{d["dst_raw"]}</Speaker>'
                          for n, d in target_state['speakers'].items()
                          if self.INDEX_MAP[n].get("dst") is not None and 'dst_raw' in d)
        if dst_xml:
            self.set_config_https("4", f"<Distances><List>{dst_xml}</List></Distances>")

        # Sizes (Type 3 - per unique index, skip Subwoofer 1)
        print("  [+] Setting Speaker Sizes...")
        seen_sz = set()
        for name, d in target_state['speakers'].items():
            if name == "Subwoofer 1":
                continue
            sz_idx = self.INDEX_MAP[name].get("sz")
            if sz_idx is None or 'size_raw' not in d or sz_idx in seen_sz:
                continue
            seen_sz.add(sz_idx)
            self.set_config_https("3", f'<Speaker index="{sz_idx}">{d["size_raw"]}</Speaker>')

    def apply_diff(self, backup, current):
        print("[*] Computing differential restore...")
        changes = 0

        # Volume
        if backup['audio'].get('vol_db') != current['audio'].get('vol_db'):
            self.set_volume(backup['audio']['vol_db'])
            print(f"  [~] Volume: {current['audio'].get('vol_db')} -> {backup['audio']['vol_db']} dB")
            changes += 1

        # Audyssey
        if backup['audio'].get('audyssey') != current['audio'].get('audyssey'):
            self.set_config_https("9", f"<MultEQ>{backup['audio']['audyssey']}</MultEQ>", "audio")
            print(f"  [~] Audyssey: {current['audio'].get('audyssey')} -> {backup['audio']['audyssey']}")
            changes += 1

        # Surround Mode (telnet MS<code>)
        backup_mode  = backup['audio'].get('surround_mode')
        current_mode = current['audio'].get('surround_mode')
        if backup_mode and backup_mode != current_mode:
            self.set_surround_mode(f"MS{backup_mode}")
            print(f"  [~] Surround Mode: {current_mode} -> {backup_mode}")
            changes += 1

        # ECO Mode (10443 general type 3): 1=On, 2=Auto, 3=Off
        backup_eco  = backup['audio'].get('eco')
        current_eco = current['audio'].get('eco')
        if backup_eco and backup_eco != current_eco:
            self.set_config_https("3", f"<Mode>{backup_eco}</Mode>", "general")
            eco_lbl = {"1": "On", "2": "Auto", "3": "Off"}
            print(f"  [~] ECO: {eco_lbl.get(current_eco, current_eco)} -> {eco_lbl.get(backup_eco, backup_eco)}")
            changes += 1

        # Subwoofer LPF for LFE (10443 speakers type 7), e.g. 80..250 Hz
        backup_lpf  = backup['audio'].get('lpf_lfe')
        current_lpf = current['audio'].get('lpf_lfe')
        if backup_lpf and backup_lpf != current_lpf:
            self.set_config_https("7", f"<LPFforLFE>{backup_lpf}</LPFforLFE>", "speakers")
            print(f"  [~] Sub LPF: {current_lpf} -> {backup_lpf} Hz")
            changes += 1

        # 2-Channel Playback. Front, SubwooferMode, and L/R distance/level are
        # read-only while Setting=Auto, so enter Manual first if any of those
        # need to change, apply them, then set final Setting last (which may
        # revert to Auto).
        b2 = backup['audio'].get('2ch') or {}
        c2 = current['audio'].get('2ch') or {}
        bset, bfr, bsub = b2.get('setting'), b2.get('front'), b2.get('sub_mode')
        cset, cfr, csub = c2.get('setting'), c2.get('front'), c2.get('sub_mode')
        need_fr  = bfr  is not None and bfr  != cfr
        need_sub = bsub is not None and bsub != csub
        need_set = bset is not None and bset != cset
        # Per-speaker distance/level diffs (web UI sets each individually).
        dst_writes = [(idx, lbl, b2.get(bkey), c2.get(bkey))
                      for idx, lbl, bkey in (("0", "L", "dist_l"), ("1", "R", "dist_r"))
                      if b2.get(bkey) is not None and b2.get(bkey) != c2.get(bkey)]
        lvl_writes = [(idx, lbl, b2.get(bkey), c2.get(bkey))
                      for idx, lbl, bkey in (("0", "L", "lvl_l"),  ("1", "R", "lvl_r"))
                      if b2.get(bkey) is not None and b2.get(bkey) != c2.get(bkey)]
        need_dst = bool(dst_writes)
        need_lvl = bool(lvl_writes)
        if need_fr or need_sub or need_set or need_dst or need_lvl:
            # All 2CH writes require Manual. Enter Manual if any field is changing.
            if (need_fr or need_sub or need_dst or need_lvl) and cset != '2':
                self._set_2ch_field('Setting', '2'); time.sleep(0.3)
            if need_fr:
                self._set_2ch_field('Front', bfr); time.sleep(0.3)
                print(f"  [~] 2CH Front: {cfr} -> {bfr}")
                changes += 1
            if need_sub:
                self._set_2ch_field('SubwooferMode', bsub); time.sleep(0.3)
                print(f"  [~] 2CH SubMode: {csub} -> {bsub}")
                changes += 1
            for idx, lbl, bval, cval in dst_writes:
                self._set_2ch_field('DistanceList', f'<Speaker index="{idx}">{bval}</Speaker>'); time.sleep(0.3)
                print(f"  [~] 2CH Dist {lbl}: {cval} -> {bval}")
                changes += 1
            for idx, lbl, bval, cval in lvl_writes:
                self._set_2ch_field('LevelList',    f'<Speaker index="{idx}">{bval}</Speaker>'); time.sleep(0.3)
                print(f"  [~] 2CH Level {lbl}: {cval} -> {bval}")
                changes += 1
            # Apply target Setting last (may revert to Auto).
            final_set = bset or cset or '2'
            if need_set or ((need_fr or need_sub or need_dst or need_lvl) and final_set != '2'):
                self._set_2ch_field('Setting', final_set); time.sleep(0.3)
                if need_set:
                    print(f"  [~] 2CH Setting: {cset} -> {bset}")
                    changes += 1

        # Levels - batch only changed speakers (must have a level index)
        lvl_items = [(n, d) for n, d in backup['speakers'].items()
                     if n in self.INDEX_MAP and self.INDEX_MAP[n].get("lvl") is not None
                     and 'lvl_raw' in d
                     and d.get('lvl_raw') != current['speakers'].get(n, {}).get('lvl_raw')]
        if lvl_items:
            lvl_xml = "".join(f'<Speaker index="{self.INDEX_MAP[n]["lvl"]}">{d["lvl_raw"]}</Speaker>' for n, d in lvl_items)
            self.set_config_https("5", f"<List>{lvl_xml}</List>")
            for n, d in lvl_items:
                print(f"  [~] {n} level: {current['speakers'].get(n, {}).get('lvl_raw')} -> {d['lvl_raw']}")
            changes += len(lvl_items)

        # Distances - batch only changed speakers (must have a distance index)
        dst_items = [(n, d) for n, d in backup['speakers'].items()
                     if n in self.INDEX_MAP and self.INDEX_MAP[n].get("dst") is not None
                     and 'dst_raw' in d
                     and d.get('dst_raw') != current['speakers'].get(n, {}).get('dst_raw')]
        if dst_items:
            dst_xml = "".join(f'<Speaker index="{self.INDEX_MAP[n]["dst"]}">{d["dst_raw"]}</Speaker>' for n, d in dst_items)
            self.set_config_https("4", f"<Distances><List>{dst_xml}</List></Distances>")
            for n, d in dst_items:
                print(f"  [~] {n} distance: {current['speakers'].get(n, {}).get('dst_raw')} -> {d['dst_raw']}")
            changes += len(dst_items)

        # Sizes - per unique index, skip Subwoofer 1, only where changed
        seen_sz = set()
        for name, d in backup['speakers'].items():
            if name == "Subwoofer 1" or name not in self.INDEX_MAP:
                continue
            if 'size_raw' not in d:
                continue
            if d.get('size_raw') == current['speakers'].get(name, {}).get('size_raw'):
                continue
            sz_idx = self.INDEX_MAP[name].get("sz")
            if sz_idx is None or sz_idx in seen_sz:
                continue
            seen_sz.add(sz_idx)
            self.set_config_https("3", f'<Speaker index="{sz_idx}">{d["size_raw"]}</Speaker>')
            print(f"  [~] {name} size (index {sz_idx}): {current['speakers'].get(name, {}).get('size_raw')} -> {d['size_raw']}")
            changes += 1

        if changes == 0:
            print("  [!] No differences found. Nothing to apply.")
        else:
            print(f"  [+] Differential restore complete. {changes} setting(s) updated.")

    def calibration_macro(self, mode):
        print(f"[*] Preparing for {mode.upper()} CALIBRATION...")
        state = self.fetch_full_state()
        state['audio']['audyssey'] = "4"    # Off
        state['audio']['vol_db'] = "-10"  # 70 Absolute
        # Force 2-ch to Manual + Large front + LFE (not LFE+Main) for calibration,
        # with L/R distance=0 cm and level=0 dB.
        state['audio']['2ch'] = {'setting': '2', 'front': '3', 'sub_mode': '1',
                                 'dist_l': '0', 'dist_r': '0',
                                 'lvl_l':  '0', 'lvl_r':  '0'}

        # Only target speakers that are actually configured on the AVR.
        if mode == "full":
            target_names = [n for n in self.INDEX_MAP if n in state['speakers']]
        else:
            target_names = [n for n in ("Front L", "Front R", "Subwoofer 1") if n in state['speakers']]

        for name in target_names:
            state['speakers'][name]['lvl_raw'] = "0"
            if 'dst_raw' in state['speakers'][name]:
                state['speakers'][name]['dst_raw'] = "0"
            if "Subwoofer" not in name and 'size_raw' in state['speakers'][name]:
                state['speakers'][name]['size_raw'] = "3"  # Large

        state['speakers'] = {n: state['speakers'][n] for n in target_names}
        self.apply_state(state)

        print("  [+] Activating Stereo mode for calibration...")
        confirmed = self.set_surround_mode("MSSTEREO")
        if confirmed == "STEREO":
            print("  [+] Stereo mode confirmed active.")
        else:
            print(f"  [!] Stereo mode may not have set correctly (got: {confirmed})")

        print("  [+] Forcing ECO mode Off for calibration...")
        self.set_config_https("3", "<Mode>3</Mode>", "general")

        print("  [+] Setting Subwoofer LPF for LFE to 250 Hz for calibration...")
        self.set_config_https("7", "<LPFforLFE>250</LPFforLFE>", "speakers")

        print("  [+] Calibration environment ready.")

def main():
    mgr = RecieverManager()
    if not mgr.discover():
        ip = input("AVR not found. Enter IP: ").strip()
        mgr.ip = ip

    while True:
        state = mgr.fetch_full_state()
        mgr.display_audit(state)

        print("\nOPTIONS:")
        print(" \033[1mb\033[0m: Backup               \033[1mr\033[0m: Restore")
        print(" \033[1mf\033[0m: Full Calibration     \033[1ms\033[0m: Sub Calibration")
        print(" \033[1mv\033[0m: Set Volume           \033[1mp\033[0m: Toggle Power")
        print(" \033[1md\033[0m: Refresh Display      \033[1mq\033[0m: Quit")

        choice = input("\nChoice: ").strip().lower()

        if choice == 'b':
            with open("avr_backup.json", "w") as f:
                json.dump(state, f, indent=4)
            print("[+] Backup saved to avr_backup.json")
            time.sleep(2)
        elif choice == 'r':
            if os.path.exists("avr_backup.json"):
                with open("avr_backup.json", "r") as f:
                    backup = json.load(f)
                current = mgr.ensure_power_on(mgr.fetch_full_state())
                mgr.apply_diff(backup, current)
            else:
                print("[!] No backup file found.")
            time.sleep(2)
        elif choice == 's':
            state = mgr.ensure_power_on(state)
            mgr.calibration_macro("sub")
            time.sleep(2)
        elif choice == 'f':
            state = mgr.ensure_power_on(state)
            mgr.calibration_macro("full")
            time.sleep(2)
        elif choice == 'p':
            current_power = (state['audio'].get('power') or 'off')
            mgr.toggle_power(current_power)
            new_label = "OFF" if current_power.upper() == "ON" else "ON"
            print(f"  [+] Power toggled -> {new_label}")
            if new_label == "ON":
                print("[*] System booting... Waiting 10 seconds for network services.")
                time.sleep(10)            
        elif choice == 'v':
            try:
                vol_abs = float(state['audio'].get('vol_db', 0)) + 80
                print(f"\n  Current volume : {state['audio'].get('vol_db')} dB  ({vol_abs:.1f} abs)")
            except:
                print(f"\n  Current volume : {state['audio'].get('vol_db')} dB")
            print("  Enter a value to set volume:")
            print("   • dB  (value <= 20) : e.g.  -40   or  -12.5")
            print("   • Abs (value  > 20) : e.g.   38   or   67.5")
            val = input("  Volume: ").strip()
            if val:
                state = mgr.ensure_power_on(state)
                if mgr.set_volume(val):
                    print("  [+] Volume set.")
                else:
                    print("  [!] Invalid value. Enter a number.")
            time.sleep(1)
        elif choice == 'm':
            state = mgr.ensure_power_on(state)
            current_mute = (state['audio'].get('mute') or 'off')
            mgr.toggle_mute(current_mute)
            new_label = "OFF" if current_mute.upper() == "ON" else "ON"
            print(f"  [+] Mute toggled -> {new_label}")
            time.sleep(1)
        elif choice == 'q':
            break


if __name__ == "__main__":
    main()

