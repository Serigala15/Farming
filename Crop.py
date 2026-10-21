#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
import uuid
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

try:
    import requests
except ImportError:
    print("ERROR: install dulu 'requests' → pip install requests")
    sys.exit(1)

# ==================== CONSTANTS ====================
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "cconfig.json"
BASE = "https://cryptocrops.net"

DEFAULT_CONFIG = {
    "cookie": ""
}

STATE = {
    "farm_coins": 0,
    "farm_level": 1,
    "total_capacity": 4,
    "crops": [],
    "seeds": {},
    "seed_info": {},
    "produce": {}, 
    "orders": [],
    "catalog": {},
    "checkpoint_required": False,
    "required_since": 0,
    "pool_total_hc": 0,
    "pool_ends_at": 0,
    "pool_est_hc": 0,
    "pool_est_usd": 0,
}

TIMER_ACTIVE = False

AUTH_ERROR_KEYWORDS = [
    "AUTHENTICATION_REQUIRED", "UNAUTHORIZED", "INVALID_SESSION",
    "SESSION_EXPIRED", "AUTH_REQUIRED",
]

# ==================== COLORS & BANNER ====================
class C:
    R = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
    CYAN = "\033[96m"; MAGENTA = "\033[95m"; BLUE = "\033[94m"
    WHITE = "\033[97m"; GRAY = "\033[90m"
    PINK = "\033[38;5;213m"
    LIGHT_GREEN = "\033[38;5;118m" 
    ORANGE = "\033[38;5;214m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def now_str():
    return datetime.now().strftime("%H:%M:%S")

def fmt_duration(seconds):
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def banner():
    clear()
    c_muda = "\033[38;5;118m"
    c_tua  = "\033[38;5;28m"
    c_daun = "\033[38;5;34m"
    bold = "\033[1m"
    reset = "\033[0m"

    print(f"""{bold}{c_muda}              ███████╗ █████╗ ██████╗ ███╗   ███╗
              ██╔════╝██╔══██╗██╔══██╗████╗ ████║
              {c_tua}█████╗  ███████║██████╔╝██╔████╔██║
              ██╔══╝  ██╔══██║██╔══██╗██║╚██╔╝██║
              {c_daun}██║     ██║  ██║██║  ██║██║ ╚═╝ ██║
              ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
    {reset}""")
    print(f"{C.YELLOW}{bold}                   CRYPTOCROPS Versi Mantap!{reset}")
    print(f"{c_muda}{bold}                 Mod by Jendela Semesta REBORN{reset}")
    print(f"{C.WHITE}{bold}                      Join my Group Telegram{reset}")
    print(f"{C.BOLD}{C.ORANGE}   https://t.me/jendelasemesta | https://t.me/jendelagamedana{reset}\n")

# ==================== UTILS ====================
def log(msg, level="info"):
    global TIMER_ACTIVE
    icons = {
        "info": f"{C.CYAN}ℹ{C.R}", "ok": f"{C.GREEN}✔{C.R}",
        "warn": f"{C.YELLOW}⚠{C.R}", "err": f"{C.RED}✖{C.R}",
        "farm": f"{C.GREEN}🌱{C.R}", "coin": f"{C.YELLOW}🪙{C.R}",
        "captcha": f"{C.BLUE}🔐{C.R}", "sync": f"{C.BLUE}🔄{C.R}",
        "order": f"{C.MAGENTA}📦{C.R}", "money": f"{C.GREEN}💵{C.R}",
        "upgrade": f"{C.MAGENTA}⬆️{C.R}",
    }
    icon = icons.get(level, icons["info"])
    print(f"{C.PINK}[{now_str()}]{C.R} {icon}  {msg}")

def section(title):
    print(f"\n{C.BOLD}{C.GREEN}▸ {title}{C.R}")
    print(f"{C.GRAY}{'─' * 56}{C.R}")

def is_auth_error(err_str):
    s = str(err_str).upper()
    return any(k in s for k in AUTH_ERROR_KEYWORDS)

def blink_earnings(hc, usd):
    text = f"💰 ESTIMASI REWARD POOL: {hc} HC (${usd:.2f}) 💰"
    for _ in range(5): 
        sys.stdout.write(f"\r\033[K{C.BOLD}{C.GREEN}{text}{C.R}")
        sys.stdout.flush()
        time.sleep(0.4)
        sys.stdout.write(f"\r\033[K") 
        sys.stdout.flush()
        time.sleep(0.4)
    
    print(f"\n{C.BOLD}{C.GREEN}╔══════════════════════════════════════════════════╗{C.R}")
    print(f"{C.BOLD}{C.GREEN}║ {text.center(48)} ║{C.R}")
    print(f"{C.BOLD}{C.GREEN}╚══════════════════════════════════════════════════╝{C.R}\n")

# ==================== CONFIG ====================
def load_config():
    if not CONFIG_PATH.exists(): return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"{C.RED}!! Gagal simpan config: {e}{C.R}")

