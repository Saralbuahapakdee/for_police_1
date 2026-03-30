<template>
  <div class="multicam-tab">

    <!-- ── Header bar ── -->
    <div class="mc-header">
      <div class="mc-header-left">
        <div class="mc-title-block">
          <span class="mc-eye-icon">👁</span>
          <div>
            <h2 class="mc-title">Multi-Camera Monitor</h2>
            <p class="mc-subtitle">Live surveillance grid — all feeds at a glance</p>
          </div>
        </div>
      </div>

      <div class="mc-header-right">
        <!-- Layout picker -->
        <div class="layout-picker">
          <button v-for="opt in layoutOptions" :key="opt.value"
                  @click="layout = opt.value"
                  :class="['layout-btn', { active: layout === opt.value }]"
                  :title="opt.label">
            <span class="layout-icon">{{ opt.icon }}</span>
          </button>
        </div>

        <!-- Alert sound toggle -->
        <button @click="soundEnabled = !soundEnabled"
                :class="['sound-btn', { muted: !soundEnabled }]"
                title="Toggle alert sound">
          {{ soundEnabled ? '🔔' : '🔕' }}
        </button>

        <!-- Fullscreen -->
        <button @click="toggleFullscreen" class="fullscreen-btn" title="Toggle fullscreen">
          {{ isFullscreen ? '⊡' : '⊞' }}
        </button>
      </div>
    </div>

    <!-- ── Global alert strip ── -->
    <transition name="alert-slide">
      <div v-if="globalAlert" class="global-alert-strip">
        <span class="alert-pulse"></span>
        <strong>🚨 WEAPON DETECTED</strong>
        <span class="alert-sep">|</span>
        <span>{{ formatWeapon(globalAlert.weapon_type) }}</span>
        <span class="alert-sep">·</span>
        <span>{{ globalAlert.camera_name }}</span>
        <span class="alert-sep">·</span>
        <span>{{ globalAlert.location }}</span>
        <span class="alert-sep">·</span>
        <span>{{ formatShortTime(globalAlert.timestamp) }}</span>
        <button @click="globalAlert = null" class="alert-dismiss">✕</button>
      </div>
    </transition>

    <!-- ── Stats row ── -->
    <div class="mc-stats">
      <div class="mc-stat">
        <div class="mc-stat-val">{{ activeCameras.length }}</div>
        <div class="mc-stat-label">Active Feeds</div>
      </div>
      <div class="mc-stat" :class="{ 'mc-stat-alert': anyDetection }">
        <div class="mc-stat-val">{{ detectionCount }}</div>
        <div class="mc-stat-label">Active Alerts</div>
      </div>
      <div class="mc-stat">
        <div class="mc-stat-val">{{ todayIncidents }}</div>
        <div class="mc-stat-label">Today's Incidents</div>
      </div>
      <div class="mc-stat">
        <div class="mc-stat-val">
          <span :class="['conn-dot', isConnected ? 'online' : 'offline']"></span>
          {{ isConnected ? 'Live' : 'Off' }}
        </div>
        <div class="mc-stat-label">Detection Status</div>
      </div>
    </div>

    <!-- ── Camera grid ── -->
    <div :class="['camera-grid', `grid-${layout}`]" ref="gridRef">
      <div v-for="camera in activeCameras" :key="camera.id"
           :class="['camera-cell', {
             'cell-alert': cameraHasAlert(camera.id),
             'cell-expanded': expandedCamera === camera.id
           }]"
           @dblclick="toggleExpand(camera.id)">

        <!-- Video feed -->
        <div class="feed-wrapper">
          <img
            :src="`/api/video?token=${token}&camera_id=${camera.id}`"
            class="feed-img"
            :alt="camera.camera_name"
            @error="onFeedError(camera.id)"
          />

          <!-- Alert overlay flash -->
          <transition name="alert-flash">
            <div v-if="cameraHasAlert(camera.id)" class="alert-overlay">
              <div class="alert-overlay-icon">⚠</div>
              <div class="alert-overlay-text">
                {{ getAlertWeapons(camera.id) }}
              </div>
            </div>
          </transition>

          <!-- Offline overlay -->
          <div v-if="feedErrors.has(camera.id)" class="offline-overlay">
            <span class="offline-icon">📷</span>
            <span class="offline-text">No Signal</span>
          </div>
        </div>

        <!-- Camera label bar -->
        <div class="cell-label">
          <div class="cell-label-left">
            <span :class="['cell-status-dot', feedErrors.has(camera.id) ? 'offline' : 'online']"></span>
            <span class="cell-name">{{ camera.camera_name }}</span>
          </div>
          <div class="cell-label-right">
            <span v-if="cameraHasAlert(camera.id)" class="cell-alert-badge">
              🚨 {{ getAlertWeapons(camera.id) }}
            </span>
            <span class="cell-loc">{{ camera.location }}</span>
            <button @click.stop="openSingle(camera)" class="cell-expand-btn" title="Open single view">⤢</button>
          </div>
        </div>

        <!-- Expand hint -->
        <div class="expand-hint">Double-click to expand</div>
      </div>

      <!-- Empty state -->
      <div v-if="activeCameras.length === 0" class="no-cameras-state">
        <div class="no-cam-icon">📷</div>
        <p>No active cameras found.</p>
        <p class="no-cam-sub">Activate cameras in the Camera Management tab.</p>
      </div>
    </div>

    <!-- ── Single camera lightbox ── -->
    <transition name="lightbox-fade">
      <div v-if="lightboxCamera" class="lightbox-overlay" @click.self="lightboxCamera = null">
        <div class="lightbox-box">
          <div class="lightbox-header">
            <div class="lightbox-title-row">
              <span :class="['cell-status-dot', 'online']"></span>
              <strong>{{ lightboxCamera.camera_name }}</strong>
              <span class="lightbox-loc">📍 {{ lightboxCamera.location }}</span>
            </div>
            <button @click="lightboxCamera = null" class="lightbox-close">✕</button>
          </div>

          <div class="lightbox-feed-wrap">
            <img
              :src="`/api/video?token=${token}&camera_id=${lightboxCamera.id}`"
              class="lightbox-feed"
              :alt="lightboxCamera.camera_name"
            />
            <div v-if="cameraHasAlert(lightboxCamera.id)" class="lightbox-alert-strip">
              🚨 WEAPON DETECTED — {{ getAlertWeapons(lightboxCamera.id) }}
            </div>
          </div>

          <!-- Recent detections for this camera -->
          <div class="lightbox-detections">
            <h4>Recent Detections</h4>
            <div v-if="detectionsForCamera(lightboxCamera.id).length === 0" class="lb-no-det">
              No recent detections
            </div>
            <div v-else class="lb-det-list">
              <div v-for="d in detectionsForCamera(lightboxCamera.id).slice(0, 6)"
                   :key="d.id" class="lb-det-item">
                <span :class="['lb-weapon', d.weapon_type]">{{ formatWeapon(d.weapon_type) }}</span>
                <span class="lb-conf">{{ Math.round(d.confidence_score * 100) }}%</span>
                <span class="lb-time">{{ formatShortTime(d.detection_time) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import detectionService from '../services/detectionService.js'
import { parseUTC } from '../services/dateUtils.js'

const props = defineProps({ token: String })

// ── State ─────────────────────────────────────────────────────────────────
const cameras         = ref([])
const recentDetections = ref([])
const layout          = ref('2x2')
const expandedCamera  = ref(null)
const lightboxCamera  = ref(null)
const isFullscreen    = ref(false)
const soundEnabled    = ref(true)
const feedErrors      = ref(new Set())
const globalAlert     = ref(null)
const isConnected     = ref(false)
const todayIncidents  = ref(0)

// Detection state per camera: camera_id → { detected, objects, timestamp }
const cameraDetections = ref({})

let unsubscribe     = null
let detectionTimer  = null
let refreshTimer    = null

// ── Layout options ─────────────────────────────────────────────────────────
const layoutOptions = [
  { value: '1x1', icon: '▣',  label: 'Single' },
  { value: '1x2', icon: '⊟',  label: '1 × 2' },
  { value: '2x2', icon: '⊞',  label: '2 × 2' },
  { value: '2x3', icon: '⊟⊟', label: '2 × 3' },
  { value: '3x3', icon: '⊞⊞', label: '3 × 3' },
]

// ── Computed ───────────────────────────────────────────────────────────────
const activeCameras = computed(() =>
  cameras.value.filter(c => c.is_active)
)

const anyDetection = computed(() =>
  Object.values(cameraDetections.value).some(d => d?.detected)
)

const detectionCount = computed(() =>
  Object.values(cameraDetections.value).filter(d => d?.detected).length
)

// ── Helpers ────────────────────────────────────────────────────────────────
function cameraHasAlert(cameraId) {
  return !!cameraDetections.value[cameraId]?.detected
}

function getAlertWeapons(cameraId) {
  const det = cameraDetections.value[cameraId]
  if (!det?.objects) return ''
  return Object.keys(det.objects).map(formatWeapon).join(', ')
}

function detectionsForCamera(cameraId) {
  return recentDetections.value.filter(d => d.camera_id === cameraId)
}

function formatWeapon(w) {
  const map = { knife: 'Knife', pistol: 'Pistol', gun: 'Pistol', heavy_weapon: 'Heavy Weapon', 'heavy-weapon': 'Heavy Weapon' }
  return map[w] || w
}

function formatShortTime(ts) {
  if (!ts) return ''
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function onFeedError(cameraId) {
  feedErrors.value = new Set([...feedErrors.value, cameraId])
}

function toggleExpand(cameraId) {
  expandedCamera.value = expandedCamera.value === cameraId ? null : cameraId
}

function openSingle(camera) {
  lightboxCamera.value = camera
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {})
    isFullscreen.value = true
  } else {
    document.exitFullscreen().catch(() => {})
    isFullscreen.value = false
  }
}

// ── Data loading ───────────────────────────────────────────────────────────
async function loadCameras() {
  try {
    const res = await fetch('/api/cameras')
    if (res.ok) cameras.value = (await res.json()).cameras
  } catch (e) { console.error(e) }
}

async function loadRecentDetections() {
  try {
    const res = await fetch('/api/detection-logs?limit=200&days=1', {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    if (res.ok) recentDetections.value = (await res.json()).logs
  } catch (e) { console.error(e) }
}

async function loadTodayIncidents() {
  try {
    const res = await fetch('/api/incidents?limit=500', {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      const today = new Date().toDateString()
      todayIncidents.value = data.incidents.filter(i => {
        const d = parseUTC(i.detected_at)
        return d && d.toDateString() === today
      }).length
    }
  } catch (e) { console.error(e) }
}

// Poll /detection-status for each camera individually
async function pollDetectionStatus() {
  try {
    const res = await fetch('/api/detection-status')
    if (!res.ok) { isConnected.value = false; return }
    isConnected.value = true
    const data = await res.json()

    if (data.detected && data.objects && Object.keys(data.objects).length > 0) {
      // We don't know which camera from the global endpoint — use latest_incident_id
      // to figure out the camera, or just show the alert globally
      if (data.timestamp) {
        // Update per-camera detection state from the service's internal map
        // The detectionService already has camera-aware data via MQTT
      }
    }
  } catch (e) { isConnected.value = false }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadCameras()
  await loadRecentDetections()
  await loadTodayIncidents()

  // Subscribe to the global detection service
  unsubscribe = detectionService.subscribe((state) => {
    isConnected.value = state.isConnected

    // If a new alert incident arrives, show the global strip
    if (state.currentAlert && state.currentAlert.incident) {
      const inc = state.currentAlert.incident
      if (!globalAlert.value || globalAlert.value.id !== state.currentAlert.id) {
        globalAlert.value = {
          id:          state.currentAlert.id,
          weapon_type: inc.weapon_type,
          camera_name: inc.camera_name,
          location:    inc.camera_location || inc.location,
          timestamp:   inc.detected_at
        }
        if (soundEnabled.value) playAlertSound()
      }
    }

    // Update per-camera detection map from current detection
    const det = state.currentDetection
    if (det?.detected && det.objects && Object.keys(det.objects).length > 0) {
      // Try to find which camera this is for via the latest incident
      if (state.currentAlert?.incident?.camera_id) {
        const camId = state.currentAlert.incident.camera_id
        cameraDetections.value = {
          ...cameraDetections.value,
          [camId]: { detected: true, objects: det.objects, timestamp: det.timestamp }
        }
        // Auto-clear after 30s
        setTimeout(() => {
          const current = cameraDetections.value[camId]
          if (current?.timestamp === det.timestamp) {
            const updated = { ...cameraDetections.value }
            delete updated[camId]
            cameraDetections.value = updated
          }
        }, 30000)
      }
    }
  })

  detectionService.startPolling(props.token)

  // Refresh detections every 15s
  refreshTimer = setInterval(async () => {
    await loadRecentDetections()
    await loadTodayIncidents()
  }, 15000)
})

onBeforeUnmount(() => {
  if (unsubscribe) unsubscribe()
  if (detectionTimer) clearInterval(detectionTimer)
  if (refreshTimer) clearInterval(refreshTimer)
})

// ── Alert sound ────────────────────────────────────────────────────────────
function playAlertSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    ;[0, 0.18, 0.36].forEach(delay => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain); gain.connect(ctx.destination)
      osc.frequency.value = 880
      osc.type = 'square'
      gain.gain.setValueAtTime(0.15, ctx.currentTime + delay)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + 0.15)
      osc.start(ctx.currentTime + delay)
      osc.stop(ctx.currentTime + delay + 0.15)
    })
  } catch (e) {}
}
</script>

