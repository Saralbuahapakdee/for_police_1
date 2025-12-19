<template>
  <div class="multi-camera-tab">
    <div class="camera-grid-header">
      <h3>📹 Multi-Camera View</h3>
      <div class="header-controls">
        <select v-model="gridSize" class="grid-select">
          <option value="2x2">2x2 Grid (4 cameras)</option>
          <option value="3x3">3x3 Grid (9 cameras)</option>
          <option value="2x3">2x3 Grid (6 cameras)</option>
        </select>
        <button @click="toggleFullscreen" class="fullscreen-btn">
          {{ isFullscreen ? '🗗 Exit Fullscreen' : '⛶ Fullscreen' }}
        </button>
      </div>
    </div>

    <!-- Alert Banner for New Detections -->
    <div v-if="latestIncident" class="alert-banner">
      <div class="alert-content">
        <div class="alert-icon">🚨</div>
        <div class="alert-info">
          <strong>WEAPON DETECTED!</strong>
          <span>{{ formatWeaponName(latestIncident.weapon_type) }} at {{ latestIncident.camera_name }}</span>
        </div>
        <button @click="focusCamera(latestIncident.camera_id)" class="alert-action">
          View Camera
        </button>
        <button @click="dismissAlert" class="alert-dismiss">✕</button>
      </div>
    </div>

    <!-- Camera Grid -->
    <div :class="['camera-grid', `grid-${gridSize}`]" ref="gridContainer">
      <div v-for="camera in displayedCameras" :key="camera.id" 
           :class="['camera-cell', { 'has-incident': hasRecentIncident(camera.id), 'focused': focusedCamera === camera.id }]"
           @click="toggleFocus(camera.id)">
        <div class="camera-header-bar">
          <span class="camera-name">{{ camera.camera_name }}</span>
          <span v-if="hasRecentIncident(camera.id)" class="incident-badge">
            🚨 ALERT
          </span>
        </div>
        <img :src="`/api/video?token=${token}&camera_id=${camera.id}`" 
             class="camera-stream" 
             :alt="camera.camera_name" />
        <div class="camera-info-bar">
          <span class="camera-location">{{ camera.location }}</span>
          <span class="camera-status">🟢 Live</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  token: String
})

const cameras = ref([])
const incidents = ref([])
const gridSize = ref('2x2')
const focusedCamera = ref(null)
const latestIncident = ref(null)
const isFullscreen = ref(false)
const gridContainer = ref(null)
const lastIncidentId = ref(null)

let refreshInterval = null
let notificationPermission = 'default'

const displayedCameras = computed(() => {
  const maxCameras = {
    '2x2': 4,
    '2x3': 6,
    '3x3': 9
  }[gridSize.value] || 4
  
  return cameras.value.slice(0, maxCameras)
})

const recentIncidents = computed(() => {
  return incidents.value.slice(0, 10)
})

onMounted(async () => {
  await loadCameras()
  await loadIncidents()
  
  // Request notification permission
  if ('Notification' in window) {
    notificationPermission = await Notification.requestPermission()
  }
  
  // Refresh every 5 seconds
  refreshInterval = setInterval(async () => {
    await loadIncidents()
    checkForNewIncidents()
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

async function loadCameras() {
  try {
    const res = await fetch('/api/cameras')
    if (res.ok) {
      const data = await res.json()
      cameras.value = data.cameras
    }
  } catch (error) {
    console.error('Could not load cameras:', error)
  }
}

async function loadIncidents() {
  try {
    const res = await fetch('/api/incidents?limit=20', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      incidents.value = data.incidents
    }
  } catch (error) {
    console.error('Could not load incidents:', error)
  }
}

function checkForNewIncidents() {
  if (incidents.value.length === 0) return
  
  const newest = incidents.value[0]
  
  // Check if this is a new incident
  if (lastIncidentId.value !== newest.id) {
    lastIncidentId.value = newest.id
    
    // Only alert for pending/responding incidents
    if (newest.status === 'pending' || newest.status === 'responding') {
      showAlert(newest)
      playAlertSound()
      showBrowserNotification(newest)
      sendEmailNotification(newest)
      
      // Auto-focus camera
      focusCamera(newest.camera_id)
    }
  }
}

function showAlert(incident) {
  latestIncident.value = incident
  
  // Auto-dismiss after 15 seconds
  setTimeout(() => {
    if (latestIncident.value?.id === incident.id) {
      latestIncident.value = null
    }
  }, 15000)
}

function dismissAlert() {
  latestIncident.value = null
}

function playAlertSound() {
  // Play alarm sound: 3 beeps
  playBeep(880, 0.2, 0) // First beep
  playBeep(880, 0.2, 0.3) // Second beep
  playBeep(880, 0.4, 0.6) // Third beep (longer)
}

function playBeep(frequency = 880, duration = 0.2, delay = 0) {
  setTimeout(() => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      
      oscillator.frequency.value = frequency
      oscillator.type = 'sine'
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration)
      
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + duration)
    } catch (error) {
      console.error('Could not play beep:', error)
    }
  }, delay * 1000)
}