def normalize_cookie(raw):
    if not raw: return ""
    raw = raw.strip().replace("\r", "").replace("\n", "").replace("\t", " ")
    if ";" not in raw and "," in raw:
        raw = raw.replace(",", ";")
    import re
    raw = re.sub(r"\s*;\s*", "; ", raw)
    return raw.strip().rstrip(";")

def ensure_config():
    cfg = load_config()
    if cfg and isinstance(cfg, dict):
        changed = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
                changed = True
        if cfg.get("cookie"):
            normalized = normalize_cookie(cfg["cookie"])
            if normalized != cfg["cookie"]:
                cfg["cookie"] = normalized
                changed = True
        if changed:
            save_config(cfg)
        return cfg

    banner()
    section("Setup Config Pertama Kali")
    print(f"{C.YELLOW}File cconfig.json belum ada. Silakan masukkan Cookie.{C.R}\n")
    cookie = input(f"  {C.CYAN}Cookie browser{C.R} : ").strip()
    
    cfg = {"cookie": normalize_cookie(cookie)}
    save_config(cfg)
    print(f"\n{C.GREEN}✔ cconfig.json tersimpan di {CONFIG_PATH}{C.R}\n")
    time.sleep(1)
    return cfg

# ==================== STATE UPDATER ====================
def update_state_from_bootstrap(bootstrap):
    farm = bootstrap.get("farm") or {}
    profile = farm.get("profile") or {}
    STATE["farm_coins"] = profile.get("farm_coins", 0)
    STATE["farm_level"] = profile.get("farm_level", 1)
    STATE["total_capacity"] = profile.get("total_capacity") or profile.get("base_capacity") or 4

    crops = []
    for c in farm.get("crops") or []:
        crops.append({
            "crop_id": c.get("crop_id"), 
            "seed_id": c.get("seed_id"),
            "plot_index": c.get("plot_index"),
            "ready_at_ms": int(c.get("ready_at") or c.get("harvest_ready_at") or 0),
        })
    STATE["crops"] = crops

    seeds = {}
    seed_info = {}
    for s in farm.get("seeds") or []:
        seeds[s["seed_id"]] = s.get("quantity", 0)
        seed_info[s["seed_id"]] = s
    STATE["seeds"] = seeds
    STATE["seed_info"] = seed_info

    produce = {}
    inventory_data = farm.get("inventory") or []
    for p in inventory_data:
        sid = p.get("seed_id")
        qty = p.get("fresh_quantity", p.get("quantity", 0))
        if sid and qty > 0:
            produce[sid] = qty
    STATE["produce"] = produce

    orders_data = farm.get("orders") or farm.get("active_orders") or []
    STATE["orders"] = orders_data

    checkpoint = farm.get("farm_checkpoint") or {}
    STATE["checkpoint_required"] = bool(checkpoint.get("required"))
    STATE["required_since"] = int(checkpoint.get("required_since") or 0)

    pool = bootstrap.get("pool") or {}
    STATE["pool_total_hc"] = pool.get("harvestCredits", 0)
    STATE["pool_ends_at"] = pool.get("endsAt", 0)
    STATE["pool_est_hc"] = pool.get("estimatedHarvestCredits", 0)
    STATE["pool_est_usd"] = pool.get("estimatedUsdMicros", 0) / 1_000_000