<style scoped>
/* ── Design tokens ──────────────────────────────────────────────────────── */
.multicam-tab {
  --bg:        #0a0e17;
  --surface:   #111827;
  --surface2:  #1a2235;
  --border:    #1e2d45;
  --accent:    #00d4ff;
  --danger:    #ff3b3b;
  --warn:      #ffb020;
  --success:   #00e676;
  --text:      #e2e8f0;
  --text-dim:  #64748b;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;

  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--bg);
  min-height: 100%;
  padding: 4px;
  font-family: var(--font-mono);
  color: var(--text);
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.mc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.mc-header-left { display: flex; align-items: center; }

.mc-title-block {
  display: flex;
  align-items: center;
  gap: 14px;
}

.mc-eye-icon {
  font-size: 1.8rem;
  filter: drop-shadow(0 0 8px var(--accent));
  animation: blink 3s ease-in-out infinite;
}

@keyframes blink {
  0%, 90%, 100% { opacity: 1; }
  95%            { opacity: 0.2; }
}

.mc-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
  text-shadow: 0 0 12px rgba(0,212,255,.4);
}

.mc-subtitle {
  margin: 2px 0 0;
  font-size: 0.72rem;
  color: var(--text-dim);
  letter-spacing: 0.06em;
}

.mc-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Layout picker */
.layout-picker {
  display: flex;
  gap: 4px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 3px;
}

