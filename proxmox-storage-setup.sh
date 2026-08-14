#!/bin/bash
# ==============================================================================
# Proxmox Storage Optimization Script
# ==============================================================================
# Target: MacBook Air 2018 running Proxmox
#   - Internal SSD ~120GB usable
#   - Google Drive 2TB mounted via rclone at /mnt/gdrive
#
# Strategy:
#   Frigate  (LXC 101): local SSD for last 2 days, archive to Google Drive
#   Immich   (LXC 102): Google Drive as primary library (write-once, read-occasionally)
#   HAOS     (VM  100): weekly backups to Google Drive, retain last 4
#
# Run this script as root on the Proxmox host.
# ==============================================================================

set -euo pipefail

LOG_TAG="storage-setup"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/storage-setup.log; }

# ------------------------------------------------------------------------------
# 0. PRE-FLIGHT CHECKS
# ------------------------------------------------------------------------------
log "=== Starting storage optimization setup ==="

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Run this script as root." >&2
    exit 1
fi

# Verify rclone mount is available
if ! mountpoint -q /mnt/gdrive 2>/dev/null; then
    echo "ERROR: /mnt/gdrive is not mounted. Mount Google Drive via rclone first." >&2
    echo "  Example: rclone mount gdrive: /mnt/gdrive --vfs-cache-mode full --vfs-cache-max-size 10G --daemon" >&2
    exit 1
fi

# Verify Google Drive folder structure exists
log "Ensuring Google Drive directory structure..."
mkdir -p /mnt/gdrive/HomeServer/backups
mkdir -p /mnt/gdrive/HomeServer/frigate
mkdir -p /mnt/gdrive/HomeServer/immich

# ------------------------------------------------------------------------------
# 1. CREATE HOST-SIDE DIRECTORIES FOR BIND MOUNTS
# ------------------------------------------------------------------------------
log "=== Creating host-side directories ==="

# Frigate: local SSD storage for active recordings (last 2 days)
mkdir -p /srv/frigate/storage

# Frigate: config directory (stays local for speed)
mkdir -p /srv/frigate/config

# Immich: local config and database stay on SSD (fast random I/O)
mkdir -p /srv/immich/config
mkdir -p /srv/immich/db

# Immich: library on Google Drive (write-once, read-occasionally)
# This is the actual photo/video storage -- goes straight to gdrive
mkdir -p /mnt/gdrive/HomeServer/immich/library

# Scripts and logs directory
mkdir -p /opt/homeserver/scripts
mkdir -p /var/log/homeserver

# ------------------------------------------------------------------------------
# 2. STOP CONTAINERS BEFORE MODIFYING MOUNT POINTS
# ------------------------------------------------------------------------------
log "=== Stopping containers ==="

# Stop Frigate (LXC 101)
if pct status 101 | grep -q "running"; then
    log "Stopping LXC 101 (Frigate)..."
    pct stop 101
    sleep 5
fi

# Stop Immich (LXC 102)
if pct status 102 | grep -q "running"; then
    log "Stopping LXC 102 (Immich)..."
    pct stop 102
    sleep 5
fi

log "Containers stopped."

# ------------------------------------------------------------------------------
# 3. CONFIGURE BIND MOUNTS
# ------------------------------------------------------------------------------
log "=== Configuring bind mounts ==="

# --- Frigate (LXC 101) ---
# mp0: Local SSD storage for active recordings (fast read/write)
# mp1: Google Drive archive for old recordings (read-mostly after archive)
# mp2: Config directory on local SSD
log "Setting up Frigate bind mounts..."
pct set 101 -mp0 /srv/frigate/storage,mp=/opt/frigate/storage
pct set 101 -mp1 /mnt/gdrive/HomeServer/frigate,mp=/opt/frigate/archive
pct set 101 -mp2 /srv/frigate/config,mp=/opt/frigate/config

# --- Immich (LXC 102) ---
# mp0: Google Drive library for photos (primary storage, write-once)
# mp1: Local config + database on SSD (needs fast I/O)
# mp2: Local upload cache -- photos land here first, then move to library
log "Setting up Immich bind mounts..."
mkdir -p /srv/immich/upload-cache
pct set 102 -mp0 /mnt/gdrive/HomeServer/immich/library,mp=/opt/immich/library
pct set 102 -mp1 /srv/immich/config,mp=/opt/immich/config
pct set 102 -mp2 /srv/immich/upload-cache,mp=/opt/immich/upload-cache

