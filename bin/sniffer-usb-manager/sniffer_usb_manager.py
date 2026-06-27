#!/usr/bin/env python3
"""
USB Manager
Desktop tool to switch between Ubertooth One, nRF Sniffer (Raytac MDBT50Q-CX etc.),
HackRF, and Onboard Bluetooth without them fighting over USB interfaces.

It safely unbinds devices from btusb / cdc_acm / etc. so the specialized tools
(ubertooth-btle, nRF Sniffer Wireshark extcap / Kismet, hackrf tools, etc.)
can get exclusive/clean access.

Usage (GUI - best):
  ./launch.sh
  Then click the big "Full Optimized Setup" button once.
  After that the tool is basically magic.

Usage (CLI):
  ./launch.sh --full-setup          # Do the complete one-time optimization
  ./launch.sh --ubertooth
  ./launch.sh --nrf
  ./launch.sh --hackrf
  ./launch.sh --onboard-only
  ./launch.sh --normal
  ./launch.sh --install-udev
  ./launch.sh --install-sudoers

Best experience (one-time):
  Launch the GUI and click the big "🚀 Full Optimized Setup (Recommended)" button.
  This installs:
    • Passwordless sudo (zero prompts forever for this tool)
    • udev rules (easy permissions + devices auto-unbind from btusb/cdc_acm the moment you plug them in)

  After that you can literally just plug in Ubertooth, Raytac/nRF, or HackRF and start using your tools.
  The manager now understands Ubertooth One + Raytac MDBT50Q-CX + HackRF together.
"""

import argparse
import subprocess
import sys
import re
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from dataclasses import dataclass
from typing import List, Optional


# =============================================================================
# Device definitions (exact VID:PID matches)
# The code also does fuzzy matching on product strings for Raytac, other nRF52840
# dongles, etc. So most third-party nRF sniffers should now appear automatically.
# =============================================================================
KNOWN_DEVICES = [
    {
        "name": "Ubertooth One",
        "vid": "1d50",
        "pid": "6002",
        "mode": "ubertooth",
        "description": "Ubertooth One (main firmware)"
    },
    {
        "name": "Ubertooth One (DFU)",
        "vid": "1d50",
        "pid": "6003",
        "mode": "ubertooth",
        "description": "Ubertooth One (bootloader/DFU mode)"
    },
    {
        "name": "nRF Sniffer",
        "vid": "1915",
        "pid": "522a",
        "mode": "nrf",
        "description": "Nordic nRF Sniffer for Bluetooth LE (nRF52840)"
    },
    {
        "name": "nRF Sniffer (alt)",
        "vid": "1915",
        "pid": "521f",
        "mode": "nrf",
        "description": "Nordic nRF52840 Dongle (other firmware)"
    },
    # Your onboard Realtek (detected on your machine)
    {
        "name": "Onboard Bluetooth",
        "vid": "0bda",
        "pid": "4853",
        "mode": "onboard",
        "description": "Built-in Realtek Bluetooth"
    },
    # HackRF (user also has this for general SDR / 2.4 GHz work alongside BT sniffers)
    {
        "name": "HackRF One",
        "vid": "1d50",
        "pid": "6089",
        "mode": "hackrf",
        "description": "HackRF One (main)"
    },
    {
        "name": "HackRF One (DFU)",
        "vid": "1fc9",
        "pid": "000c",
        "mode": "hackrf",
        "description": "HackRF One (DFU / bootloader)"
    },
]

# Modes that conflict with each other (the two BT sniffers + sometimes onboard)
# HackRF can usually coexist but when doing pure 2.4GHz SDR work you often want
# the dedicated BT sniffers (Ubertooth/Raytac) unbound so they don't claim USB
# bandwidth or cause interference.
CONFLICTING_MODES = {"ubertooth", "nrf"}


@dataclass
class DetectedDevice:
    name: str
    vid: str
    pid: str
    mode: str
    bus: str
    device: str
    bound_to_btusb: bool
    sysfs_path: Optional[str] = None


# =============================================================================
# Low-level USB / driver manipulation
# =============================================================================

HELPER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "priv-helper.sh")