.layout-btn {
  width: 34px;
  height: 34px;
  background: transparent;
  border: none;
  border-radius: 5px;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.layout-btn:hover { background: var(--border); color: var(--text); }
.layout-btn.active { background: var(--accent); color: #000; }

.sound-btn, .fullscreen-btn {
  width: 38px;
  height: 38px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 7px;
  color: var(--text);
  cursor: pointer;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.sound-btn:hover, .fullscreen-btn:hover { border-color: var(--accent); color: var(--accent); }
.sound-btn.muted { opacity: 0.5; }

/* ── Global alert strip ─────────────────────────────────────────────────── */
.global-alert-strip {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(90deg, rgba(255,59,59,.15), rgba(255,59,59,.05));
  border: 1px solid var(--danger);
  border-radius: 8px;
  padding: 10px 40px 10px 16px;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  animation: stripPulse 2s ease-in-out infinite;
}

@keyframes stripPulse {
  0%, 100% { border-color: var(--danger); box-shadow: 0 0 0 rgba(255,59,59,0); }
  50%       { border-color: #ff7070;      box-shadow: 0 0 16px rgba(255,59,59,.35); }
}

.alert-pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--danger);
  flex-shrink: 0;
  animation: dotPulse 1s ease-in-out infinite;
}

@keyframes dotPulse {
  0%, 100% { transform: scale(1);   opacity: 1; }
  50%       { transform: scale(1.5); opacity: .7; }
}

.alert-sep { color: var(--text-dim); margin: 0 2px; }

.alert-dismiss {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 1rem;
  padding: 2px 6px;
  transition: color 0.2s;
}
.alert-dismiss:hover { color: var(--danger); }

/* Transition */
.alert-slide-enter-active, .alert-slide-leave-active { transition: all 0.3s ease; }
.alert-slide-enter-from, .alert-slide-leave-to { opacity: 0; transform: translateY(-10px); }

/* ── Stats row ──────────────────────────────────────────────────────────── */
.mc-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.mc-stat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
  transition: border-color 0.3s;
}

.mc-stat-alert {
  border-color: var(--danger);
  background: rgba(255,59,59,.07);
}

.mc-stat-val {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.mc-stat-label {
  font-size: 0.7rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 4px;
}

.conn-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.conn-dot.online  { background: var(--success); box-shadow: 0 0 6px var(--success); }
.conn-dot.offline { background: var(--text-dim); }

/* ── Camera grid ────────────────────────────────────────────────────────── */
.camera-grid {
  display: grid;
  gap: 10px;
  flex: 1;
}

.grid-1x1 { grid-template-columns: 1fr; }
.grid-1x2 { grid-template-columns: 1fr 1fr; }
.grid-2x2 { grid-template-columns: 1fr 1fr; }
.grid-2x3 { grid-template-columns: 1fr 1fr 1fr; }
.grid-3x3 { grid-template-columns: 1fr 1fr 1fr; }

/* Camera cell */
.camera-cell {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: border-color 0.3s, box-shadow 0.3s;
  min-height: 220px;
}

.camera-cell:hover {
  border-color: #2a3f60;
  box-shadow: 0 4px 20px rgba(0,0,0,.4);
}

.camera-cell.cell-alert {
  border-color: var(--danger);
  box-shadow: 0 0 20px rgba(255,59,59,.25);
  animation: cellPulse 2s ease-in-out infinite;
}

@keyframes cellPulse {
  0%, 100% { box-shadow: 0 0 12px rgba(255,59,59,.2); }
  50%       { box-shadow: 0 0 28px rgba(255,59,59,.45); }
}

.camera-cell.cell-expanded {
  grid-column: span 2;
  grid-row: span 2;
}

/* Feed */
.feed-wrapper {
  position: relative;
  flex: 1;
  background: #000;
  overflow: hidden;
  min-height: 160px;
}

.feed-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* Alert overlay */
.alert-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255,59,59,.18);
  border: 2px solid var(--danger);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  backdrop-filter: blur(1px);
  animation: overlayFlash 1s ease-in-out infinite;
}