log "Bind mounts configured."

# ------------------------------------------------------------------------------
# 4. FRIGATE ARCHIVE SCRIPT
# ------------------------------------------------------------------------------
# Strategy:
#   - Frigate writes recordings to /opt/frigate/storage (local SSD via mp0)
#   - This script runs hourly, finds recordings older than 2 days, moves them
#     to /mnt/gdrive/HomeServer/frigate/ preserving directory structure
#   - After moving, clean up empty directories on local storage
# ------------------------------------------------------------------------------
log "=== Creating Frigate archive script ==="

cat > /opt/homeserver/scripts/frigate-archive.sh << 'SCRIPT'
#!/bin/bash
# Frigate recording archiver: local SSD -> Google Drive
# Runs on the Proxmox HOST (not inside the container)
set -euo pipefail

LOGFILE="/var/log/homeserver/frigate-archive.log"
LOCAL_STORAGE="/srv/frigate/storage"
GDRIVE_ARCHIVE="/mnt/gdrive/HomeServer/frigate"
RETENTION_DAYS=2

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] FRIGATE-ARCHIVE: $*" >> "$LOGFILE"; }

# Check Google Drive is mounted
if ! mountpoint -q /mnt/gdrive 2>/dev/null; then
    log "ERROR: /mnt/gdrive not mounted. Skipping archive."
    exit 1
fi

log "Starting archive run..."
ARCHIVED=0
ERRORS=0

# Find recording files older than RETENTION_DAYS
# Frigate stores recordings in a structure like: camera_name/YYYY-MM-DD/HH/file.mp4
while IFS= read -r -d '' file; do
    # Compute relative path from LOCAL_STORAGE
    relpath="${file#${LOCAL_STORAGE}/}"
    dest_dir="${GDRIVE_ARCHIVE}/$(dirname "$relpath")"

    mkdir -p "$dest_dir"

    # Use rsync for reliable transfer with checksum verification
    if rsync --remove-source-files --checksum "$file" "$dest_dir/" 2>> "$LOGFILE"; then
        ((ARCHIVED++))
    else
        log "ERROR: Failed to archive $relpath"
        ((ERRORS++))
    fi
done < <(find "$LOCAL_STORAGE" -type f \( -name "*.mp4" -o -name "*.jpg" -o -name "*.png" \) -mtime +${RETENTION_DAYS} -print0 2>/dev/null)

# Clean up empty directories left behind after moving files
find "$LOCAL_STORAGE" -mindepth 1 -type d -empty -delete 2>/dev/null || true

log "Archive complete. Archived: $ARCHIVED, Errors: $ERRORS"

# Report local disk usage
LOCAL_USAGE=$(du -sh "$LOCAL_STORAGE" 2>/dev/null | cut -f1)
log "Local storage usage after cleanup: $LOCAL_USAGE"
SCRIPT

chmod +x /opt/homeserver/scripts/frigate-archive.sh

# ------------------------------------------------------------------------------
# 5. FRIGATE LOCAL CLEANUP SCRIPT
# ------------------------------------------------------------------------------
# Safety net: if local SSD is getting full, aggressively remove oldest recordings
# even if they haven't been archived yet (better to lose old footage than crash)
# ------------------------------------------------------------------------------
log "=== Creating Frigate local cleanup script ==="

cat > /opt/homeserver/scripts/frigate-local-cleanup.sh << 'SCRIPT'
#!/bin/bash
# Emergency cleanup: prevent local SSD from filling up
set -euo pipefail

LOGFILE="/var/log/homeserver/frigate-cleanup.log"
LOCAL_STORAGE="/srv/frigate/storage"
# Trigger cleanup when the filesystem is more than 85% full
THRESHOLD_PERCENT=85

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] FRIGATE-CLEANUP: $*" >> "$LOGFILE"; }

# Get usage percentage of the filesystem containing LOCAL_STORAGE
USAGE=$(df --output=pcent "$LOCAL_STORAGE" | tail -1 | tr -dc '0-9')

if [[ "$USAGE" -lt "$THRESHOLD_PERCENT" ]]; then
    exit 0
fi

log "WARNING: Disk at ${USAGE}% (threshold: ${THRESHOLD_PERCENT}%). Starting emergency cleanup."