function showBrowserNotification(incident) {
  if (notificationPermission === 'granted') {
    new Notification('🚨 Weapon Detected!', {
      body: `${formatWeaponName(incident.weapon_type)} detected at ${incident.camera_name}`,
      icon: '/icon-alert.png',
      tag: 'weapon-detection',
      requireInteraction: true
    })
  }
}

async function sendEmailNotification(incident) {
  try {
    await fetch('/api/send-alert-email', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({
        incident_id: incident.id,
        weapon_type: incident.weapon_type,
        camera_name: incident.camera_name,
        location: incident.camera_location,
        detected_at: incident.detected_at
      })
    })
  } catch (error) {
    console.error('Could not send email:', error)
  }
}

function hasRecentIncident(cameraId) {
  const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000)
  return incidents.value.some(inc => 
    inc.camera_id === cameraId && 
    new Date(inc.detected_at) > fiveMinutesAgo &&
    inc.status !== 'resolved'
  )
}

function focusCamera(cameraId) {
  focusedCamera.value = focusedCamera.value === cameraId ? null : cameraId
}

function toggleFocus(cameraId) {
  focusCamera(cameraId)
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    gridContainer.value?.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

function formatWeaponName(weaponType) {
  const names = {
    'knife': 'Knife',
    'pistol': 'Pistol',
    'heavy_weapon': 'Heavy Weapon'
  }
  return names[weaponType] || weaponType
}

function formatTime(timeString) {
  if (!timeString) return 'N/A'
  try {
    return new Date(timeString).toLocaleTimeString()
  } catch {
    return 'N/A'
  }
}
</script>

<style scoped>
.multi-camera-tab {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.camera-grid-header {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.camera-grid-header h3 {
  color: #2c3e50;
  margin: 0;
}

.header-controls {
  display: flex;
  gap: 10px;
}

.grid-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
}

.fullscreen-btn {
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.fullscreen-btn:hover {
  background: #2980b9;
}

/* Alert Banner */
.alert-banner {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  padding: 15px 20px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.9; }
}

.alert-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.alert-icon {
  font-size: 2rem;
  animation: shake 0.5s ease-in-out infinite;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.alert-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.alert-info strong {
  font-size: 1.1rem;
}

.alert-action {
  padding: 8px 16px;
  background: white;
  color: #e74c3c;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.alert-action:hover {
  transform: scale(1.05);
}

.alert-dismiss {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 5px 10px;
}

/* Camera Grid */
.camera-grid {
  display: grid;
  gap: 15px;
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  flex: 1;
}

.camera-grid.grid-2x2 {
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
}

.camera-grid.grid-3x3 {
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(3, 1fr);
}

.camera-grid.grid-2x3 {
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
}

.camera-cell {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 3px solid transparent;
}

.camera-cell:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.camera-cell.has-incident {
  border-color: #e74c3c;
  box-shadow: 0 0 20px rgba(231, 76, 60, 0.5);
  animation: borderPulse 1s ease-in-out infinite;
}

@keyframes borderPulse {
  0%, 100% { border-color: #e74c3c; }
  50% { border-color: #c0392b; }
}

.camera-cell.focused {
  grid-column: span 2;
  grid-row: span 2;
  z-index: 10;
}

.camera-header-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  background: linear-gradient(180deg, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%);
  padding: 10px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 2;
}

.camera-name {
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
}

.incident-badge {
  background: #e74c3c;
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.camera-stream {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-info-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(0deg, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%);
  padding: 10px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 2;
}

.camera-location {
  color: white;
  font-size: 0.8rem;
}

.camera-status {
  color: #2ecc71;
  font-size: 0.8rem;
  font-weight: 600;
}

/* Incidents Sidebar */
.incidents-sidebar {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-height: 400px;
  overflow-y: auto;
}

.incidents-sidebar h4 {
  color: #2c3e50;
  margin-bottom: 15px;
}

.no-incidents {
  text-align: center;
  color: #7f8c8d;
  padding: 20px;
  font-style: italic;
}

.incident-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.incident-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #e74c3c;
  cursor: pointer;
  transition: all 0.3s ease;
}

.incident-item:hover {
  background: #ecf0f1;
  transform: translateX(5px);
}

.incident-time {
  font-size: 0.8rem;
  color: #7f8c8d;
  margin-bottom: 5px;
}

.incident-details {
  display: flex;
  gap: 10px;
  align-items: center;
}

.weapon-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: 600;
}

.weapon-badge.knife {
  background: #ffebee;
  color: #e74c3c;
}

.weapon-badge.pistol {
  background: #fff3e0;
  color: #f39c12;
}

.weapon-badge.heavy_weapon {
  background: #f3e5f5;
  color: #9b59b6;
}

.incident-camera {
  font-size: 0.85rem;
  color: #2c3e50;
}

@media (max-width: 768px) {
  .camera-grid.grid-2x2,
  .camera-grid.grid-3x3,
  .camera-grid.grid-2x3 {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }
  
  .camera-cell.focused {
    grid-column: span 1;
    grid-row: span 1;
  }
}
</style>
