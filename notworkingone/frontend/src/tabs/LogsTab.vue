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

        <!-- Quick Presets -->
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

        <!-- Custom Date Range -->
        <template v-if="dateRangeType === 'custom'">
          <input 
            type="date" 
            v-model="startDate" 
            @change="loadLogs"
            :max="endDate"
            class="date-input"
            title="Start Date"
          />
          <input 
            type="date" 
            v-model="endDate" 
            @change="loadLogs"
            :min="startDate"
            :max="today"
            class="date-input"
            title="End Date"
          />
        </template>
        
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
        <div class="stat-value">{{ logs.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Cameras Monitored</div>
        <div class="stat-value">{{ uniqueCameras }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Weapon Types</div>
        <div class="stat-value">{{ uniqueWeapons }}</div>
      </div>
    </div>

    <div class="logs-table-container">
      <table class="logs-table">
        <thead>
          <tr>
            <th @click="sortBy('detection_time')" class="sortable">
              Date & Time 
              <span v-if="sortColumn === 'detection_time'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th @click="sortBy('camera_name')" class="sortable">
              Camera
              <span v-if="sortColumn === 'camera_name'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th>Location</th>
            <th @click="sortBy('weapon_type')" class="sortable">
              Weapon Type
              <span v-if="sortColumn === 'weapon_type'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th @click="sortBy('confidence_score')" class="sortable">
              Confidence
              <span v-if="sortColumn === 'confidence_score'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th>Detected By</th>
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
    
    <div class="logs-footer">
      <span class="total-count">
        Showing {{ sortedLogs.length }} of {{ logs.length }} records
      </span>
      <span class="date-info">{{ dateRangeDisplay }}</span>
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

// Date range
const today = new Date().toISOString().split('T')[0]
const startDate = ref(getDateDaysAgo(7))
const endDate = ref(today)

// Sorting
const sortColumn = ref('detection_time')
const sortDirection = ref('desc')

function getDateDaysAgo(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date.toISOString().split('T')[0]
}

const dateRangeDisplay = computed(() => {
  if (dateRangeType.value === 'preset') {
    if (filterDays.value === 1) return 'Today'
    if (filterDays.value === 7) return 'Last 7 days'
    if (filterDays.value === 30) return 'Last 30 days'
    return `Last ${filterDays.value} days`
  } else {
    return `${formatDate(startDate.value)} - ${formatDate(endDate.value)}`
  }
})

const uniqueCameras = computed(() => {
  const cameras = new Set(logs.value.map(log => log.camera_id))
  return cameras.size
})

const uniqueWeapons = computed(() => {
  const weapons = new Set(logs.value.map(log => log.weapon_type))
  return weapons.size
})

const sortedLogs = computed(() => {
  const sorted = [...logs.value].sort((a, b) => {
    let aVal = a[sortColumn.value]
    let bVal = b[sortColumn.value]
    
    if (sortColumn.value === 'detection_time') {
      aVal = new Date(aVal).getTime()
      bVal = new Date(bVal).getTime()
    }
    
    if (sortDirection.value === 'asc') {
      return aVal > bVal ? 1 : -1
    } else {
      return aVal < bVal ? 1 : -1
    }
  })
  return sorted
})

onMounted(async () => {
  await loadCameras()
  await loadLogs()
})

function handleDateRangeChange() {
  if (dateRangeType.value === 'preset') {
    filterDays.value = 7
  } else {
    startDate.value = getDateDaysAgo(7)
    endDate.value = today
  }
  loadLogs()
}

function sortBy(column) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = 'desc'
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

async function loadLogs() {
  isLoading.value = true
  
  try {
    let url = '/api/detection-logs?limit=1000'
    
    if (dateRangeType.value === 'preset') {
      url += `&days=${filterDays.value}`
    } else {
      // Calculate days between dates
      const start = new Date(startDate.value)
      const end = new Date(endDate.value)
      const diffDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1
      url += `&days=${diffDays}`
    }
    
    if (filterCamera.value) url += `&camera_id=${filterCamera.value}`
    if (filterWeapon.value) url += `&weapon_type=${filterWeapon.value}`
    
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      
      // Filter by custom date range if needed
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
  if (logs.value.length === 0) {
    alert('No data to export')
    return
  }
  
  let csv = 'Date,Time,Camera,Location,Weapon Type,Confidence,Detected By\n'
  
  logs.value.forEach(log => {
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
  a.download = `detection-logs-${new Date().toISOString().split('T')[0]}.csv`
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

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString()
  } catch {
    return dateString
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
.date-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  font-size: 0.95rem;
  cursor: pointer;
}

.date-input {
  min-width: 140px;
}

.filter-select:focus,
.date-input:focus {
  outline: none;
  border-color: #4a90e2;
}

.refresh-btn,
.export-btn {
  padding: 8px 16px;
  background: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: background-color 0.3s ease;
}

.export-btn {
  background: #27ae60;
}

.refresh-btn:hover {
  background: #357ab7;
}

.export-btn:hover {
  background: #219a52;
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
}

.logs-table th.sortable:hover {
  background: #e9ecef;
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

.logs-footer {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.total-count,
.date-info {
  color: #7f8c8d;
  font-size: 0.9rem;
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
  .refresh-btn,
  .export-btn {
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
  
  .logs-footer {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
}
</style>