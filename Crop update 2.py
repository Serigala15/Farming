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
    "custom_seeds": [], 
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
    c1 = "\033[38;5;51m"
    c2 = "\033[38;5;45m"
    c3 = "\033[38;5;39m"
    c4 = "\033[38;5;33m"
    c5 = "\033[38;5;27m"
    c6 = "\033[38;5;21m"
    bold = "\033[1m"
    reset = "\033[0m"

    print(f"""{bold}{c1}            ███████╗ █████╗ ██████╗ ███╗   ███╗
            {c2}██╔════╝██╔══██╗██╔══██╗████╗ ████║
            {c3}█████╗  ███████║██████╔╝██╔████╔██║
            {c4}██╔══╝  ██╔══██║██╔══██╗██║╚██╔╝██║
            {c5}██║     ██║  ██║██║  ██║██║ ╚═╝ ██║
            {c6}╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
    {reset}""")
    print(f"{C.YELLOW}{bold}                 CRYPTOCROPS Versi Mantap!{reset}")
    print(f"{c1}{bold}               Mod by Jendela Semesta REBORN{reset}")
    print(f"{C.WHITE}{bold}                    Join my Group Telegram{reset}")
    print(f"{C.BOLD}{C.ORANGE}                https://t.me/jendelasemesta{reset}\n")

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

    # === FITUR AUTORELOAD CONFIG ===
    def reload_config_if_updated(self):
        new_cfg = load_config()
        if new_cfg and new_cfg.get("cookie"):
            new_cookie = new_cfg.get("cookie")
            if new_cookie != self.cfg.get("cookie"):
                self.cfg["cookie"] = new_cookie
                self.update_session_cookie(new_cookie)
                log("Cookie baru terdeteksi di cconfig.json! Autoreload berhasil ✅", "ok")
                return True
        return False

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

        if STATE.get("custom_seeds"):
            available_seeds = [s for s in available_seeds if s["seed_id"] in STATE["custom_seeds"]]
            if not available_seeds:
                return 0

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
                    log("Cookie Expired! Server meminta Checkpoint.", "err")
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
                    log("Cookie Expired! Server meminta Checkpoint.", "err")
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