def run_privileged(commands: List[str]) -> tuple[bool, str]:
    """
    Run privileged operations using the small audited helper script.

    This is much safer than arbitrary shell scripts, and makes it easy
    to give passwordless sudo just for this tool.

    The helper only allows a tiny whitelist of unbind/bind/reload operations.
    """
    if not commands:
        return True, "Nothing to do"

    if not os.path.isfile(HELPER_PATH):
        return False, f"Missing privileged helper: {HELPER_PATH}"

    outputs = []
    overall_success = True

    for cmdline in commands:
        # We now pass structured commands to the helper instead of raw shell
        # The old "build_action_commands" produces lines like:
        #   echo "1-5:1.0" > "/sys/bus/usb/drivers/cdc_acm/unbind" ...
        # We parse the important ones and translate them.

        m = re.search(r'echo\s+"?([^"\s]+)"?\s*>\s*["\']?/sys/bus/usb/drivers/([^/]+)/([a-z]+)', cmdline)
        if m:
            iface, driver, action = m.groups()
            if action == "unbind":
                full_cmd = [HELPER_PATH, "unbind", iface, driver]
            elif action == "bind":
                full_cmd = [HELPER_PATH, "bind", iface, driver]
            else:
                full_cmd = None
        elif "modprobe -r btusb" in cmdline or "modprobe btusb" in cmdline:
            full_cmd = [HELPER_PATH, "reload-btusb"]
        else:
            full_cmd = None

        if not full_cmd:
            # Unknown command - skip safely
            outputs.append(f"Skipped unknown operation: {cmdline[:80]}")
            continue

        # Prefer direct sudo (nopasswd) if we have the passwordless rule configured.
        # This avoids repeated polkit/pkexec password dialogs after the one-time setup.
        if is_passwordless_sudo_configured():
            try:
                proc = subprocess.run(
                    ["sudo"] + full_cmd,
                    capture_output=True, text=True, timeout=60
                )
                if proc.returncode == 0:
                    outputs.append(proc.stdout.strip() or proc.stderr.strip())
                    continue
                else:
                    overall_success = False
                    outputs.append(f"sudo (passwordless) failed: {proc.stderr.strip() or proc.stdout.strip()}")
                    continue
            except Exception as e:
                overall_success = False
                outputs.append(f"sudo (passwordless) error: {e}")
                continue

        # Try pkexec first (for systems without the sudoers rule yet)
        try:
            proc = subprocess.run(
                ["pkexec"] + full_cmd,
                capture_output=True, text=True, timeout=60
            )
            if proc.returncode != 0:
                # pkexec failed or not available → try sudo
                raise FileNotFoundError
            outputs.append(proc.stdout.strip() or proc.stderr.strip())
            continue
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        except Exception as e:
            outputs.append(f"pkexec error: {e}")

        # sudo path (this is the one showing up as PID 2482 for you)
        askpass = os.environ.get("SUDO_ASKPASS")
        if not askpass:
            for candidate in [
                "/usr/libexec/openssh/ssh-askpass",
                "/usr/bin/ssh-askpass",
                "/usr/bin/ksshaskpass",
                "/usr/bin/lxqt-sudo",
            ]:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    askpass = candidate
                    break

        sudo_base = ["sudo", "-A"] if askpass else ["sudo"]
        env = os.environ.copy()
        if askpass:
            env["SUDO_ASKPASS"] = askpass

        try:
            proc = subprocess.run(
                sudo_base + full_cmd,
                capture_output=True, text=True, env=env, timeout=60
            )
            if proc.returncode == 0:
                outputs.append(proc.stdout.strip() or proc.stderr.strip())
            else:
                overall_success = False
                outputs.append(f"sudo failed: {proc.stderr.strip() or proc.stdout.strip()}")
        except Exception as e:
            overall_success = False
            outputs.append(f"sudo error: {e}")

    return overall_success, "\n".join(o for o in outputs if o).strip() or "Done"