# Delete oldest files first until we are below 75%
TARGET_PERCENT=75
while [[ "$USAGE" -gt "$TARGET_PERCENT" ]]; do
    # Find the single oldest file and remove it
    OLDEST=$(find "$LOCAL_STORAGE" -type f \( -name "*.mp4" -o -name "*.jpg" \) -printf '%T+ %p\n' 2>/dev/null | sort | head -1 | cut -d' ' -f2-)
    if [[ -z "$OLDEST" ]]; then
        log "No more files to delete but still at ${USAGE}%."
        break
    fi
    log "Deleting: $OLDEST"
    rm -f "$OLDEST"
    USAGE=$(df --output=pcent "$LOCAL_STORAGE" | tail -1 | tr -dc '0-9')
done

# Clean up empty directories
find "$LOCAL_STORAGE" -mindepth 1 -type d -empty -delete 2>/dev/null || true

log "Cleanup complete. Disk now at ${USAGE}%."
SCRIPT

chmod +x /opt/homeserver/scripts/frigate-local-cleanup.sh

# ------------------------------------------------------------------------------
# 6. HAOS BACKUP SCRIPT
# ------------------------------------------------------------------------------
# Strategy:
#   - Trigger a full HAOS backup via the HA CLI (through SSH to the VM)
#   - Copy the resulting .tar to Google Drive
#   - Keep only the last 4 backups on Google Drive
#
# Prerequisites:
#   - SSH key from Proxmox host authorized in HAOS
#   - HA CLI available inside the HAOS VM
#   - HAOS VM IP is set below (adjust as needed)
# ------------------------------------------------------------------------------
log "=== Creating HAOS backup script ==="

cat > /opt/homeserver/scripts/haos-backup.sh << 'SCRIPT'
#!/bin/bash
# Home Assistant OS weekly backup to Google Drive
set -euo pipefail

LOGFILE="/var/log/homeserver/haos-backup.log"
GDRIVE_BACKUPS="/mnt/gdrive/HomeServer/backups"
HAOS_IP="192.168.50.203"
HAOS_SSH_PORT=22
HAOS_SSH_USER="root"
KEEP_BACKUPS=4

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] HAOS-BACKUP: $*" >> "$LOGFILE"; }

# Check Google Drive is mounted
if ! mountpoint -q /mnt/gdrive 2>/dev/null; then
    log "ERROR: /mnt/gdrive not mounted. Skipping backup."
    exit 1
fi

# Check HAOS is reachable
if ! ssh -o ConnectTimeout=10 -p "$HAOS_SSH_PORT" "${HAOS_SSH_USER}@${HAOS_IP}" "echo ok" &>/dev/null; then
    log "ERROR: Cannot reach HAOS at ${HAOS_IP}:${HAOS_SSH_PORT}. Skipping backup."
    exit 1
fi

log "Starting HAOS backup..."

# Trigger backup creation via HA CLI
BACKUP_SLUG=$(ssh -p "$HAOS_SSH_PORT" "${HAOS_SSH_USER}@${HAOS_IP}" \
    "ha backups new --name homeserver-$(date +%Y%m%d) 2>/dev/null | grep slug | awk '{print \$2}'"
)

if [[ -z "$BACKUP_SLUG" ]]; then
    log "ERROR: Failed to create backup. No slug returned."
    exit 1
fi

log "Backup created with slug: $BACKUP_SLUG"

# Wait for the backup file to be ready (HAOS writes to /backup/)
sleep 30

# Copy backup from HAOS to Google Drive
BACKUP_FILE="${BACKUP_SLUG}.tar"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DEST_NAME="haos-backup-${TIMESTAMP}.tar"

scp -P "$HAOS_SSH_PORT" "${HAOS_SSH_USER}@${HAOS_IP}:/backup/${BACKUP_FILE}" \
    "${GDRIVE_BACKUPS}/${DEST_NAME}"

if [[ $? -eq 0 ]]; then
    log "Backup copied to Google Drive: ${DEST_NAME}"
else
    log "ERROR: Failed to copy backup to Google Drive."
    exit 1
fi

