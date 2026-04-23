# Raspberry Pi Setup

This guide gets the BVG display running on a Raspberry Pi and starting
automatically on boot.

## Prerequisites

- Raspberry Pi (any model with network access)
- Raspberry Pi OS (Bookworm or later)
- Network connection (Wi-Fi or Ethernet)

## 1. Install Python and Poetry

Raspberry Pi OS ships with Python 3.11+. Install Poetry:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add it to your PATH (add to `~/.bashrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Reload your shell, then verify:

```bash
poetry --version
```

## 2. Clone and install

```bash
cd ~
git clone https://github.com/linusseiffert/BVG-Display.git bvg-display
cd bvg-display
poetry install --without dev
```

The `--without dev` skips test/lint dependencies to save space.

## 3. Configure

```bash
cp .env.example .env
nano .env
```

Fill in at least:

```
API_BASE_URL=https://v6.bvg.transport.rest
STOP_ID=900017101
```

Set the display backend and poll interval as needed.

## 4. Test it

```bash
poetry run bvg-display
```

You should see departures in the terminal. Press `Ctrl+C` to stop.

## 5. Install the systemd service

Copy the service file and enable it:

```bash
sudo cp scripts/bvg-display.service /etc/systemd/system/
```

Edit the service file if your username is not `pi` or the repo is in a
different location:

```bash
sudo nano /etc/systemd/system/bvg-display.service
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bvg-display
sudo systemctl start bvg-display
```

## 6. Check status and logs

```bash
# Service status
sudo systemctl status bvg-display

# Live logs
journalctl -u bvg-display -f

# Logs from the last hour
journalctl -u bvg-display --since "1 hour ago"
```

## 7. Updating

```bash
cd ~/bvg-display
git pull
poetry install --without dev
sudo systemctl restart bvg-display
```

## Troubleshooting

**Service fails immediately:**
Check logs with `journalctl -u bvg-display -e`. Usually a missing
env var or wrong Python path.

**Poetry not found by systemd:**
The service file uses `/home/pi/.local/bin/poetry`. If Poetry is
installed elsewhere, update the `ExecStart` path:

```bash
which poetry   # find the actual path
sudo nano /etc/systemd/system/bvg-display.service
sudo systemctl daemon-reload
sudo systemctl restart bvg-display
```

**Display not updating:**
Check the API is reachable: `curl https://v6.bvg.transport.rest/stops/900017101/departures?results=1`

If you're behind a captive portal or the Pi has no internet, the app
will back off automatically and recover once connectivity returns.
