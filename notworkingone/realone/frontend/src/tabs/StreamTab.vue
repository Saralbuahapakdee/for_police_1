<template>
  <div class="stream-tab">
    <!-- Camera Selector -->
    <div class="camera-selector">
      <h3>📹 Select Camera</h3>
      <div class="camera-buttons">
        <button 
          v-for="camera in cameras" 
          :key="camera.id"
          @click="selectCamera(camera)"
          :class="['camera-btn', { active: selectedCamera?.id === camera.id }]"
        >
          {{ camera.camera_name }}
          <span class="camera-loc">{{ camera.location }}</span>
        </button>
      </div>
    </div>

    <!-- Weapon Preferences -->
    <div class="stream-controls">
      <h3>⚙️ Weapon Detection Preferences</h3>
      <div v-if="weaponPreferences.length === 0" class="loading-preferences">
        Loading weapon preferences...
      </div>
      <div v-else class="weapon-filters">
        <label v-for="pref in weaponPreferences" :key="pref.weapon_type" class="weapon-checkbox">
          <input 
            type="checkbox" 
            :checked="pref.is_enabled"
            @change="updateWeaponPreference(pref.weapon_type, $event.target.checked)"
          />
          <span class="weapon-name">{{ formatWeaponName(pref.weapon_type) }}</span>
        </label>
      </div>
      <button @click="savePreferences" class="save-preferences-btn" :disabled="isSaving">
        {{ isSaving ? 'Saving...' : 'Save Preferences' }}
      </button>
    </div>
    
    <!-- Video Stream -->
    <div class="stream-container">
      <h3 class="stream-title">
        Live Feed: {{ selectedCamera?.camera_name || 'Select a camera' }}
      </h3>
      <p class="stream-location">📍 {{ selectedCamera?.location }}</p>
      <img v-if="selectedCamera" :src="videoUrl" class="video-stream" alt="AI Stream" />
      
      <!-- Recent Detections -->
      <div class="recent-detections">
        <h4>Recent Detections (This Camera)</h4>
        <div v-if="recentDetections.length === 0" class="no-detections">
          No detections yet
        </div>
        <div v-else class="detection-list">
          <div v-for="(detection, index) in recentDetections.slice(0, 5)" :key="index" class="detection-item">
            <span class="weapon-type">{{ formatWeaponName(detection.weapon_type) }}</span>
            <span class="confidence">{{ Math.round(detection.confidence_score * 100) }}%</span>
            <span class="time">{{ formatTime(detection.detection_time) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'

const props = defineProps({
  token: String
})

const cameras = ref([])
const selectedCamera = ref(null)
const weaponPreferences = ref([])
const allRecentDetections = ref([])
const isSaving = ref(false)

const videoUrl = computed(() => {
  if (!selectedCamera.value) return ''
  return `/api/video?token=${props.token}&camera_id=${selectedCamera.value.id}`
})

const recentDetections = computed(() => {
  if (!selectedCamera.value) return []
  return allRecentDetections.value.filter(d => d.camera_id === selectedCamera.value.id)
})

onMounted(async () => {
  await Promise.all([
    loadCameras(),
    loadWeaponPreferences(),
    loadRecentDetections()
  ])
  
  // Refresh detections every 10 seconds
  setInterval(loadRecentDetections, 10000)
})

async function loadCameras() {
  try {
    const res = await fetch('/api/cameras')
    if (res.ok) {
      const data = await res.json()
      cameras.value = data.cameras
      if (cameras.value.length > 0) {
        selectedCamera.value = cameras.value[0]
      }
    }
  } catch (error) {
    console.error('Could not load cameras:', error)
    // Create default camera if API fails
    cameras.value = [{
      id: 1,
      camera_name: 'Main Entrance',
      location: 'Building A - Front Gate'
    }]
    selectedCamera.value = cameras.value[0]
  }
}

function selectCamera(camera) {
  selectedCamera.value = camera
}

async function loadWeaponPreferences() {
  try {
    const res = await fetch('/api/weapon-preferences', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      weaponPreferences.value = data.preferences
      
      // Create defaults if empty
      if (weaponPreferences.value.length === 0) {
        weaponPreferences.value = [
          { weapon_type: 'knife', is_enabled: true },
          { weapon_type: 'pistol', is_enabled: true },
          { weapon_type: 'heavy_weapon', is_enabled: true }
        ]
      }
    }
  } catch (error) {
    console.error('Could not load weapon preferences:', error)
  }
}

function updateWeaponPreference(weaponType, enabled) {
  const pref = weaponPreferences.value.find(p => p.weapon_type === weaponType)
  if (pref) {
    pref.is_enabled = enabled
  }
}

async function savePreferences() {
  isSaving.value = true
  
  try {
    const res = await fetch('/api/weapon-preferences', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}` 
      },
      body: JSON.stringify({ preferences: weaponPreferences.value })
    })
    
    if (res.ok) {
      // Show success briefly
      setTimeout(() => {}, 1000)
    }
  } catch (error) {
    console.error('Could not save preferences:', error)
  }
  
  isSaving.value = false
}

async function loadRecentDetections() {
  try {
    const res = await fetch(`/api/dashboard-data?days=1`, {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      allRecentDetections.value = data.recent_detections
    }
  } catch (error) {
    console.error('Could not load recent detections:', error)
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
.stream-tab {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.camera-selector {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.camera-selector h3 {
  margin-bottom: 15px;
  color: #2c3e50;
}

.camera-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.camera-btn {
  padding: 12px 16px;
  background: #f8f9fa;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: all 0.3s ease;
  font-size: 1rem;
}

.camera-btn:hover {
  border-color: #4a90e2;
  background: #e8f4fd;
}

.camera-btn.active {
  background: #4a90e2;
  color: white;
  border-color: #4a90e2;
}

.camera-btn.active .camera-loc {
  color: rgba(255, 255, 255, 0.8);
}

.camera-loc {
  display: block;
  font-size: 0.85rem;
  color: #7f8c8d;
  margin-top: 4px;
}

.stream-controls {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stream-controls h3 {
  margin-bottom: 15px;
  color: #2c3e50;
}

.loading-preferences {
  color: #7f8c8d;
  font-style: italic;
  padding: 20px 0;
  text-align: center;
}

.weapon-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
}

.weapon-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background-color 0.3s ease;
}

.weapon-checkbox:hover {
  background-color: #f8f9fa;
}

.weapon-checkbox input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.weapon-name {
  font-weight: 500;
  color: #2c3e50;
}

.save-preferences-btn {
  padding: 10px 20px;
  background-color: #27ae60;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.save-preferences-btn:hover:not(:disabled) {
  background-color: #219a52;
}

.save-preferences-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.stream-container {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.stream-title {
  font-size: 1.5rem;
  margin-bottom: 8px;
  color: #2c3e50;
}

.stream-location {
  color: #7f8c8d;
  margin-bottom: 20px;
}

.video-stream {
  max-width: 100%;
  max-height: 60vh;
  border-radius: 8px;
  border: 1px solid #ddd;
  margin-bottom: 20px;
}

.recent-detections {
  text-align: left;
}

.recent-detections h4 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.no-detections {
  color: #7f8c8d;
  font-style: italic;
}

.detection-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 6px;
}

.weapon-type {
  font-weight: 600;
  color: #e74c3c;
}

.confidence {
  color: #f39c12;
  font-weight: 500;
}

.time {
  color: #7f8c8d;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .camera-buttons {
    grid-template-columns: 1fr;
  }
  
  .weapon-filters {
    flex-direction: column;
  }
}
</style>