# ==================== CLIENT ====================
class FarmClient:
    RARITY_RANK = {"mythical": 6, "legendary": 5, "epic": 4, "rare": 3, "uncommon": 2, "common": 1}
    
    SEED_ICONS = {
        "carrot": "🥕", "lettuce": "🥬", "radish": "🥗", "wheat": "🌾",
        "corn": "🌽", "tomato": "🍅", "eggplant": "🍆", "pumpkin": "🎃", "strawberry": "🍓",
    }

    def __init__(self, cfg):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": BASE,
            "Referer": f"{BASE}/farm/",
        })
        self.update_session_cookie(cfg.get("cookie", ""))

    def update_session_cookie(self, cookie_str):
        self.session.cookies.clear()
        cookie_raw = normalize_cookie(cookie_str)
        for part in cookie_raw.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                k, v = k.strip(), unquote(v.strip())
                if k and v: self.session.cookies.set(k, v, domain="cryptocrops.net")

    def get_icon(self, seed_id):
        return self.SEED_ICONS.get(str(seed_id).lower(), "🌱")

    def api(self, method, path, json_data=None, referer=None, retries=3):
        headers = {}
        if referer: headers["Referer"] = referer
        
        for attempt in range(retries):
            try:
                r = self.session.request(method, BASE + path, json=json_data, headers=headers or None, timeout=45)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == retries - 1:
                    raise Exception(f"Koneksi ke server terputus.")
                time.sleep(2)
            except Exception as e:
                raise Exception(f"Request Error: {e}")

        try:
            data = r.json()
        except Exception:
            raise Exception(f"HTTP {r.status_code} | non-JSON: {r.text[:200]}")
            
        if r.status_code >= 400:
            err = data.get("error") or data.get("message") or str(data)
            raise Exception(err)
        return data

    def bootstrap(self, update_state=True):
        data = self.api("GET", "/api/bootstrap")
        if update_state: update_state_from_bootstrap(data)
        return data

    def load_catalog(self):
        if STATE["catalog"]: return STATE["catalog"]
        log("Mengambil data katalog benih...", "sync")
        try:
            data = self.api("GET", "/api/catalog?version=3")
            seeds = data.get("seeds") or []
            STATE["catalog"] = {s["seed_id"]: s for s in seeds}
        except Exception:
            pass
        return STATE["catalog"]

    def get_upgrade_preview(self, seed_id):
        try:
            res = self.api("GET", f"/api/seeds/upgrade-preview?seed_id={seed_id}", referer=f"{BASE}/seeds/")
            return res.get("preview", {})
        except Exception:
            return None

    def upgrade_seed(self, seed_id):
        try:
            res = self.api("POST", "/api/seeds/upgrade", {
                "idempotency_key": str(uuid.uuid4()),
                "seed_id": seed_id
            }, referer=f"{BASE}/seeds/")
            return True, res.get("upgraded", {})
        except Exception as e:
            return False, str(e)

    def sell_produce(self):
        count = 0
        if not STATE["produce"]: return count
            
        for seed_id, qty in list(STATE["produce"].items()):
            if qty <= 0: continue
            try:
                self.api("POST", "/api/farm/sell", {
                    "idempotency_key": str(uuid.uuid4()),
                    "seed_id": seed_id,
                    "quantity": qty
                }, referer=f"{BASE}/farm/")
                
                info = STATE["catalog"].get(seed_id, {})
                name = info.get("name", seed_id).capitalize()
                log(f"Menjual Sayuran {self.get_icon(seed_id)} {name} {qty} biji Sukses ✅️", "money")
                
                del STATE["produce"][seed_id]
                count += qty
                time.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                log(f"Gagal menjual {seed_id}: {e}", "err")
                time.sleep(2)
        return count

    def plant(self):
        capacity = max(1, min(int(STATE["total_capacity"]), 24))
        used_plots = {c["plot_index"] for c in STATE["crops"] if c.get("plot_index") is not None}
        empty_plots = [i for i in range(1, capacity + 1) if i not in used_plots]

        if not empty_plots: return 0

        planted_map = {}
        for c in STATE["crops"]:
            sid = c.get("seed_id")
            if sid: planted_map[sid] = planted_map.get(sid, 0) + 1

        available_seeds = []
        for sid, qty in STATE["seeds"].items():
            free = qty - planted_map.get(sid, 0)
            if free > 0:
                available_seeds.append({"seed_id": sid, "free": free})

        if not available_seeds: return 0

        def get_priority(seed_id):
            info = STATE["catalog"].get(seed_id) or {}
            return (int(info.get("base_points") or 0), self.RARITY_RANK.get(str(info.get("rarity", "")).lower(), 0))
        
        available_seeds.sort(key=lambda x: get_priority(x["seed_id"]), reverse=True)

        count = 0
        for plot in empty_plots:
            chosen = next((item for item in available_seeds if item["free"] > 0), None)
            if not chosen: break

            seed_id = chosen["seed_id"]
            try:
                self.api("POST", "/api/farm/plant", {
                    "idempotency_key": str(uuid.uuid4()),
                    "seed_id": seed_id,
                    "plot_index": plot
                }, referer=f"{BASE}/farm/")
                
                info = STATE["catalog"].get(seed_id, {})
                name = info.get("name", seed_id).capitalize()
                durasi = fmt_duration(int(info.get("grow_seconds") or 0))
                
                log(f"Menanam {self.get_icon(seed_id)} {name} ✅️ ({durasi})", "farm")
                
                STATE["seeds"][seed_id] -= 1
                STATE["crops"].append({"crop_id": None, "seed_id": seed_id, "plot_index": plot})
                chosen["free"] -= 1
                count += 1
                time.sleep(random.uniform(1.5, 2.5))
                
            except Exception as e:
                err_msg = str(e)
                if "CHECKPOINT_REQUIRED" in err_msg or "UNAUTHORIZED" in err_msg:
                    log("Cookie Expired! Server meminta Checkpoint. Silakan update cookie lewat Menu [9].", "err")
                    break 
                else:
                    log(f"Gagal menanam di plot {plot}: {e}", "err")
                    break
        return count

    def harvest(self):
        count = 0
        now_ms = int(time.time() * 1000)
        safe_ms = now_ms - 2000 
        
        ready_crops = [c for c in STATE["crops"] if c.get("ready_at_ms", 0) > 0 and c.get("ready_at_ms") <= safe_ms]
        
        for crop in ready_crops:
            crop_id = crop.get("crop_id")
            if not crop_id: continue
            
            try:
                res = self.api("POST", "/api/farm/harvest", {
                    "idempotency_key": str(uuid.uuid4()),
                    "crop_id": crop_id
                }, referer=f"{BASE}/farm/")
                
                STATE["crops"] = [c for c in STATE["crops"] if c.get("crop_id") != crop_id]
                
                h = res.get("harvested", {})
                pts = h.get("point_value", 0)
                icon = self.get_icon(crop.get("seed_id", "?"))
                name = STATE["catalog"].get(crop.get("seed_id"), {}).get("name", crop.get("seed_id")).capitalize()
                
                log(f"Panen {icon} {name} ✅️ (+{pts} Pts)", "farm")
                count += 1
                time.sleep(1)
                
            except Exception as e:
                err_msg = str(e)
                if "CHECKPOINT_REQUIRED" in err_msg or "UNAUTHORIZED" in err_msg:
                    log("Cookie Expired! Server meminta Checkpoint. Silakan update cookie lewat Menu [9].", "err")
                    break 
                else:
                    log(f"Gagal memanen {crop.get('seed_id')}: {e}", "err")
                    
        return count

    def fulfill_orders(self):
        count = 0
        try:
            orders = STATE.get("orders") or []
            if not orders:
                log("Tidak ada order aktif di papan.", "info")
                return 0

            for order in orders:
                order_id = order.get("order_id")
                if not order_id: continue

                try:
                    fres = self.api("POST", "/api/orders/fulfill", {
                        "idempotency_key": str(uuid.uuid4()),
                        "order_id": order_id
                    }, referer=f"{BASE}/orders/")
                    
                    f_data = fres.get("fulfilled", {})
                    coins = f_data.get("total_coins", 0)
                    
                    log(f"✅ Order {order_id[:8]} Terpenuhi! +{coins} Coins", "ok")
                    
                    if "farm_coin_balance" in f_data:
                        STATE["farm_coins"] = f_data["farm_coin_balance"]
                        
                    count += 1
                    time.sleep(1.5)
                    
                except Exception as e:
                    err_msg = str(e)
                    if "ORDER_NOT_READY" in err_msg:
                        log(f"Skip order {order_id[:8]} : Kamu gak punya benih ini", "info")
                    else:
                        log(f"Skip order {order_id[:8]}: {err_msg}", "warn")
        except Exception as e:
            log(f"Error saat Auto Order: {e}", "err")
        return count

    def get_withdrawals(self):
        try:
            res = self.api("GET", "/api/withdrawals", referer=f"{BASE}/withdraw/")
            return res.get("withdrawals", {})
        except Exception as e:
            log(f"Gagal mengambil history withdraw: {e}", "err")
            return None