@keyframes overlayFlash {
  0%, 100% { background: rgba(255,59,59,.12); }
  50%       { background: rgba(255,59,59,.28); }
}

.alert-overlay-icon {
  font-size: 2.2rem;
  animation: iconShake 0.4s ease-in-out infinite;
}

@keyframes iconShake {
  0%, 100% { transform: rotate(0deg); }
  25%       { transform: rotate(-8deg); }
  75%       { transform: rotate(8deg); }
}

.alert-overlay-text {
  background: var(--danger);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 3px 10px;
  border-radius: 4px;
}

/* Alert flash transition */
.alert-flash-enter-active, .alert-flash-leave-active { transition: opacity 0.3s; }
.alert-flash-enter-from, .alert-flash-leave-to { opacity: 0; }

/* Offline overlay */
.offline-overlay {
  position: absolute;
  inset: 0;
  background: rgba(10,14,23,.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.offline-icon { font-size: 2rem; opacity: 0.4; }
.offline-text { font-size: 0.75rem; color: var(--text-dim); letter-spacing: 0.1em; text-transform: uppercase; }

/* Label bar */
.cell-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--surface2);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  gap: 8px;
  flex-wrap: wrap;
}

.cell-label-left {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.cell-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.cell-status-dot.online  { background: var(--success); box-shadow: 0 0 5px var(--success); }
.cell-status-dot.offline { background: var(--text-dim); }

.cell-name {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-label-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.cell-alert-badge {
  font-size: 0.68rem;
  font-weight: 700;
  background: var(--danger);
  color: #fff;
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.05em;
  animation: badgePulse 1.5s ease-in-out infinite;
}

@keyframes badgePulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.6; }
}

