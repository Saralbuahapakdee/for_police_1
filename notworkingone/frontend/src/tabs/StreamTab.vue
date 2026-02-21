<!-- src/tabs/StreamTab.vue - SIMPLIFIED: Always show all bounding boxes, no preferences -->
<template>
  <div class="stream-tab">
    <!-- Camera Selector -->
    <div class="camera-selector">
      <h2>📹 Select Camera</h2>
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
    
    <!-- Video Stream with Overlay -->
    <div class="stream-container">
      <h3 class="stream-title">
        {{ selectedCamera?.camera_name || 'Select a camera' }}
      </h3>
      <p class="stream-location">{{ selectedCamera?.location }}</p>
      
      <div v-if="selectedCamera" class="video-wrapper">
        <img :src="videoUrl" class="video-stream" alt="AI Stream" ref="videoElement" />
        
        <!-- Canvas overlay for bounding boxes -->
        <canvas 
          ref="canvasElement"
          class="bounding-box-canvas"
          :width="canvasWidth"
          :height="canvasHeight"
        ></canvas>
      </div>
      
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
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import detectionService from '../services/detectionService.js'

const props = defineProps({
  token: String
})

const cameras = ref([])
const selectedCamera = ref(null)
const allRecentDetections = ref([])
const detectionState = ref({
  detected: false,
  objects: {},
  timestamp: null
})

const videoElement = ref(null)
const canvasElement = ref(null)
const canvasWidth = ref(640)
const canvasHeight = ref(480)

let unsubscribe = null
let animationFrameId = null

// Weapon colors
const weaponColors = {
  'gun': '#FF0000',
  'pistol': '#FF0000',
  'heavy-weapon': '#FF00FF',
  'heavy_weapon': '#FF00FF',
  'knife': '#FFFF00'
}

const videoUrl = computed(() => {
  if (!selectedCamera.value) return ''
  return `/api/video?token=${props.token}&camera_id=${selectedCamera.value.id}`
})

const recentDetections = computed(() => {
  if (!selectedCamera.value) return []
  return allRecentDetections.value.filter(d => d.camera_id === selectedCamera.value.id)
})

onMounted(async () => {
  console.log('🔵 StreamTab mounted')
  
  await loadCameras()
  await loadRecentDetections()
  
  // Subscribe to detection service for real-time updates
  unsubscribe = detectionService.subscribe((state) => {
    detectionState.value = state.currentDetection
    drawBoundingBoxes()
  })
  
  // Setup canvas resize observer
  setupCanvasResize()
  
  // Start drawing loop
  startDrawingLoop()
  
  // Refresh detections every 10 seconds
  setInterval(loadRecentDetections, 10000)
  
  console.log('✅ StreamTab initialization complete')
})

onBeforeUnmount(() => {
  console.log('🔴 StreamTab unmounting')
  
  if (unsubscribe) {
    unsubscribe()
  }
  
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})

function setupCanvasResize() {
  const updateSize = () => {
    if (videoElement.value) {
      canvasWidth.value = videoElement.value.clientWidth || 640
      canvasHeight.value = videoElement.value.clientHeight || 480
      nextTick(() => drawBoundingBoxes())
    }
  }
  
  window.addEventListener('resize', updateSize)
  setTimeout(updateSize, 100)
  
  onBeforeUnmount(() => {
    window.removeEventListener('resize', updateSize)
  })
}

function startDrawingLoop() {
  const draw = () => {
    drawBoundingBoxes()
    animationFrameId = requestAnimationFrame(draw)
  }
  animationFrameId = requestAnimationFrame(draw)
}

function drawBoundingBoxes() {
  const canvas = canvasElement.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  if (!detectionState.value || !detectionState.value.detected) {
    return
  }
  
  const scaleX = canvas.width / 640
  const scaleY = canvas.height / 480
  
  // Draw boxes for ALL detected weapons (no filtering)
  for (const [weaponType, data] of Object.entries(detectionState.value.objects || {})) {
    const boxes = data.boxes || []
    const confidences = Array.isArray(data.confidences) 
      ? data.confidences 
      : [data.confidences]
    
    const color = weaponColors[weaponType] || '#00FF00'
    
    boxes.forEach((box, index) => {
      const [x1, y1, x2, y2] = box
      const confidence = confidences[index] || confidences[0] || 0
      
      const scaledX = x1 * scaleX
      const scaledY = y1 * scaleY
      const scaledWidth = (x2 - x1) * scaleX
      const scaledHeight = (y2 - y1) * scaleY
      
      // Draw bounding box
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(scaledX, scaledY, scaledWidth, scaledHeight)
      
      // Draw label background
      const label = `${formatWeaponName(weaponType)} ${(confidence * 100).toFixed(0)}%`
      ctx.font = 'bold 14px Arial'
      const textMetrics = ctx.measureText(label)
      const textHeight = 20
      
      ctx.fillStyle = color
      ctx.fillRect(scaledX, scaledY - textHeight, textMetrics.width + 10, textHeight)
      
      // Draw label text
      ctx.fillStyle = '#000000'
      ctx.fillText(label, scaledX + 5, scaledY - 5)
      
      // Draw corner markers
      const cornerSize = 15
      ctx.lineWidth = 4
      
      // Top-left
      ctx.beginPath()
      ctx.moveTo(scaledX, scaledY + cornerSize)
      ctx.lineTo(scaledX, scaledY)
      ctx.lineTo(scaledX + cornerSize, scaledY)
      ctx.stroke()
      
      // Top-right
      ctx.beginPath()
      ctx.moveTo(scaledX + scaledWidth - cornerSize, scaledY)
      ctx.lineTo(scaledX + scaledWidth, scaledY)
      ctx.lineTo(scaledX + scaledWidth, scaledY + cornerSize)
      ctx.stroke()
      
      // Bottom-left
      ctx.beginPath()
      ctx.moveTo(scaledX, scaledY + scaledHeight - cornerSize)
      ctx.lineTo(scaledX, scaledY + scaledHeight)
      ctx.lineTo(scaledX + cornerSize, scaledY + scaledHeight)
      ctx.stroke()
      
      // Bottom-right
      ctx.beginPath()
      ctx.moveTo(scaledX + scaledWidth - cornerSize, scaledY + scaledHeight)
      ctx.lineTo(scaledX + scaledWidth, scaledY + scaledHeight)
      ctx.lineTo(scaledX + scaledWidth, scaledY + scaledHeight - cornerSize)
      ctx.stroke()
    })
  }
}

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
    'gun': 'Pistol',
    'heavy_weapon': 'Heavy Weapon',
    'heavy-weapon': 'Heavy Weapon'
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
  gap: 20px;
}

.camera-selector {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.camera-selector h2 {
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

.video-wrapper {
  position: relative;
  display: inline-block;
  max-width: 100%;
  margin-bottom: 20px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.video-stream {
  display: block;
  max-width: 100%;
  max-height: 60vh;
  border: 1px solid #ddd;
}

.bounding-box-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.recent-detections {
  text-align: left;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 2px solid #e0e0e0;
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
}
</style>