# PlayStation 5 — Home Assistant Integration

A local-polling Home Assistant integration for jailbroken PS5 consoles running the VoidShell homebrew. Exposes system stats, game library, media player control, and more — all without cloud dependency.

---

## Requirements

- A jailbroken PS5 with [VoidShell](https://ko-fi.com/voidwhisper) running
- Home Assistant 2024.3.0 or later
- PS5 and HA on the same local network

---

## Installation

### Via HACS (recommended)
1. In HACS, go to **Integrations** → **Custom Repositories**
2. Add this repository URL and select **Integration**
3. Install **PlayStation 5**
4. Restart Home Assistant

### Manual
1. Copy the `custom_components/ps5` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **PlayStation 5**
3. Enter your PS5's IP address and port (default: `7007`)

> The port field is optional — only change it if you've configured VoidShell to run on a non-default port.

---

## Entities

### Media Player
| Entity | Description |
|---|---|
| PS5 | Full media player with game cover art, title, and active user. Source list lets you launch any installed game directly from HA. |

### Sensors
| Entity | Description |
|---|---|
| PS5 Total Games | Total installed game count |
| PS5 Game Count | PS5 titles installed |
| PS4 Game Count | PS4 titles installed |

### Image
| Entity | Description |
|---|---|
| PS5 Active User | Avatar of the currently logged-in user |

### Buttons
| Entity | Description |
|---|---|
| PS5 Rescan Library | Triggers a full game library rescan |
| PS5 Repair | Runs the VoidShell repair tool |
| PS5 Clear Logs | Clears VoidShell logs |

### Switch
| Entity | Description |
|---|---|
| PS5 Scanner Paused | Toggle the VoidShell background scanner on/off |

### Diagnostic Entities
These are hidden from default dashboards but visible on the device page and useful for automations:

| Entity | Type | Description |
|---|---|---|
| PS5 CPU Temperature | Sensor | CPU temp in °C |
| PS5 SoC Temperature | Sensor | SoC/APU temp in °C |
| PS5 Fan Target | Sensor | Fan target speed % |
| PS5 Uptime | Sensor | System uptime string |
| PS5 Sentinel State | Sensor | Sentinel Warden state |
| PS5 Custom Fan Active | Binary Sensor | Whether custom fan control is active |
| PS5 Kstuff Active | Binary Sensor | Whether kstuff kernel patches are loaded |

---

## Events

The integration fires a `ps5_game_changed` event on the HA event bus whenever the active game changes. You can use this to trigger automations.

**Event data:**
```yaml
event_type: ps5_game_changed
data:
  previous_game: MENU
  current_game: CUSA12345
  current_game_name: "Some Game Title"
  username: Player1
```

**Example automation — change Hue scene when a game launches:**
```yaml
automation:
  trigger:
    platform: event
    event_type: ps5_game_changed
  condition:
    condition: template
    value_template: "{{ trigger.event.data.current_game != 'MENU' }}"
  action:
    service: hue.activate_scene
    data:
      group_name: Living Room
      scene_name: Gaming
```

---

## Reconfiguring

To change the IP or port after setup:
1. Go to **Settings → Devices & Services**
2. Find the **PlayStation 5** integration card
3. Click **Configure**

---

## Notes

- The integration polls the PS5 every 10 seconds
- All entities become **unavailable** if the PS5 goes offline and recover automatically when it comes back
- The game library is only refreshed when the total game count changes, not on every poll
- This integration does **not** interact with PlayStation Network — it is entirely local
