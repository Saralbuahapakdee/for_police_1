<template>
  <div class="multi-camera-tab">
    <div class="camera-grid-header">
      <h2>📹 Multi-Camera View</h2>
      <div class="header-controls">
        <select v-if="!isFullView" v-model="gridSize" class="grid-select">
          <option value="2x2">2x2 Grid (4 cameras)</option>
          <option value="3x3">3x3 Grid (9 cameras)</option>
          <option value="2x3">2x3 Grid (6 cameras)</option>
        </select>
        <button v-if="isFullView" @click="exitFullView" class="exit-full-btn">
          ← Back to Grid View
        </button>
      </div>
    </div>

    <!-- Camera Grid -->
    <div :class="['camera-grid', `grid-${gridSize}`, { 'full-view': isFullView }]" ref="gridContainer">
      <div v-for="camera in displayedCameras" :key="camera.id" 
           :class="['camera-cell', { 'has-incident': hasRecentIncident(camera.id) }]"
           @click="toggleFocus(camera.id)"
           :title="isFullView ? 'Click to return to grid view' : 'Click to view full screen'">
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
import { ref, computed, onMounted, onBeforeUnmount, onUnmounted } from 'vue'

const props = defineProps({
  token: String
})

const cameras = ref([])
const incidents = ref([])
const gridSize = ref('2x2')
const focusedCamera = ref(null)
const isFullView = ref(false)
const isFullscreen = ref(false)
const gridContainer = ref(null)
const lastIncidentId = ref(null)

let refreshIntervalId = null
let notificationPermission = 'default'

const displayedCameras = computed(() => {
  if (isFullView.value && focusedCamera.value) {
    return cameras.value.filter(c => c.id === focusedCamera.value)
  }
  
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
  console.log('📹 MultiCameraTab MOUNTED - starting polling')
  
  await loadCameras()
  await loadIncidents()
  
  if ('Notification' in window) {
    notificationPermission = await Notification.requestPermission()
  }
  
  startPolling()
})

onBeforeUnmount(() => {
  console.log('📹 MultiCameraTab BEFORE UNMOUNT - stopping polling')
  stopPolling()
})

onUnmounted(() => {
  console.log('📹 MultiCameraTab UNMOUNTED - final cleanup')
  stopPolling()
  
  cameras.value = []
  incidents.value = []
  lastIncidentId.value = null
})

function startPolling() {
  stopPolling()
  
  console.log('🔄 Starting incident polling...')
  
  refreshIntervalId = setInterval(async () => {
    console.log('🔄 Polling for incidents... (interval ID:', refreshIntervalId, ')')
    await loadIncidents()
    checkForNewIncidents()
  }, 5000)
  
  console.log('✅ Polling started with interval ID:', refreshIntervalId)
}

function stopPolling() {
  if (refreshIntervalId !== null) {
    console.log('🛑 STOPPING interval ID:', refreshIntervalId)
    clearInterval(refreshIntervalId)
    refreshIntervalId = null
    console.log('✅ Interval cleared')
  } else {
    console.log('⚠️ No interval to clear')
  }
}

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
    } else {
      console.error('Failed to load incidents:', res.status)
    }
  } catch (error) {
    console.error('Could not load incidents:', error)
  }
}

function checkForNewIncidents() {
  if (incidents.value.length === 0) return
  
  const newest = incidents.value[0]
  
  // Check if this is a new incident (ONLY FROM REAL MQTT DATA)
  if (lastIncidentId.value !== newest.id) {
    lastIncidentId.value = newest.id
    
    // Only alert for pending/responding incidents
    if (newest.status === 'pending' || newest.status === 'responding') {
      showAlert(newest)
      playAlertSound()
      showBrowserNotification(newest)
      
      // Auto-focus camera
      focusCamera(newest.camera_id)
    }
  }
}

function playAlertSound() {
  // Play alarm sound: 3 beeps
  playBeep(880, 0.2, 0)
  playBeep(880, 0.2, 0.3)
  playBeep(880, 0.4, 0.6)
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
  if (isFullView.value && focusedCamera.value === cameraId) {
    isFullView.value = false
    focusedCamera.value = null
  } else {
    isFullView.value = true
    focusedCamera.value = cameraId
  }
}

function exitFullView() {
  isFullView.value = false
  focusedCamera.value = null
}

function formatWeaponName(weaponType) {
  const names = {
    'knife': 'Knife',
    'pistol': 'Pistol',
    'heavy_weapon': 'Heavy Weapon'
  }
  return names[weaponType] || weaponType
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

.camera-grid-header h2 {
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
  font-size: 0.95rem;
  cursor: pointer;
}

.exit-full-btn {
  padding: 8px 16px;
  background: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.3s ease;
}

.exit-full-btn:hover {
  background: #357ab7;
  transform: translateX(-2px);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.9; }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.camera-grid {
  display: grid;
  gap: 15px;
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  flex: 1;
}

.camera-grid.full-view {
  display: flex;
  padding: 0;
  background: transparent;
  box-shadow: none;
}

.camera-grid.full-view .camera-cell {
  width: 100%;
  height: 100%;
  border-radius: 12px;
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
  min-height: 200px;
}

.full-view .camera-cell {
  min-height: 100%;
  border-radius: 12px;
  border: none;
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

.full-view .camera-header-bar {
  padding: 20px 30px;
}

.camera-name {
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
}

.full-view .camera-name {
  font-size: 1.5rem;
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

.full-view .camera-info-bar {
  padding: 20px 30px;
}

.camera-location {
  color: white;
  font-size: 0.8rem;
}

.full-view .camera-location {
  font-size: 1.2rem;
}

.camera-status {
  color: #2ecc71;
  font-size: 0.8rem;
  font-weight: 600;
}

.full-view .camera-status {
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .camera-grid.grid-2x2,
  .camera-grid.grid-3x3,
  .camera-grid.grid-2x3 {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }
}
</style>