.cell-loc {
  font-size: 0.7rem;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.cell-expand-btn {
  background: var(--border);
  border: none;
  color: var(--text-dim);
  border-radius: 4px;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.cell-expand-btn:hover { background: var(--accent); color: #000; }

/* Expand hint */
.expand-hint {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 0.6rem;
  color: rgba(255,255,255,.3);
  background: rgba(0,0,0,.4);
  padding: 2px 6px;
  border-radius: 3px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s;
}
.camera-cell:hover .expand-hint { opacity: 1; }

/* No cameras state */
.no-cameras-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-dim);
  gap: 12px;
}
.no-cam-icon { font-size: 3rem; opacity: 0.3; }
.no-cam-sub  { font-size: 0.8rem; opacity: 0.7; }

/* ── Lightbox ────────────────────────────────────────────────────────────── */
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.88);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.lightbox-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  width: 100%;
  max-width: 900px;
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0,0,0,.6);
}

.lightbox-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
  flex-shrink: 0;
}

.lightbox-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.95rem;
  font-weight: 700;
}

.lightbox-loc {
  font-size: 0.8rem;
  color: var(--text-dim);
  font-weight: 400;
}

.lightbox-close {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 1.4rem;
  cursor: pointer;
  transition: color 0.2s;
}
.lightbox-close:hover { color: var(--danger); }