# Clean up old backups on Google Drive -- keep only the newest KEEP_BACKUPS
BACKUP_COUNT=$(find "$GDRIVE_BACKUPS" -maxdepth 1 -name "haos-backup-*.tar" -type f | wc -l)
if [[ "$BACKUP_COUNT" -gt "$KEEP_BACKUPS" ]]; then
    DELETE_COUNT=$((BACKUP_COUNT - KEEP_BACKUPS))
    log "Pruning ${DELETE_COUNT} old backup(s) from Google Drive..."
    find "$GDRIVE_BACKUPS" -maxdepth 1 -name "haos-backup-*.tar" -type f -printf '%T+ %p\n' \
        | sort \
        | head -n "$DELETE_COUNT" \
        | cut -d' ' -f2- \
        | while read -r old; do
            log "Deleting old backup: $(basename "$old")"
            rm -f "$old"
        done
fi

# Also clean up the backup inside HAOS to save VM disk space
ssh -p "$HAOS_SSH_PORT" "${HAOS_SSH_USER}@${HAOS_IP}" \
    "ha backups remove ${BACKUP_SLUG}" 2>/dev/null || true

log "HAOS backup complete."
SCRIPT

chmod +x /opt/homeserver/scripts/haos-backup.sh

# ------------------------------------------------------------------------------
# 7. GOOGLE DRIVE ARCHIVE CLEANUP SCRIPT
# ------------------------------------------------------------------------------
# Frigate archives can grow unbounded on Google Drive.
# This script prunes Frigate recordings older than 30 days from the archive.
# Adjust ARCHIVE_RETENTION_DAYS as needed.
# ------------------------------------------------------------------------------
log "=== Creating Google Drive archive cleanup script ==="

cat > /opt/homeserver/scripts/gdrive-cleanup.sh << 'SCRIPT'
#!/bin/bash
# Prune old Frigate recordings from Google Drive archive
set -euo pipefail

LOGFILE="/var/log/homeserver/gdrive-cleanup.log"
GDRIVE_FRIGATE="/mnt/gdrive/HomeServer/frigate"
ARCHIVE_RETENTION_DAYS=30

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] GDRIVE-CLEANUP: $*" >> "$LOGFILE"; }

if ! mountpoint -q /mnt/gdrive 2>/dev/null; then
    log "ERROR: /mnt/gdrive not mounted. Skipping cleanup."
    exit 1
fi

log "Cleaning Frigate archives older than ${ARCHIVE_RETENTION_DAYS} days..."

DELETED=0
while IFS= read -r -d '' file; do
    rm -f "$file"
    ((DELETED++))
done < <(find "$GDRIVE_FRIGATE" -type f -mtime +${ARCHIVE_RETENTION_DAYS} -print0 2>/dev/null)

# Clean empty directories
find "$GDRIVE_FRIGATE" -mindepth 1 -type d -empty -delete 2>/dev/null || true

log "Deleted $DELETED file(s) from Frigate archive."

# Report Google Drive usage for HomeServer
GDRIVE_USAGE=$(du -sh /mnt/gdrive/HomeServer 2>/dev/null | cut -f1)
log "Total Google Drive HomeServer usage: $GDRIVE_USAGE"
SCRIPT

chmod +x /opt/homeserver/scripts/gdrive-cleanup.sh

# ------------------------------------------------------------------------------
# 8. LOG ROTATION
# ------------------------------------------------------------------------------
log "=== Setting up log rotation ==="

cat > /etc/logrotate.d/homeserver << 'LOGROTATE'
/var/log/homeserver/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    create 0640 root root
}
LOGROTATE

# ------------------------------------------------------------------------------
# 9. RCLONE MOUNT SYSTEMD SERVICE
# ------------------------------------------------------------------------------
# Ensure Google Drive is mounted automatically on boot.
# Adjust the rclone remote name ("gdrive:") to match your rclone config.
# ------------------------------------------------------------------------------
log "=== Creating rclone mount systemd service ==="

cat > /etc/systemd/system/rclone-gdrive.service << 'SYSTEMD'
[Unit]
Description=Mount Google Drive via rclone
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStartPre=/bin/mkdir -p /mnt/gdrive
ExecStart=/usr/bin/rclone mount gdrive: /mnt/gdrive \
    --vfs-cache-mode full \
    --vfs-cache-max-size 10G \
    --vfs-cache-max-age 72h \
    --vfs-read-chunk-size 64M \
    --vfs-read-chunk-size-limit 1G \
    --buffer-size 64M \
    --dir-cache-time 72h \
    --poll-interval 15s \
    --log-file /var/log/homeserver/rclone.log \
    --log-level INFO \
    --allow-other