# ==================== MENU LOGIC ====================
client = None

def do_update_cookie():
    global client
    section("Update Cookie (Manual)")
    print(f"{C.YELLOW}Silakan copy cookie dari ekstensi 'Cookie Master' di Kiwi Browser (klik tombol Copy).{C.R}")
    print(f"{C.GRAY}Format: cc_session_v1=...; cc_farm_clearance_v1=...;{C.R}")
    print(f"{C.GRAY}(Kosongkan lalu tekan Enter jika ingin membatalkan){C.R}")
    
    new_cookie = input(f"\n{C.CYAN}Paste Cookie{C.R} : ").strip()
    if not new_cookie:
        log("Batal update cookie.", "info")
        time.sleep(1)
        return
    
    new_cookie = normalize_cookie(new_cookie)
    
    if "cc_session_v1=" not in new_cookie:
        log("GAGAL! Cookie 'cc_session_v1' (Cookie Login) tidak ditemukan di paste-an lu.", "err")
        log("Pastikan lu nge-copy SEMUA cookie dari ekstensi, jangan cuma clearance-nya aja.", "warn")
        input(f"\n{C.CYAN}Tekan Enter untuk kembali...{C.R}")
        return

    cfg = load_config()
    cfg["cookie"] = new_cookie
    save_config(cfg)
    
    if client:
        client.cfg["cookie"] = new_cookie
        client.update_session_cookie(new_cookie)
        
    log("Cookie berhasil diupdate dan disimpan ke cconfig.json!", "ok")
    log("Mencoba sinkronisasi ulang untuk mengetes cookie...", "sync")
    
    try:
        client.bootstrap(update_state=True)
        if STATE["checkpoint_required"]:
            log("Peringatan: Server MASIH meminta checkpoint (Cookie Expired/Beda IP).", "warn")
        else:
            log("Mantap! Cookie valid. Checkpoint sudah hilang.", "ok")
    except Exception as e:
        log(f"Gagal sinkronisasi: {e}", "err")
    
    input(f"\n{C.CYAN}Tekan Enter untuk kembali...{C.R}")