def run_privileged_action(*args: str) -> tuple[bool, str]:
    """
    Directly invoke the privileged helper with specific arguments.
    Example:
        run_privileged_action("install-sudoers")
        run_privileged_action("unbind", "1-5:1.0", "cdc_acm")
    """
    if not os.path.isfile(HELPER_PATH):
        return False, f"Missing privileged helper: {HELPER_PATH}"

    full_cmd = [HELPER_PATH] + list(args)

    # Prefer direct sudo (nopasswd) if we have the passwordless rule configured.
    # This avoids repeated polkit/pkexec password dialogs after the one-time setup.
    if is_passwordless_sudo_configured():
        try:
            proc = subprocess.run(
                ["sudo"] + full_cmd,
                capture_output=True, text=True, timeout=60
            )
            if proc.returncode == 0:
                return True, proc.stdout.strip() or proc.stderr.strip() or "Success"
            else:
                return False, proc.stderr.strip() or proc.stdout.strip() or "Failed"
        except Exception as e:
            return False, str(e)

    # Try pkexec (for systems without the sudoers rule yet)
    try:
        proc = subprocess.run(
            ["pkexec"] + full_cmd,
            capture_output=True, text=True, timeout=60
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip() or proc.stderr.strip() or "Success"
        # pkexec returned non-zero — fall through to sudo
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    except Exception as e:
        pass  # fall through

    # sudo with askpass support
    askpass = os.environ.get("SUDO_ASKPASS")
    if not askpass:
        for candidate in [
            "/usr/libexec/openssh/ssh-askpass",
            "/usr/bin/ssh-askpass",
            "/usr/bin/ksshaskpass",
            "/usr/bin/lxqt-sudo",
        ]:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                askpass = candidate
                break

    sudo_base = ["sudo", "-A"] if askpass else ["sudo"]
    env = os.environ.copy()
    if askpass:
        env["SUDO_ASKPASS"] = askpass

    try:
        proc = subprocess.run(
            sudo_base + full_cmd,
            capture_output=True, text=True, env=env, timeout=60
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip() or proc.stderr.strip() or "Success"
        else:
            return False, proc.stderr.strip() or proc.stdout.strip() or "Failed"
    except Exception as e:
        return False, str(e)


def is_passwordless_sudo_configured() -> bool:
    """Check if the sudoers rule for our helper exists and looks valid."""
    rule_file = "/etc/sudoers.d/sniffer-usb-manager"
    if not os.path.isfile(rule_file):
        return False
    try:
        with open(rule_file) as f:
            content = f.read()
        return HELPER_PATH in content
    except Exception:
        return False


def is_udev_optimized() -> bool:
    """Check if our udev rules for easy permissions + auto-unbind are installed."""
    rule_file = "/etc/udev/rules.d/99-sniffer-usb.rules"
    if not os.path.isfile(rule_file):
        return False
    try:
        with open(rule_file) as f:
            content = f.read()
        return "1d50:6002" in content and "1915:522a" in content
    except Exception:
        return False


def find_bound_interfaces(vid: str, pid: str) -> List[tuple[str, str]]:
    """
    Find all interfaces currently bound to *any* driver for a given VID:PID.
    Returns list of (interface_name, driver_name) tuples.
    Example: [('1-8:1.0', 'btusb'), ('1-8:1.1', 'btusb')]
    """
    results: List[tuple[str, str]] = []
    base = "/sys/bus/usb/devices"

    try:
        for entry in os.listdir(base):
            # Match devices like "1-8" or "1-8.3" etc.
            dev_path = os.path.join(base, entry)
            vendor_file = os.path.join(dev_path, "idVendor")
            product_file = os.path.join(dev_path, "idProduct")

            if not (os.path.isfile(vendor_file) and os.path.isfile(product_file)):
                continue

            try:
                with open(vendor_file) as f:
                    v = f.read().strip().lower()
                with open(product_file) as f:
                    p = f.read().strip().lower()
            except Exception:
                continue

            if v != vid.lower() or p != pid.lower():
                continue

            # This is our device. Now look for interface subdirectories (1-8:1.0 etc.)
            for iface in os.listdir(dev_path):
                if not re.match(r'^\d+-\d+(?:\.\d+)?:\d+\.\d+$', iface):
                    continue

                iface_path = os.path.join(dev_path, iface)
                driver_link = os.path.join(iface_path, "driver")

                if os.path.islink(driver_link):
                    try:
                        driver = os.path.basename(os.readlink(driver_link))
                        results.append((iface, driver))
                    except Exception:
                        pass
    except FileNotFoundError:
        pass

    return results


def find_btusb_interfaces(vid: str, pid: str) -> List[str]:
    """Backwards-compatible wrapper: return only interfaces bound to btusb."""
    return [iface for (iface, drv) in find_bound_interfaces(vid, pid) if drv == "btusb"]


def get_detected_devices() -> List[DetectedDevice]:
    """Scan lsusb and sysfs to find all relevant devices and their btusb binding state."""
    detected: List[DetectedDevice] = []

    try:
        output = subprocess.check_output(["lsusb"], text=True)
    except Exception:
        return detected

    for line in output.splitlines():
        # Bus 001 Device 006: ID 1d50:6002 OpenMoko, Inc. Ubertooth One
        m = re.search(r'Bus (\d+) Device (\d+): ID ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})', line)
        if not m:
            continue

        bus, dev, vid, pid = m.groups()
        vid = vid.lower()
        pid = pid.lower()

        # Match against known devices
        for kdev in KNOWN_DEVICES:
            if kdev["vid"].lower() == vid and kdev["pid"].lower() == pid:
                bound_ifaces = find_bound_interfaces(vid, pid)
                bound = len(bound_ifaces) > 0
                # Store a hint about current driver in the name for display
                driver_hint = ""
                if bound_ifaces:
                    drivers = sorted(set(drv for _, drv in bound_ifaces))
                    driver_hint = f" ({', '.join(drivers)})"

                detected.append(DetectedDevice(
                    name=kdev["name"] + driver_hint,
                    vid=vid,
                    pid=pid,
                    mode=kdev["mode"],
                    bus=bus,
                    device=dev,
                    bound_to_btusb=bound
                ))
                break

    # --- Fallback: Fuzzy + VID-based detection for nRF52840 / Raytac / other Nordic dongles ---
    # Broad matching so devices like Raytac MDBT50Q-CX, Adafruit nRF52840, etc. are detected
    nrf_keywords = ["nrf", "nordic", "raytac", "mdbt50", "52840", "sniffer", "ble", "nordic semiconductor"]
    nrf_vids = {"1915", "239a", "2e73", "0d28"}  # Common Nordic / nRF52840 VIDs (including many Raytac-based dongles)

    for line in output.splitlines():
        lower_line = line.lower()
        m = re.search(r'Bus (\d+) Device (\d+): ID ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+(.*)', line)
        if not m:
            continue

        bus, dev, vid, pid, product = m.groups()
        vid = vid.lower()
        pid = pid.lower()

        # Skip if we already matched it with exact KNOWN_DEVICES
        if any(d.vid == vid and d.pid == pid for d in detected):
            continue

        is_nrf = False
        if vid in nrf_vids:
            is_nrf = True
        elif any(kw in lower_line for kw in nrf_keywords):
            is_nrf = True

        if not is_nrf:
            continue

        # Make a friendly name
        name = product.strip()
        if len(name) > 50:
            name = name[:47] + "..."
        if not name:
            name = f"Unknown nRF device ({vid}:{pid})"

        # Driver info
        bound_ifaces = find_bound_interfaces(vid, pid)
        bound = len(bound_ifaces) > 0
        driver_hint = ""
        if bound_ifaces:
            drivers = sorted(set(drv for _, drv in bound_ifaces))
            driver_hint = f" ({', '.join(drivers)})"

        detected.append(DetectedDevice(
            name=f"{name}{driver_hint}",
            vid=vid,
            pid=pid,
            mode="nrf",
            bus=bus,
            device=dev,
            bound_to_btusb=bound
        ))

    return detected


def build_action_commands(mode: str, detected: List[DetectedDevice]) -> List[str]:
    """
    Return a list of shell commands that should be run privileged
    to put the system into the desired mode.
    """
    commands: List[str] = []

    # The BT sniffer dongles we usually want to manage exclusively for raw access
    bt_sniffer_targets = [d for d in detected if d.mode in ("ubertooth", "nrf")]

    # HackRF devices (for status / optional prep)
    hackrf_targets = [d for d in detected if d.mode == "hackrf"]

    if mode in ("ubertooth", "nrf", "onboard-only", "hackrf"):
        # Unbind the BT sniffers (Ubertooth + Raytac/nRF) so they are free for
        # their specialized tools. When going to HackRF mode we also unbind them
        # so the USB bus is clean for SDR work and 2.4 GHz interference is minimized.
        for d in bt_sniffer_targets:
            for iface, driver in find_bound_interfaces(d.vid, d.pid):
                unbind_path = f"/sys/bus/usb/drivers/{driver}/unbind"
                commands.append(f'echo "{iface}" > "{unbind_path}" 2>/dev/null || true')

        # For HackRF we could also do other prep here in future (rfkill etc.)
        # but the main value is the status + unbinding the BT dongles.

    elif mode == "normal":
        # Try to give the kernel a chance to reclaim the devices
        for d in detected:
            if d.mode in ("ubertooth", "nrf", "onboard"):
                # sysfs names are usually like "1-4" or "3-2.1", not zero-padded
                bus = d.bus.lstrip("0") or "1"
                devnum = str(int(d.device))   # remove leading zeros
                dev_id = f"{bus}-{devnum}"
                if dev_id:
                    commands.append(f'echo "{dev_id}" > /sys/bus/usb/drivers/btusb/bind 2>/dev/null || true')
                    commands.append(f'echo "{dev_id}:1.0" > /sys/bus/usb/drivers/btusb/bind 2>/dev/null || true')

        # Most reliable way to get normal Bluetooth behavior back
        commands.append("modprobe -r btusb 2>/dev/null || true")
        commands.append("modprobe btusb 2>/dev/null || true")

    return commands


def perform_action(mode: str, silent: bool = False) -> tuple[bool, str]:
    """High level action runner used by both CLI and GUI."""
    detected = get_detected_devices()
    commands = build_action_commands(mode, detected)

    if not commands:
        return True, "No devices needed unbinding (already in desired state)."

    success, output = run_privileged(commands)

    if success:
        # Re-scan so the caller sees fresh state
        new_state = get_detected_devices()
        msg = f"Successfully switched to {mode} mode."
        if output:
            msg += f"\n\nDetails:\n{output}"
        return True, msg
    else:
        return False, f"Failed to apply changes:\n{output}"


# =============================================================================
# GUI
# =============================================================================

class SnifferUSBManagerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("USB Manager")
        root.geometry("640x720")
        root.resizable(True, True)

        self.style = ttk.Style()
        self._setup_ui()
        self.refresh_status()

    def _setup_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        # Title
        ttk.Label(main, text="USB Sniffer Device Switcher", font=("sans", 14, "bold")).pack(pady=(0, 8))

        # Status frame
        status_frame = ttk.LabelFrame(main, text="Currently detected devices", padding=8)
        status_frame.pack(fill="x", pady=4)

        self.status_text = tk.Text(status_frame, height=5, width=58, font=("monospace", 9),
                                   state="disabled", wrap="none", relief="flat",
                                   background="#f5f5f5")
        self.status_text.pack(fill="x")

        # Action buttons
        action_frame = ttk.LabelFrame(main, text="Activate mode (others will be brought down)", padding=8)
        action_frame.pack(fill="x", pady=8)

        # Let buttons size naturally to their text (avoids truncation)
        for text, mode in [
            ("Activate Ubertooth One", "ubertooth"),
            ("Activate nRF Sniffer (Raytac MDBT50Q-CX etc.)", "nrf"),
            ("Prepare for HackRF (unbind BT sniffers for clean SDR)", "hackrf"),
            ("Onboard Bluetooth Only (unbind dongles)", "onboard-only"),
            ("Normal Mode (rebind everything to kernel)", "normal"),
        ]:
            ttk.Button(action_frame, text=text,
                       command=lambda m=mode: self.run_action(m)).pack(fill="x", pady=3, padx=4)

        # System optimization / setup section (maximum functionality)
        setup_frame = ttk.LabelFrame(main, text="System Optimization (do this once for best experience)", padding=8)
        setup_frame.pack(fill="x", pady=6)

        self.setup_status = ttk.Label(setup_frame, text="Checking setup status...", font=("sans", 9))
        self.setup_status.pack(anchor="w", pady=(0, 4))

        # Prominent full setup button
        self.full_setup_btn = ttk.Button(setup_frame, text="🚀 Full Optimized Setup (Recommended)",
                                         command=self.run_full_setup)
        self.full_setup_btn.pack(fill="x", pady=3)

        # Individual controls (advanced)
        small_btns = ttk.Frame(setup_frame)
        small_btns.pack(fill="x", pady=(4, 0))

        ttk.Button(small_btns, text="Install Passwordless Sudo",
                   command=self.install_sudoers).pack(side="left", padx=(0, 4))
        ttk.Button(small_btns, text="Install Udev Rules",
                   command=self.install_udev).pack(side="left", padx=4)
        ttk.Button(small_btns, text="Remove All Rules",
                   command=self.remove_all_rules).pack(side="left", padx=4)

        ttk.Button(small_btns, text="Diagnostics",
                   command=self.show_diagnostics).pack(side="right")

        # Bottom row - use a more robust layout
        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=8)

        ttk.Button(bottom, text="Refresh", command=self.refresh_status).pack(side="left", padx=(0, 6))
        ttk.Button(bottom, text="Show All USB Devices", command=self.show_all_usb).pack(side="left", padx=6)
        ttk.Button(bottom, text="Close", command=self.root.destroy).pack(side="right")

        # Log
        log_frame = ttk.LabelFrame(main, text="Action log", padding=6)
        log_frame.pack(fill="both", expand=True, pady=4)

        self.log = scrolledtext.ScrolledText(log_frame, height=5, font=("monospace", 8),
                                             state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)

    def log_message(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.root.update_idletasks()

    def refresh_status(self):
        detected = get_detected_devices()

        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")

        if not detected:
            self.status_text.insert("end", "No devices detected.\n")
            self.status_text.insert("end", "Plug in your devices (Ubertooth One, Raytac/nRF Sniffer, HackRF, etc.) and click Refresh.\n")
            self.status_text.insert("end", "Ubertooth + nRF/Raytac + HackRF are now all detected and manageable.\n")
        else:
            for d in detected:
                bound = "BOUND to btusb" if d.bound_to_btusb else "FREE (good for tools)"
                self.status_text.insert("end", f"{d.name}\n")
                self.status_text.insert("end", f"  {d.vid}:{d.pid}  •  {bound}\n\n")

        self.status_text.configure(state="disabled")
        self.refresh_setup_status()

    def show_all_usb(self):
        """Show every USB device currently connected (very useful for unknown dongles like Raytac)."""
        try:
            output = subprocess.check_output(["lsusb", "-v"], text=True, stderr=subprocess.STDOUT, timeout=10)
        except Exception as e:
            output = f"Failed to run lsusb -v:\n{e}"

        # Simpler view: use plain lsusb + try to get product strings
        try:
            simple = subprocess.check_output(["lsusb"], text=True)
        except Exception:
            simple = "lsusb failed"

        win = tk.Toplevel(self.root)
        win.title("All USB Devices (Debug)")
        win.geometry("850x600")

        txt = scrolledtext.ScrolledText(win, font=("monospace", 9))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", "=== lsusb (simple) ===\n" + simple + "\n\n=== lsusb -v (detailed) ===\n" + output[:15000])
        txt.configure(state="disabled")

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)

    def run_action(self, mode: str):
        self.log_message(f"→ Switching to {mode} mode...")

        # Run in a way that doesn't freeze the GUI
        self.root.after(50, lambda: self._run_action_bg(mode))

    def _run_action_bg(self, mode: str):
        success, message = perform_action(mode)
        self.log_message(message)
        if success:
            self.refresh_status()
        else:
            messagebox.showerror("Error", message)

    def refresh_setup_status(self):
        sudo_ok = is_passwordless_sudo_configured()
        udev_ok = is_udev_optimized()

        if sudo_ok and udev_ok:
            self.setup_status.config(
                text="✅ Perfect setup active — passwordless + devices auto-ready on plug-in",
                foreground="#006400")
            self.full_setup_btn.config(state="disabled")
        elif sudo_ok:
            self.setup_status.config(
                text="⚠️ Passwordless sudo is on, but udev rules missing (plug & play not optimized)",
                foreground="#b8860b")
            self.full_setup_btn.config(state="normal")
        elif udev_ok:
            self.setup_status.config(
                text="⚠️ Udev rules present, but you will still get password prompts",
                foreground="#b8860b")
            self.full_setup_btn.config(state="normal")
        else:
            self.setup_status.config(
                text="❌ Not optimized — click the big button below for best experience (one-time)",
                foreground="#8b0000")
            self.full_setup_btn.config(state="normal")

    def run_full_setup(self):
        msg = ("This will perform the complete recommended setup:\n\n"
               "• Install passwordless sudo (no more password prompts ever)\n"
               "• Install udev rules for easy device access + automatic unbind\n"
               "  from conflicting drivers the moment you plug in a device\n\n"
               "After this you can plug Ubertooth or nRF Sniffer and they will\n"
               "be immediately ready for your tools with zero extra steps.\n\n"
               "Continue?")
        if messagebox.askyesno("Full Optimized Setup", msg):
            self.log_message("→ Running FULL OPTIMIZED SETUP (this may ask for password once)...")
            self.root.after(80, self._run_full_setup_bg)

    def _run_full_setup_bg(self):
        # Do sudoers first
        ok1, m1 = run_privileged_action("install-sudoers")
        self.log_message("Sudoers: " + (m1 or "done"))

        # Then udev
        ok2, m2 = run_privileged_action("install-udev")
        self.log_message("Udev: " + (m2 or "done"))

        if ok1 and ok2:
            messagebox.showinfo("Setup Complete",
                                "✅ Full optimization finished!\n\n"
                                "• No more password prompts for this tool\n"
                                "• Plug in devices → they auto-unbind from bad drivers\n"
                                "• Permissions are wide open for your sniffing tools\n\n"
                                "Click Refresh to see updated status.")
        else:
            messagebox.showerror("Setup Issues", f"Some steps had problems:\n\nSudoers: {m1}\nUdev: {m2}")

        self.refresh_status()

    def install_sudoers(self):
        self.log_message("→ Installing passwordless sudo rule...")
        success, message = run_privileged_action("install-sudoers")
        self.log_message(message)
        if success:
            messagebox.showinfo("Done", "Passwordless sudo installed.")
        else:
            messagebox.showerror("Failed", message)
        self.refresh_status()

    def install_udev(self):
        self.log_message("→ Installing udev rules (permissions + auto-unbind)...")
        success, message = run_privileged_action("install-udev")
        self.log_message(message)
        if success:
            messagebox.showinfo("Done", "Udev rules installed.\n\n"
                                        "Try unplugging and replugging your devices — they should\n"
                                        "now auto-prepare themselves for sniffing tools.")
        else:
            messagebox.showerror("Failed", message)
        self.refresh_status()

    def remove_all_rules(self):
        if not messagebox.askyesno("Remove Rules", "Remove both passwordless sudo and udev rules?"):
            return
        self.log_message("→ Removing all custom rules...")
        s1, m1 = run_privileged_action("remove-sudoers")
        s2, m2 = run_privileged_action("remove-udev")
        self.log_message(m1)
        self.log_message(m2)
        messagebox.showinfo("Done", "Rules removed.")
        self.refresh_status()

    def show_diagnostics(self):
        try:
            lsusb = subprocess.check_output(["lsusb", "-t"], text=True, stderr=subprocess.STDOUT)
        except Exception as e:
            lsusb = f"lsusb failed: {e}"

        try:
            bound = subprocess.check_output(
                ["bash", "-c", "for d in /sys/bus/usb/drivers/btusb/*/idVendor; do [ -f \"$d\" ] && echo \"$(dirname $d) -> $(cat $d):$(cat $(dirname $d)/idProduct)\"; done"],
                text=True, stderr=subprocess.STDOUT)
        except Exception:
            bound = "(no btusb devices or error)"

        diag = f"=== lsusb -t (driver tree) ===\n{lsusb}\n\n=== Currently bound to btusb ===\n{bound or '(none)'}"

        # Show in a simple dialog
        win = tk.Toplevel(self.root)
        win.title("Diagnostics")
        win.geometry("700x500")
        txt = scrolledtext.ScrolledText(win, font=("monospace", 9))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", diag)
        txt.configure(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)


# =============================================================================
# CLI entry point
# =============================================================================

def cli_main():
    parser = argparse.ArgumentParser(description="Manage USB devices for Ubertooth One / nRF Sniffer (Raytac MDBT50Q-CX) / HackRF / Onboard Bluetooth")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--gui", action="store_true", help="Launch graphical interface")
    group.add_argument("--ubertooth", action="store_true", help="Prepare for Ubertooth One use")
    group.add_argument("--nrf", "--nrf-sniffer", action="store_true", help="Prepare for nRF Sniffer use (Raytac MDBT50Q-CX etc.)")
    group.add_argument("--hackrf", action="store_true", help="Prepare for HackRF use (unbinds BT sniffers for clean SDR / 2.4 GHz work)")
    group.add_argument("--onboard-only", action="store_true", help="Unbind both dongles, use only onboard Bluetooth")
    group.add_argument("--normal", action="store_true", help="Return everything to normal kernel drivers")
    group.add_argument("--install-sudoers", action="store_true", help="Install passwordless sudo rule (no more prompts)")
    group.add_argument("--remove-sudoers", action="store_true", help="Remove the passwordless sudo rule")
    group.add_argument("--install-udev", action="store_true", help="Install udev rules for permissions + auto-unbind on plug")
    group.add_argument("--remove-udev", action="store_true", help="Remove the custom udev rules")
    group.add_argument("--full-setup", action="store_true", help="Do the complete best setup (passwordless sudo + udev rules)")

    args = parser.parse_args()

    # Default to GUI if someone ran without flags but we required one above for clarity
    # Actually argparse will error; we handle default in main()

    if args.ubertooth:
        success, msg = perform_action("ubertooth", silent=True)
        print(msg)
        sys.exit(0 if success else 1)
    elif args.nrf:
        success, msg = perform_action("nrf", silent=True)
        print(msg)
        sys.exit(0 if success else 1)
    elif args.hackrf:
        success, msg = perform_action("hackrf", silent=True)
        print(msg)
        sys.exit(0 if success else 1)
    elif args.onboard_only:
        success, msg = perform_action("onboard-only", silent=True)
        print(msg)
        sys.exit(0 if success else 1)
    elif args.normal:
        success, msg = perform_action("normal", silent=True)
        print(msg)
        sys.exit(0 if success else 1)
    elif args.install_sudoers:
        print("Installing passwordless sudo rule (you may be prompted once)...")
        success, msg = run_privileged_action("install-sudoers")
        print(msg)
        sys.exit(0 if success else 1)
    elif args.remove_sudoers:
        print("Removing passwordless sudo rule...")
        success, msg = run_privileged_action("remove-sudoers")
        print(msg)
        sys.exit(0 if success else 1)
    elif args.install_udev:
        print("Installing optimized udev rules (permissions + auto-unbind)...")
        success, msg = run_privileged_action("install-udev")
        print(msg)
        sys.exit(0 if success else 1)
    elif args.remove_udev:
        print("Removing custom udev rules...")
        success, msg = run_privileged_action("remove-udev")
        print(msg)
        sys.exit(0 if success else 1)
    elif args.full_setup:
        print("=== Running FULL OPTIMIZED SETUP ===")
        print("\n[1/2] Installing passwordless sudo...")
        ok1, m1 = run_privileged_action("install-sudoers")
        print(m1)
        print("\n[2/2] Installing udev rules for permissions + auto-unbind on plug...")
        ok2, m2 = run_privileged_action("install-udev")
        print(m2)
        if ok1 and ok2:
            print("\n✅ Full setup complete! You can now use the launcher with zero prompts,")
            print("   and devices will be ready for sniffing tools the moment you plug them in.")
        sys.exit(0 if (ok1 and ok2) else 1)
    else:
        # GUI
        root = tk.Tk()
        app = SnifferUSBManagerGUI(root)
        root.mainloop()


if __name__ == "__main__":
    # If no arguments at all, default to GUI (nicer UX)
    if len(sys.argv) == 1:
        root = tk.Tk()
        app = SnifferUSBManagerGUI(root)
        root.mainloop()
    else:
        cli_main()