.lightbox-feed-wrap {
  position: relative;
  flex: 1;
  background: #000;
  overflow: hidden;
  min-height: 300px;
}

.lightbox-feed {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.lightbox-alert-strip {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(255,59,59,.85);
  color: #fff;
  text-align: center;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 8px;
  animation: stripPulse 1.5s ease-in-out infinite;
}

/* Lightbox detections */
.lightbox-detections {
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.lightbox-detections h4 {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-dim);
  margin: 0 0 10px;
}

.lb-no-det { font-size: 0.8rem; color: var(--text-dim); font-style: italic; }

.lb-det-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 6px;
}

.lb-det-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.78rem;
}

.lb-weapon {
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}
.lb-weapon.knife        { background: rgba(231,60,140,.2); color: #e73c8c; }
.lb-weapon.pistol       { background: rgba(54,56,202,.2);  color: #8890ff; }
.lb-weapon.heavy_weapon { background: rgba(155,89,182,.2); color: #c39bd3; }

.lb-conf { color: var(--warn); font-weight: 600; margin-left: auto; }
.lb-time { color: var(--text-dim); white-space: nowrap; }

/* Lightbox fade transition */
.lightbox-fade-enter-active, .lightbox-fade-leave-active { transition: all 0.25s ease; }
.lightbox-fade-enter-from, .lightbox-fade-leave-to { opacity: 0; transform: scale(0.97); }

/* ── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 900px) {
  .mc-stats { grid-template-columns: 1fr 1fr; }
  .grid-2x3, .grid-3x3 { grid-template-columns: 1fr 1fr; }
}

@media (max-width: 600px) {
  .mc-stats { grid-template-columns: 1fr 1fr; }
  .grid-1x2, .grid-2x2, .grid-2x3, .grid-3x3 { grid-template-columns: 1fr; }
  .camera-cell.cell-expanded { grid-column: span 1; grid-row: span 1; }
  .mc-header { flex-direction: column; align-items: flex-start; }
}
</style>
