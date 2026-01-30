<!-- src/tabs/LogsTab.vue - UPDATED with time filter -->
<template>
  <div class="logs-tab">
    <div class="logs-header">
      <h2>📋 Detection Logs</h2>
      <div class="logs-filters">
        <select v-model="filterCamera" @change="loadLogs" class="filter-select">
          <option :value="null">All Cameras</option>
          <option v-for="camera in cameras" :key="camera.id" :value="camera.id">
            {{ camera.camera_name }}
          </option>
        </select>
        
        <select v-model="filterWeapon" @change="loadLogs" class="filter-select">
          <option :value="null">All Weapons</option>
          <option value="knife">Knife</option>
          <option value="pistol">Pistol</option>
          <option value="heavy_weapon">Heavy Weapon</option>
        </select>
        
        <select v-model="dateRangeType" @change="handleDateRangeChange" class="filter-select">
          <option value="preset">Quick Select</option>
          <option value="custom">Custom Range</option>
        </select>

        <select v-if="dateRangeType === 'preset'" v-model="filterDays" @change="loadLogs" class="filter-select">
          <option :value="1">Today</option>
          <option :value="7">Last 7 days</option>
          <option :value="14">Last 2 weeks</option>
          <option :value="30">Last 30 days</option>
          <option :value="60">Last 2 months</option>
          <option :value="90">Last 3 months</option>
          <option :value="180">Last 6 months</option>
          <option :value="365">Last year</option>
        </select>

        <template v-if="dateRangeType === 'custom'">
          <input 
            type="date" 
            v-model="startDate" 
            @change="loadLogs"
            :max="endDate"
            class="date-input"
          />
          <input 
            type="date" 
            v-model="endDate" 
            @change="loadLogs"
            :min="startDate"
            :max="today"
            class="date-input"
          />
        </template>
        
        <!-- NEW: Time filter -->
        <input 
          type="time" 
          v-model="startTime" 
          @change="loadLogs"
          class="time-input"
          placeholder="From"
          title="Filter by start time (e.g., 09:00)"
        />
        <input 
          type="time" 
          v-model="endTime" 
          @change="loadLogs"
          class="time-input"
          placeholder="To"
          title="Filter by end time (e.g., 17:00)"
        />
        
        <button v-if="startTime || endTime" 
                @click="clearTimeFilter" 
                class="clear-time-btn"
                title="Clear time filter">
          ⌫
        </button>
        
        <button @click="exportToCSV" class="export-btn" title="Export to CSV">
          📥 Export
        </button>

        <button @click="loadLogs" class="refresh-btn" title="Refresh">
          🔄
        </button>
      </div>
    </div>

    <!-- Summary Stats -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">Total Detections</div>
        <div class="stat-value">{{ filteredLogs.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Cameras Monitored</div>
        <div class="stat-value">{{ uniqueCameras }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Weapon Types</div>
        <div class="stat-value">{{ uniqueWeapons }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Average Confidence</div>
        <div class="stat-value">{{ avgConfidence }}%</div>
      </div>
    </div>

    <div class="logs-table-container">
      <table class="logs-table">
        <thead>
          <tr>
            <th @click="sortBy('detection_time')" class="sortable">
              Date & Time 
              <span v-if="sortColumn === 'detection_time'" class="sort-icon">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('camera_name')" class="sortable">
              Camera
              <span v-if="sortColumn === 'camera_name'" class="sort-icon">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('location')" class="sortable">
              Location
              <span v-if="sortColumn === 'location'" class="sort-icon">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('weapon_type')" class="sortable">
              Weapon Type
              <span v-if="sortColumn === 'weapon_type'" class="sort-icon">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('confidence_score')" class="sortable">
              Confidence
              <span v-if="sortColumn === 'confidence_score'" class="sort-icon">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
            <th @click="sortBy('username')" class="sortable">
              Detected By
              <span v-if="sortColumn === 'username'" class="sort-icon">
                {{ sortDirection === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="6" class="loading-cell">Loading logs...</td>
          </tr>
          <tr v-else-if="sortedLogs.length === 0">
            <td colspan="6" class="no-data">No detection logs found for selected filters</td>
          </tr>
          <tr v-else v-for="log in sortedLogs" :key="log.id" class="log-row">
            <td>{{ formatDateTime(log.detection_time) }}</td>
            <td><strong>{{ log.camera_name }}</strong></td>
            <td>{{ log.location }}</td>
            <td>
              <span :class="['weapon-badge', log.weapon_type]">
                {{ formatWeaponName(log.weapon_type) }}
              </span>
            </td>
            <td>
              <span class="confidence-badge" :class="getConfidenceClass(log.confidence_score)">
                {{ Math.round(log.confidence_score * 100) }}%
              </span>
            </td>
            <td>{{ log.username }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  token: String
})

const cameras = ref([])
const logs = ref([])
const filterCamera = ref(null)
const filterWeapon = ref(null)
const dateRangeType = ref('preset')
const filterDays = ref(7)
const isLoading = ref(false)

const today = new Date().toISOString().split('T')[0]
const startDate = ref(getDateDaysAgo(7))
const endDate = ref(today)

// NEW: Time filter
const startTime = ref('')
const endTime = ref('')

// Sorting
const sortColumn = ref('detection_time')
const sortDirection = ref('desc')

function getDateDaysAgo(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date.toISOString().split('T')[0]
}

// NEW: Filter logs by time of day
const filteredLogs = computed(() => {
  if (!startTime.value && !endTime.value) {
    return logs.value
  }
  
  return logs.value.filter(log => {
    try {
      const logTime = new Date(log.detection_time).toTimeString().slice(0, 5) // HH:MM format
      
      if (startTime.value && endTime.value) {
        if (startTime.value <= endTime.value) {
          // Normal range (e.g., 09:00 to 17:00)
          return logTime >= startTime.value && logTime <= endTime.value
        } else {
          // Overnight range (e.g., 22:00 to 06:00)
          return logTime >= startTime.value || logTime <= endTime.value
        }
      } else if (startTime.value) {
        return logTime >= startTime.value
      } else if (endTime.value) {
        return logTime <= endTime.value
      }
    } catch (error) {
      console.error('Error filtering log by time:', error)
      return true
    }
    return true
  })
})

const uniqueCameras = computed(() => {
  const cameras = new Set(filteredLogs.value.map(log => log.camera_id))
  return cameras.size
})

const uniqueWeapons = computed(() => {
  const weapons = new Set(filteredLogs.value.map(log => log.weapon_type))
  return weapons.size
})

const avgConfidence = computed(() => {
  if (filteredLogs.value.length === 0) return 0
  const sum = filteredLogs.value.reduce((acc, log) => acc + (log.confidence_score || 0), 0)
  return Math.round((sum / filteredLogs.value.length) * 100)
})

const sortedLogs = computed(() => {
  const sorted = [...filteredLogs.value].sort((a, b) => {
    let aVal = a[sortColumn.value]
    let bVal = b[sortColumn.value]
    
    // Handle date sorting
    if (sortColumn.value === 'detection_time') {
      aVal = new Date(aVal).getTime()
      bVal = new Date(bVal).getTime()
    }
    
    // Handle numeric sorting
    if (sortColumn.value === 'confidence_score') {
      aVal = aVal || 0
      bVal = bVal || 0
    }
    
    // Handle string sorting (case-insensitive)
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      aVal = aVal.toLowerCase()
      bVal = bVal.toLowerCase()
    }
    
    if (sortDirection.value === 'asc') {
      return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
    } else {
      return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
    }
  })
  
  return sorted
})

onMounted(async () => {
  await loadCameras()
  await loadLogs()
})

function sortBy(column) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = column === 'detection_time' ? 'desc' : 'asc'
  }
}

function handleDateRangeChange() {
  if (dateRangeType.value === 'preset') {
    filterDays.value = 7
  } else {
    startDate.value = getDateDaysAgo(7)
    endDate.value = today
  }
  loadLogs()
}

function clearTimeFilter() {
  startTime.value = ''
  endTime.value = ''
  loadLogs()
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

async function loadLogs() {
  isLoading.value = true
  
  try {
    let url = '/api/detection-logs?limit=1000'
    
    if (dateRangeType.value === 'preset') {
      url += `&days=${filterDays.value}`
    } else {
      const start = new Date(startDate.value)
      const end = new Date(endDate.value)
      const diffDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1
      url += `&days=${diffDays}`
    }
    
    if (filterCamera.value) url += `&camera_id=${filterCamera.value}`
    if (filterWeapon.value) url += `&weapon_type=${filterWeapon.value}`
    
    // NEW: Add time filter parameters
    if (startTime.value) url += `&start_time=${startTime.value}`
    if (endTime.value) url += `&end_time=${endTime.value}`
    
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      
      if (dateRangeType.value === 'custom') {
        const start = new Date(startDate.value)
        start.setHours(0, 0, 0, 0)
        const end = new Date(endDate.value)
        end.setHours(23, 59, 59, 999)
        
        logs.value = data.logs.filter(log => {
          const logDate = new Date(log.detection_time)
          return logDate >= start && logDate <= end
        })
      } else {
        logs.value = data.logs
      }
    }
  } catch (error) {
    console.error('Could not load logs:', error)
  }
  
  isLoading.value = false
}

function exportToCSV() {
  if (filteredLogs.value.length === 0) {
    alert('No data to export')
    return
  }
  
  let csv = 'Date,Time,Camera,Location,Weapon Type,Confidence,Detected By\n'
  
  sortedLogs.value.forEach(log => {
    const date = new Date(log.detection_time)
    const dateStr = date.toLocaleDateString()
    const timeStr = date.toLocaleTimeString()
    const conf = Math.round(log.confidence_score * 100)
    
    csv += `"${dateStr}","${timeStr}","${log.camera_name}","${log.location}","${formatWeaponName(log.weapon_type)}",${conf}%,"${log.username}"\n`
  })
  
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  
  const timeFilter = startTime.value || endTime.value ? `_${startTime.value || '00:00'}-${endTime.value || '23:59'}` : ''
  a.download = `detection-logs-${new Date().toISOString().split('T')[0]}${timeFilter}.csv`
  a.click()
  window.URL.revokeObjectURL(url)
}

function formatWeaponName(weaponType) {
  const names = {
    'knife': 'Knife',
    'pistol': 'Pistol',
    'heavy_weapon': 'Heavy Weapon'
  }
  return names[weaponType] || weaponType
}

function formatDateTime(dateTimeString) {
  if (!dateTimeString) return 'N/A'
  try {
    const date = new Date(dateTimeString)
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
  } catch {
    return dateTimeString
  }
}

function getConfidenceClass(score) {
  if (score >= 0.9) return 'high'
  if (score >= 0.75) return 'medium'
  return 'low'
}
</script>

<style scoped>
.logs-tab {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.logs-header h2 {
  color: #2c3e50;
}

.logs-filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-select,
.date-input,
.time-input {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  font-size: 0.875rem;
  cursor: pointer;
}

.date-input {
  min-width: 130px;
}

.time-input {
  min-width: 95px;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
}

.time-input::placeholder {
  color: #7f8c8d;
  font-size: 0.85rem;
}

.filter-select:focus,
.date-input:focus,
.time-input:focus {
  outline: none;
  border-color: #4a90e2;
}

.refresh-btn,
.export-btn,
.clear-time-btn {
  padding: 6px 12px;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.3s ease;
}

.refresh-btn {
  background: #4a90e2;
}

.export-btn {
  background: #27ae60;
}

.clear-time-btn {
  background: #e74c3c;
  font-size: 1rem;
}

.refresh-btn:hover {
  background: #357ab7;
}

.export-btn:hover {
  background: #219a52;
}

.clear-time-btn:hover {
  background: #c0392b;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat-card {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 0.85rem;
  color: #7f8c8d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: #2c3e50;
}

.logs-table-container {
  overflow-x: auto;
  max-height: 500px;
  overflow-y: auto;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
}

.logs-table th {
  background: #f8f9fa;
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #2c3e50;
  border-bottom: 2px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.logs-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s ease;
}

.logs-table th.sortable:hover {
  background: #e9ecef;
}

.sort-icon {
  margin-left: 5px;
  color: #4a90e2;
  font-size: 0.85rem;
}

.logs-table td {
  padding: 12px;
  border-bottom: 1px solid #e9ecef;
  color: #2c3e50;
}

.log-row:hover {
  background: #f8f9fa;
}

.loading-cell,
.no-data {
  text-align: center;
  color: #7f8c8d;
  font-style: italic;
  padding: 40px !important;
}

.weapon-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  display: inline-block;
}

.weapon-badge.knife {
  background: #ffebf4;
  color: #e73c8c;
}

.weapon-badge.pistol {
  background: #e0e2ff;
  color: #3638ca;
}

.weapon-badge.heavy_weapon {
  background: #f3e5f5;
  color: #9b59b6;
}

.confidence-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  display: inline-block;
}

.confidence-badge.high {
  background: #d4edda;
  color: #27ae60;
}

.confidence-badge.medium {
  background: #fff3cd;
  color: #f39c12;
}

.confidence-badge.low {
  background: #f8d7da;
  color: #e74c3c;
}

@media (max-width: 768px) {
  .logs-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .logs-filters {
    flex-direction: column;
    width: 100%;
  }
  
  .filter-select,
  .date-input,
  .time-input,
  .refresh-btn,
  .export-btn,
  .clear-time-btn {
    width: 100%;
  }
  
  .stats-row {
    grid-template-columns: 1fr 1fr;
  }
  
  .logs-table {
    font-size: 0.85rem;
  }
  
  .logs-table th,
  .logs-table td {
    padding: 8px;
  }
}
</style>