ExecStop=/bin/fusermount -uz /mnt/gdrive
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable rclone-gdrive.service
log "rclone mount service installed and enabled."

# ------------------------------------------------------------------------------
# 10. CRON JOBS
# ------------------------------------------------------------------------------
log "=== Installing cron jobs ==="

CRON_FILE="/etc/cron.d/homeserver-storage"

cat > "$CRON_FILE" << 'CRON'
# Homeserver storage management cron jobs
# All scripts log to /var/log/homeserver/
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Frigate: archive recordings older than 2 days to Google Drive (every hour)
15 * * * * root /opt/homeserver/scripts/frigate-archive.sh

# Frigate: emergency local SSD cleanup if disk gets too full (every 15 min)
*/15 * * * * root /opt/homeserver/scripts/frigate-local-cleanup.sh

# HAOS: weekly backup to Google Drive (Sunday at 03:00)
0 3 * * 0 root /opt/homeserver/scripts/haos-backup.sh

# Google Drive: prune old Frigate archives beyond 30 days (daily at 04:00)
0 4 * * * root /opt/homeserver/scripts/gdrive-cleanup.sh
CRON

chmod 644 "$CRON_FILE"
log "Cron jobs installed at $CRON_FILE"

# ------------------------------------------------------------------------------
# 11. FRIGATE CONFIGURATION NOTES
# ------------------------------------------------------------------------------
# Frigate itself needs to be configured to write recordings to /opt/frigate/storage
# (which is now bind-mounted from the local SSD). The archive path at
# /opt/frigate/archive is read-only from Frigate's perspective -- the host-side
# script handles the archiving.
#
# In your Frigate config.yml (inside the container at /opt/frigate/config/config.yml),
# ensure the recording path points to the local mount:
# ------------------------------------------------------------------------------
log "=== Generating Frigate config snippet ==="

cat > /srv/frigate/config/storage-note.yml << 'FRIGATE_CONFIG'
# =============================================================================
# FRIGATE STORAGE CONFIGURATION SNIPPET
# Merge these settings into your main config.yml
# =============================================================================
# The recording directory MUST point to /opt/frigate/storage (local SSD via
# bind mount). The archival to Google Drive is handled by the host-side cron
# job, NOT by Frigate itself.
#
# record:
#   enabled: True
#   retain:
#     days: 3       # Frigate's internal retention (host script handles 2-day
#                   # archive window, set this slightly higher as safety margin)
#     mode: motion  # Or "all" if you want continuous recording
#   events:
#     retain:
#       default: 14 # Keep event clips longer (they're small)
#       mode: motion
#
# snapshots:
#   enabled: True
#   retain:
#     default: 7
#
# # Ensure Frigate stores everything under /opt/frigate/storage:
# # (This is the default, but be explicit)
# # Frigate 0.13+ uses the environment variable FRIGATE_MEDIA_DIR
# # or defaults to /media/frigate. Override in docker-compose:
# #   environment:
# #     - FRIGATE_MEDIA_DIR=/opt/frigate/storage
# # Or in older versions, the "directory" key under record.
# =============================================================================
FRIGATE_CONFIG

# ------------------------------------------------------------------------------
# 12. IMMICH CONFIGURATION NOTES
# ------------------------------------------------------------------------------
# Immich stores its photo library at /opt/immich/library which is now bind-
# mounted to Google Drive. The upload-cache at /opt/immich/upload-cache is on
# the local SSD so uploads are fast; Immich moves completed uploads into the
# library directory.
#
# In Immich's docker-compose.yml or .env, set:
#   UPLOAD_LOCATION=/opt/immich/upload-cache
#   IMMICH_MEDIA_LOCATION=/opt/immich/library   (or map via Docker volumes)
# ------------------------------------------------------------------------------
log "=== Generating Immich config snippet ==="

cat > /srv/immich/config/storage-note.env << 'IMMICH_CONFIG'
# =============================================================================
# IMMICH STORAGE CONFIGURATION
# Add these to your Immich .env file or docker-compose.yml
# =============================================================================
# Upload cache on local SSD (fast writes during upload):
UPLOAD_LOCATION=/opt/immich/upload-cache