def do_auto_menanam():
    section("Auto Menanam")
    try:
        log("Sinkronisasi data ladang terbaru...", "sync")
        client.bootstrap(update_state=True)
        client.load_catalog()
        
        if STATE["checkpoint_required"]:
            log("Server meminta Checkpoint (Cookie Expired).", "err")
            log("Silakan update cookie terbaru dari browser lewat Menu [9].", "warn")
            return

        planted = client.plant()
        
        if planted > 0:
            print(f"\n{C.YELLOW}{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}")
            print(f"{C.GREEN}{C.BOLD}  ✅ SELESAI! Berhasil menanam {planted} benih.{C.R}")
            print(f"{C.YELLOW}{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}\n")
            client.bootstrap(update_state=True)
        else:
            log("Tidak ada aktivitas menanam.", "info")
    except Exception as e:
        log(f"Error saat menanam: {e}", "err")

def do_auto_panen():
    log("Memantau tanaman... (Tekan Ctrl+C untuk berhenti)", "info")
    try:
        while True:
            client.bootstrap(update_state=True)
            
            if STATE["checkpoint_required"]:
                clear()
                banner()
                log("Cookie Expired! Server meminta Checkpoint.", "err")
                log("Silakan kembali ke menu dan update cookie lewat Menu [9].", "warn")
                time.sleep(3)
                return

            now_ms = int(time.time() * 1000)
            ready_crops = [c for c in STATE["crops"] if c.get("ready_at_ms", 0) > 0 and c.get("ready_at_ms") <= now_ms]
            
            if ready_crops:
                log(f"Menemukan {len(ready_crops)} tanaman siap panen!", "farm")
                harvested = client.harvest()
                if harvested > 0:
                    print(f"\n{C.GREEN}{C.BOLD}  ✅ BERHASIL MEMANEN {harvested} TANAMAN!{C.R}\n")
                    time.sleep(1)
                    continue 
                    
            if not STATE["crops"]:
                clear()
                banner()
                print(f"{C.YELLOW}Ladang kosong. Tidak ada tanaman untuk dipantau.{C.R}")
                print(f"{C.GRAY}Kembali ke menu dalam 5 detik...{C.R}")
                time.sleep(5)
                return

            clear()
            print(f"{C.CYAN}🪙 {STATE['farm_coins']} Coins | Lv {STATE['farm_level']} | 🌱 {len(STATE['crops'])}/{STATE['total_capacity']} Plot{C.R}")
            print(f"{C.GRAY}{'─' * 56}{C.R}")
            print(f"{C.BOLD}{C.WHITE}DAFTAR TANAMAN (Pantau Realtime){C.R}")
            print(f"{C.GRAY}{'─' * 56}{C.R}")
            
            for crop in STATE["crops"]:
                sid = crop.get("seed_id", "?")
                icon = client.get_icon(sid)
                name = STATE["catalog"].get(sid, {}).get("name", sid).capitalize()
                plot = crop.get("plot_index", "?")
                r_ms = crop.get("ready_at_ms", 0)
                
                if r_ms > 0:
                    rem = max(0, (r_ms - now_ms) // 1000)
                    time_str = fmt_duration(rem)
                    if rem <= 0:
                        print(f"  {icon} {name:<15} [Plot {plot}] : {C.GREEN}{C.BOLD}READY!{C.R}")
                    else:
                        print(f"  {icon} {name:<15} [Plot {plot}] : {C.CYAN}{C.BOLD}{time_str}{C.R}")
                else:
                    print(f"  {icon} {name:<15} [Plot {plot}] : {C.YELLOW}Syncing...{C.R}")
            
            print(f"{C.GRAY}{'─' * 56}{C.R}")
            print(f"{C.GRAY}Tekan Ctrl+C untuk berhenti memantau.{C.R}")
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print()
        log("Menghentikan pemantauan panen... Kembali ke menu utama.", "warn")
        time.sleep(1.5)
    except Exception as e:
        log(f"Error saat memantau panen: {e}", "err")
        time.sleep(3)

def do_auto_farm_loop():
    log("Memulai Mode Auto Farm Loop...", "info")
    
    board_lines = 0

    def erase_board():
        nonlocal board_lines
        if board_lines > 0:
            sys.stdout.write(f"\033[{board_lines}A\033[J")
            board_lines = 0
            sys.stdout.flush()

    def draw_board():
        nonlocal board_lines
        erase_board() 
        lines = 0
        if STATE["crops"]:
            sorted_crops = sorted(STATE["crops"], key=lambda x: x.get("ready_at_ms", 0))
            for crop in sorted_crops:
                sid = crop.get("seed_id", "?")
                icon = client.get_icon(sid)
                name = STATE["catalog"].get(sid, {}).get("name", sid).capitalize()
                r_ms = crop.get("ready_at_ms", 0)
                
                if r_ms > 0:
                    rem = max(0, (r_ms - int(time.time() * 1000)) // 1000)
                    time_str = fmt_duration(rem)
                    if rem <= 0:
                        print(f"{C.LIGHT_GREEN}Menunggu panen{C.R} {icon} {name}: {C.GREEN}{C.BOLD}READY!{C.R}")
                    else:
                        print(f"{C.LIGHT_GREEN}Menunggu panen{C.R} {icon} {name}: {C.CYAN}{C.BOLD}{time_str}{C.R}")
                else:
                    print(f"{C.LIGHT_GREEN}Menunggu panen{C.R} {icon} {name}: {C.YELLOW}Syncing...{C.R}")
                lines += 1
            
            print(f"{C.GRAY}(Tekan Ctrl+C untuk berhenti){C.R}")
            lines += 1
        else:
            print(f"{C.YELLOW}Ladang kosong, menunggu ketersediaan benih...{C.R}")
            lines += 1
        board_lines = lines
        sys.stdout.flush()

    try:
        while True:
            client.bootstrap(update_state=True)
            client.load_catalog()
            
            if STATE["checkpoint_required"]:
                erase_board() 
                log("Cookie Expired! Server meminta Checkpoint.", "err")
                log("Auto Farm berhenti. Silakan update cookie lewat Menu [9].", "warn")
                time.sleep(3)
                return

            now_ms = int(time.time() * 1000)
            safe_ms = now_ms - 2000

            ready_crops = [c for c in STATE["crops"] if c.get("ready_at_ms", 0) > 0 and c.get("ready_at_ms") <= safe_ms]
            capacity = max(1, min(int(STATE["total_capacity"]), 24))
            used_plots = {c["plot_index"] for c in STATE["crops"] if c.get("plot_index") is not None}
            empty_plots = [i for i in range(1, capacity + 1) if i not in used_plots]

            if ready_crops or (empty_plots and len(STATE["seeds"]) > 0):
                erase_board()

                if ready_crops:
                    log(f"Menemukan {len(ready_crops)} tanaman siap panen!", "farm")
                    harvested = client.harvest()
                    if harvested > 0:
                        log(f"✅ Berhasil memanen {harvested} tanaman!", "ok")
                        client.bootstrap(update_state=True) 

                if empty_plots:
                    planted = client.plant()
                    if planted > 0:
                        log(f"✅ Berhasil menanam {planted} benih baru!", "ok")
                        client.bootstrap(update_state=True) 

            if not STATE["crops"] and not empty_plots:
                erase_board()
                log("Ladang kosong dan tidak ada benih. Auto Farm berhenti.", "warn")
                time.sleep(3)
                return

            draw_board()
            time.sleep(1)

    except KeyboardInterrupt:
        print()
        log("Menghentikan mode Auto Farm Loop... Kembali ke menu utama.", "warn")
        time.sleep(1.5)
    except Exception as e:
        log(f"Error pada Auto Farm Loop: {e}", "err")
        time.sleep(3)

def do_auto_jual():
    section("Menjual Hasil Panen")
    try:
        log("Sinkronisasi data gudang terbaru...", "sync")
        client.bootstrap(update_state=True)
        client.load_catalog()
        
        if not STATE["produce"]:
            log("Gudang kosong, tidak ada barang untuk dijual.", "warn")
        else:
            log(f"Menemukan {len(STATE['produce'])} jenis barang di gudang.", "info")
            sold = client.sell_produce()
            
            if sold > 0:
                print(f"\n{C.YELLOW}{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}")
                print(f"{C.GREEN}{C.BOLD}  ✅ SELESAI! Berhasil menjual {sold} barang dari gudang.{C.R}")
                print(f"{C.YELLOW}{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}\n")
            else:
                log("Tidak ada barang yang berhasil dijual.", "err")
        
        client.bootstrap(update_state=True)
        blink_earnings(STATE["pool_est_hc"], STATE["pool_est_usd"])
    except Exception as e:
        log(f"Error saat menjual barang: {e}", "err")

def do_auto_order():
    section("Auto Fulfill Order")
    try:
        log("Sinkronisasi data terbaru...", "sync")
        client.bootstrap(update_state=True)
        
        fulfilled = client.fulfill_orders()
        
        if fulfilled > 0:
            print(f"\n{C.YELLOW}{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}")
            print(f"{C.GREEN}{C.BOLD}  ✅ SELESAI! Berhasil fulfill {fulfilled} order.{C.R}")
            print(f"{C.YELLOW}{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}\n")
            client.bootstrap(update_state=True)
        else:
            log("Tidak ada order yang bisa dipenuhi saat ini.", "info")
    except Exception as e:
        log(f"Error saat Auto Order: {e}", "err")

def do_history_withdraw():
    section("History Withdraw")
    try:
        log("Mengambil data riwayat penarikan...", "sync")
        w_data = client.get_withdrawals()
        if not w_data: return
        
        balance = w_data.get("balance", {})
        credits = balance.get("harvest_credits", 0)
        usd = balance.get("usd_micros", 0) / 1_000_000
        
        print(f"{C.CYAN}💰 Saldo Withdraw:{C.R} {C.YELLOW}{C.BOLD}{credits}{C.R} Harvest Credits (${usd:.4f})")
        if credits == 0:
            print(f"  {C.BOLD}{C.GREEN}ℹ Saldo Kosong / Belum bertambah atau sudah dikirim ke FaucetPay lu bre..{C.R}")
            
        print(f"{C.GRAY}{'─' * 50}{C.R}")
        print(f"{C.BOLD}{C.WHITE}RIWAYAT WITHDRAW:{C.R}")
        print(f"{C.GRAY}{'─' * 50}{C.R}")
        
        history = w_data.get("history", [])
        if not history:
            print("  Belum ada riwayat withdraw.")
        else:
            for item in history:
                dt = datetime.fromtimestamp(item.get("created_at", 0) / 1000).strftime("%Y-%m-%d %H:%M")
                status_raw = item.get("status", "unknown").lower()
                method_raw = item.get("method", "unknown").lower()
                
                if status_raw == "paid":
                    status_text = f"✅ Sukses dikirim ({method_raw.upper()})"
                    status_color = C.GREEN
                elif status_raw == "pending":
                    status_text = "⏳ Pending"
                    status_color = C.YELLOW
                else:
                    status_text = status_raw.upper()
                    status_color = C.WHITE
                
                curr = item.get("currency", "?")
                amt = item.get("amount_atomic", "0")
                usd_amt = item.get("usd_micros", 0) / 1_000_000
                
                print(f"  {C.WHITE}Tanggal Withdraw | {dt}{C.R}")
                print(f"  Total {C.CYAN}{curr} {amt}{C.R} Setara (${usd_amt:.4f})")
                print(f"  Status  {status_color}{status_text}{C.R}")
                print(f"  {C.WHITE}------------------------------------------{C.R}")
        
        print(f"{C.GRAY}{'─' * 50}{C.R}")
    except Exception as e:
        log(f"Error History Withdraw: {e}", "err")

def do_info_pool():
    log("Memantau Info Pool Realtime... (Tekan Ctrl+C untuk berhenti)", "info")
    try:
        while True:
            client.bootstrap(update_state=True)
            ends_ms = STATE["pool_ends_at"]
            
            for i in range(5):
                clear()
                print(f"{C.CYAN}🏆 INFO REWARD POOL & SALDO (REALTIME){C.R}")
                print(f"{C.GRAY}{'─' * 50}{C.R}")
                
                rem_sec = max(0, (ends_ms - int(time.time() * 1000)) // 1000)
                
                print(f"  {C.WHITE}Total Pool   :{C.R} {C.YELLOW}{C.BOLD}{STATE['pool_total_hc']:,}{C.R} Harvest Credits")
                print(f"  {C.WHITE}Berakhir dl  :{C.R} {C.PINK}{C.BOLD}{fmt_duration(rem_sec)}{C.R}")
                
                if STATE["pool_est_hc"] == 0:
                    print(f"  {C.WHITE}Estimasi Anda:{C.R} {C.BOLD}{C.GREEN}Saldo Kosong / Belum bertambah atau sudah dikirim ke FaucetPay lu bre..{C.R}")
                else:
                    print(f"  {C.WHITE}Estimasi Anda:{C.R} {C.GREEN}{STATE['pool_est_hc']} HC (${STATE['pool_est_usd']:.2f}){C.R}")
                
                print(f"{C.GRAY}{'─' * 50}{C.R}")
                print(f"{C.WHITE}🔄 Auto check balance REALTIME{C.R}")
                print(f"{C.CYAN}Tekan CTRL + C untuk kembali ke menu{C.R}\n")
                time.sleep(1)
                
    except KeyboardInterrupt:
        print()
        log("Menghentikan pemantauan pool... Kembali ke menu utama.", "warn")
        time.sleep(1.5)
    except Exception as e:
        log(f"Error saat memantau pool: {e}", "err")
        time.sleep(3)

def do_upgrade_benih():
    section("Upgrade Benih Sayuran")
    try:
        log("Sinkronisasi data benih terbaru...", "sync")
        client.bootstrap(update_state=True)
        client.load_catalog()
        
        if not STATE["seed_info"]:
            log("Tidak ada data benih yang bisa di-upgrade.", "warn")
            return

        upgraded_count = 0
        sorted_seeds = sorted(STATE["seed_info"].items(), key=lambda x: x[1].get("level", 1))
        
        for sid, info in sorted_seeds:
            icon = client.get_icon(sid)
            name = STATE["catalog"].get(sid, {}).get("name", sid).capitalize()
            
            preview = client.get_upgrade_preview(sid)
            if not preview: continue
            
            price = preview.get("price", 0)
            balance = preview.get("farm_coin_balance", 0)
            req_lvl = preview.get("required_farm_level", 1)
            farm_lvl = preview.get("farm_level", 1)
            next_lvl = preview.get("next_level", 1)

            if farm_lvl < req_lvl:
                log(f"Gagal upgrade {icon} {name}: Butuh Farm Level {req_lvl}", "warn")
                continue

            if price > balance:
                log(f"Coin mu gak cukup Bre! Macul dulu sana", "err")
                break
                
            log(f"Mencoba upgrade {icon} {name} (Harga: {price} Coins)...", "upgrade")
            success, res_data = client.upgrade_seed(sid)
            
            if success:
                level_after = res_data.get("level_after", next_lvl)
                log(f"Sayuran {icon} {name} Sukses Upgrade ke Level {level_after}✅️", "ok")
                upgraded_count += 1
                client.bootstrap(update_state=True)
            else:
                err_msg = str(res_data)
                if "CHECKPOINT_REQUIRED" in err_msg or "UNAUTHORIZED" in err_msg:
                    log("Cookie Expired! Server meminta Checkpoint. Silakan update cookie lewat Menu [9].", "err")
                    break
                else:
                    log(f"Gagal upgrade {icon} {name}: {res_data}", "err")
            time.sleep(1.5)
            
        if upgraded_count > 0:
            print(f"\n{C.YELLOW}{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}")
            print(f"{C.GREEN}{C.BOLD}  ✅ SELESAI! Berhasil upgrade {upgraded_count} level benih.{C.R}")
            print(f"{C.YELLOW}{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}\n")
    except Exception as e:
        log(f"Error saat upgrade benih: {e}", "err")

def main_menu():
    global client
    cfg = ensure_config()
    
    if not cfg.get("cookie"):
        log("Cookie kosong di cconfig.json", "err")
        return

    client = FarmClient(cfg)
    
    try:
        client.bootstrap(update_state=True)
        client.load_catalog()
    except Exception:
        pass

    while True:
        banner()
        
        status_checkpoint = f"{C.RED}Butuh Update Cookie{C.R}" if STATE["checkpoint_required"] else f"{C.GREEN}Clear (Aman){C.R}"
        
        print(f"{C.CYAN}Status:{C.R} 🪙 {STATE['farm_coins']} Coins | Lv {STATE['farm_level']} | 🌱 {len(STATE['crops'])}/{STATE['total_capacity']} Plot")
        print(f"{C.CYAN}Checkpoint:{C.R} {status_checkpoint}")
        print(f"{C.GRAY}{'─' * 56}{C.R}")
        print(f"  {C.BOLD}{C.WHITE}MENU UTAMA{C.R}")
        print(f"  {C.YELLOW}[1]{C.R} Auto Menanam")
        print(f"  {C.YELLOW}[2]{C.R} Auto Panen (Realtime Monitor)")
        print(f"  {C.YELLOW}[3]{C.R} Auto Farm Loop (Tanam & Panen Otomatis)")
        print(f"  {C.YELLOW}[4]{C.R} Auto Fulfill Order")
        print(f"  {C.YELLOW}[5]{C.R} Menjual Hasil Panen") 
        print(f"  {C.YELLOW}[6]{C.R} Upgrade Benih Sayuran") 
        print(f"  {C.YELLOW}[7]{C.R} Info Saldo & Pool Realtime") 
        print(f"  {C.YELLOW}[8]{C.R} History Withdraw") 
        print(f"  {C.GREEN}[9]{C.R} {C.BOLD}Update Cookie Terbaru{C.R}")
        print(f"  {C.YELLOW}[0]{C.R} Keluar")
        print(f"{C.GRAY}{'─' * 56}{C.R}")
        
        try:
            pilihan = input(f"{C.CYAN}Pilih menu (0-9): {C.R}").strip()
            if pilihan == "1":
                do_auto_menanam()
                input(f"\n{C.CYAN}Tekan Enter untuk kembali...{C.R}")
            elif pilihan == "2":
                do_auto_panen()
            elif pilihan == "3":
                do_auto_farm_loop()
            elif pilihan == "4":
                do_auto_order()
                input(f"\n{C.CYAN}Tekan Enter untuk kembali...{C.R}")
            elif pilihan == "5": 
                do_auto_jual()
                input(f"\n{C.CYAN}Tekan Enter untuk kembali...{C.R}")
            elif pilihan == "6": 
                do_upgrade_benih()
                input(f"\n{C.CYAN}Tekan Enter untuk kembali...{C.R}")
            elif pilihan == "7": 
                do_info_pool()
            elif pilihan == "8": 
                do_history_withdraw()
                input(f"\n{C.CYAN}Tekan Enter untuk kembali...{C.R}")
            elif pilihan == "9":
                do_update_cookie()
            elif pilihan == "0":
                print(f"\n{C.YELLOW}Keluar...{C.R}")
                break
            else:
                log("Pilihan tidak valid!", "err")
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{C.YELLOW}Program dihentikan.{C.R}")
            break

if __name__ == "__main__":
    main_menu()