# Photo library on Google Drive (write-once, read-occasionally):
IMMICH_MEDIA_LOCATION=/opt/immich/library

# Database stays on local SSD for fast queries (configured via db volume
# in docker-compose.yml, should map to /opt/immich/config or similar).
#
# In docker-compose.yml, the immich-server volumes should look like:
#   volumes:
#     - /opt/immich/upload-cache:/usr/src/app/upload
#     - /opt/immich/library:/usr/src/app/upload/library
#
# IMPORTANT: Because Google Drive is slow (~10MB/s), large batch imports
# will be slower than local storage. For initial migration of an existing
# library, consider rclone copy from a local source directly to
# /mnt/gdrive/HomeServer/immich/library on the host.
# =============================================================================
IMMICH_CONFIG

# ------------------------------------------------------------------------------
# 13. START CONTAINERS
# ------------------------------------------------------------------------------
log "=== Starting containers ==="

log "Starting LXC 101 (Frigate)..."
pct start 101
sleep 5

log "Starting LXC 102 (Immich)..."
pct start 102
sleep 5

log "Verifying containers..."
pct status 101
pct status 102

# ------------------------------------------------------------------------------
# 14. VERIFICATION
# ------------------------------------------------------------------------------
log "=== Running verification checks ==="

echo ""
echo "============================== VERIFICATION =============================="
echo ""

echo "--- Bind mounts for LXC 101 (Frigate) ---"
pct config 101 | grep "^mp"
echo ""

echo "--- Bind mounts for LXC 102 (Immich) ---"
pct config 102 | grep "^mp"
echo ""

echo "--- Google Drive directories ---"
ls -la /mnt/gdrive/HomeServer/
echo ""

echo "--- Host-side storage directories ---"
echo "Frigate local storage: $(du -sh /srv/frigate/storage 2>/dev/null || echo 'empty')"
echo "Immich upload cache:   $(du -sh /srv/immich/upload-cache 2>/dev/null || echo 'empty')"
echo "Immich library (gdrive): $(du -sh /mnt/gdrive/HomeServer/immich/library 2>/dev/null || echo 'empty')"
echo ""

echo "--- Installed cron jobs ---"
cat /etc/cron.d/homeserver-storage
echo ""

echo "--- Installed scripts ---"
ls -la /opt/homeserver/scripts/
echo ""

echo "=========================================================================="
echo ""
echo "SETUP COMPLETE. Next steps:"
echo ""
echo "  1. ADJUST HAOS VM IP in /opt/homeserver/scripts/haos-backup.sh"
echo "     Current value: HAOS_IP=192.168.1.100, HAOS_SSH_PORT=22222"
echo "     Set these to match your HAOS VM network config."
echo ""
echo "  2. SET UP SSH KEY for HAOS backups:"
echo "     ssh-keygen -t ed25519 -f /root/.ssh/haos_key -N ''"
echo "     ssh-copy-id -p 22222 -i /root/.ssh/haos_key root@<HAOS_IP>"
echo "     Then add '-i /root/.ssh/haos_key' to the ssh/scp commands in haos-backup.sh"
echo ""
echo "  3. UPDATE FRIGATE CONFIG inside LXC 101:"
echo "     Review /opt/frigate/config/storage-note.yml and merge into your config.yml"
echo "     Ensure FRIGATE_MEDIA_DIR=/opt/frigate/storage in your docker-compose"
echo ""
echo "  4. UPDATE IMMICH CONFIG inside LXC 102:"
echo "     Review /opt/immich/config/storage-note.env and merge into your .env"
echo "     Update docker-compose.yml volumes as described"
echo ""
echo "  5. TEST SCRIPTS MANUALLY:"
echo "     /opt/homeserver/scripts/frigate-archive.sh"
echo "     /opt/homeserver/scripts/frigate-local-cleanup.sh"
echo "     /opt/homeserver/scripts/haos-backup.sh"
echo "     /opt/homeserver/scripts/gdrive-cleanup.sh"
echo ""
echo "  6. MONITOR LOGS:"
echo "     tail -f /var/log/homeserver/frigate-archive.log"
echo "     tail -f /var/log/homeserver/haos-backup.log"
echo "     tail -f /var/log/homeserver/rclone.log"
echo ""
echo "=========================================================================="

log "=== Setup complete ==="
