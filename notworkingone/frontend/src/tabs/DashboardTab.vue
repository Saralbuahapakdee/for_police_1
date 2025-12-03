<template>
  <div class="dashboard-tab">
    <div class="dashboard-header">
      <h3>📊 Detection Analytics</h3>
      <div class="dashboard-filters">
        <select v-model="filterCamera" @change="loadDashboard" class="filter-select">
          <option :value="null">All Cameras</option>
          <option v-for="camera in cameras" :key="camera.id" :value="camera.id">
            {{ camera.camera_name }}
          </option>
        </select>
        
        <select v-model="dateRangeType" @change="handleDateRangeChange" class="filter-select">
          <option value="preset">Quick Select</option>
          <option value="custom">Custom Range</option>
        </select>

        <!-- Quick Presets -->
        <select v-if="dateRangeType === 'preset'" v-model="filterDays" @change="loadDashboard" class="date-select">
          <option :value="1">Today</option>
          <option :value="7">7 days</option>
          <option :value="14">2 weeks</option>
          <option :value="30">30 days</option>
          <option :value="60">2 months</option>
          <option :value="90">3 months</option>
          <option :value="180">6 months</option>
          <option :value="365">1 year</option>
        </select>

        <!-- Custom Date Range -->
        <template v-if="dateRangeType === 'custom'">
          <input 
            type="date" 
            v-model="startDate" 
            @change="loadDashboard"
            :max="endDate"
            class="date-input"
            title="Start Date"
          />
          <input 
            type="date" 
            v-model="endDate" 
            @change="loadDashboard"
            :min="startDate"
            :max="today"
            class="date-input"
            title="End Date"
          />
        </template>

        <button @click="loadDashboard" class="refresh-btn">🔄</button>
      </div>
    </div>

    <div v-if="isLoading" class="loading-state">
      Loading analytics...
    </div>

    <div v-else class="dashboard-content">
      <!-- Date Range Display -->
      <div class="date-range-display">
        <strong>📅 Period:</strong> {{ dateRangeDisplay }}
      </div>

      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="summary-card">
          <h4>Total Detections</h4>
          <div class="card-value">{{ totalDetections }}</div>
          <div class="card-subtitle">{{ cameraInfo }}</div>
        </div>
        <div class="summary-card">
          <h4>Most Detected</h4>
          <div class="card-value">{{ mostDetectedWeapon }}</div>
          <div class="card-subtitle">{{ mostDetectedCount }} detections</div>
        </div>
        <div class="summary-card">
          <h4>Avg Confidence</h4>
          <div class="card-value">{{ avgConfidence }}%</div>
          <div class="card-subtitle" :class="getConfidenceClass(avgConfidence / 100)">
            {{ getConfidenceLabel(avgConfidence / 100) }}
          </div>
        </div>
        <div class="summary-card">
          <h4>Daily Average</h4>
          <div class="card-value">{{ dailyAverage }}</div>
          <div class="card-subtitle">detections per day</div>
        </div>
      </div>

      <!-- Charts -->
      <div class="charts-section">
        <div class="chart-container">
          <h4>Detection by Weapon Type</h4>
          <div v-if="weaponTotals.length === 0" class="no-data-chart">
            No data available for this period
          </div>
          <div v-else class="weapon-chart">
            <div v-for="weapon in weaponTotals" :key="weapon.weapon_type" class="weapon-bar">
              <div class="weapon-info">
                <div class="weapon-label">{{ formatWeaponName(weapon.weapon_type) }}</div>
                <div class="weapon-confidence">Avg: {{ Math.round(weapon.avg_conf * 100) }}%</div>
              </div>
              <div class="bar-container">
                <div class="bar" :style="{ width: (weapon.total / maxDetections) * 100 + '%' }"></div>
                <span class="bar-value">{{ weapon.total }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="chart-container">
          <h4>Daily Timeline</h4>
          <div v-if="dailyTimeline.length === 0" class="no-data-chart">
            No data available for this period
          </div>
          <div v-else class="timeline-chart">
            <div v-for="day in dailyTimeline" :key="day.date" class="timeline-day">
              <div class="day-label">{{ formatDate(day.date) }}</div>
              <div class="day-detections">
                <div v-for="(weapon, index) in day.weapons" :key="index" 
                     class="weapon-dot" :class="weapon.type"
                     :title="`${formatWeaponName(weapon.type)}: ${weapon.count}`"></div>
                <span class="day-total">{{ day.total }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Detailed Table -->
      <div class="details-section">
        <h4>📋 Daily Breakdown</h4>
        <div class="details-table-container">
          <table class="details-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Camera</th>
                <th>Weapon Type</th>
                <th>Detections</th>
                <th>Avg Confidence</th>
                <th>First Detection</th>
                <th>Last Detection</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="dailySummary.length === 0">
                <td colspan="7" class="no-data">No data available</td>
              </tr>
              <tr v-else v-for="(item, index) in dailySummary" :key="index">
                <td>{{ formatDate(item.detection_date) }}</td>
                <td>{{ item.camera_name }}</td>
                <td>
                  <span :class="['weapon-badge', item.weapon_type]">
                    {{ formatWeaponName(item.weapon_type) }}
                  </span>
                </td>
                <td><strong>{{ item.total_detections }}</strong></td>
                <td>
                  <span class="confidence-badge" :class="getConfidenceClass(item.avg_confidence)">
                    {{ Math.round(item.avg_confidence * 100) }}%
                  </span>
                </td>
                <td>{{ formatTime(item.first_detection) }}</td>
                <td>{{ formatTime(item.last_detection) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  token: String
})

const cameras = ref([])
const dashboardData = ref(null)
const filterCamera = ref(null)
const dateRangeType = ref('preset')
const filterDays = ref(7)
const isLoading = ref(false)

// Date range
const today = new Date().toISOString().split('T')[0]
const startDate = ref(getDateDaysAgo(7))
const endDate = ref(today)

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

const cameraInfo = computed(() => {
  if (filterCamera.value) {
    const cam = cameras.value.find(c => c.id === filterCamera.value)
    return cam ? cam.camera_name : 'Selected camera'
  }
  return 'All cameras'
})

const totalDetections = computed(() => {
  if (!dashboardData.value) return 0
  return dashboardData.value.weapon_totals.reduce((sum, weapon) => sum + weapon.total, 0)
})

const dailyAverage = computed(() => {
  if (!dashboardData.value || totalDetections.value === 0) return 0
  const days = dateRangeType.value === 'preset' ? filterDays.value : 
    Math.ceil((new Date(endDate.value) - new Date(startDate.value)) / (1000 * 60 * 60 * 24)) + 1
  return Math.round(totalDetections.value / days)
})

const mostDetectedWeapon = computed(() => {
  if (!dashboardData.value || dashboardData.value.weapon_totals.length === 0) return 'None'
  const top = dashboardData.value.weapon_totals[0]
  return formatWeaponName(top.weapon_type)
})

const mostDetectedCount = computed(() => {
  if (!dashboardData.value || dashboardData.value.weapon_totals.length === 0) return 0
  return dashboardData.value.weapon_totals[0].total
})

const avgConfidence = computed(() => {
  if (!dashboardData.value || dashboardData.value.weapon_totals.length === 0) return 0
  const avg = dashboardData.value.weapon_totals.reduce((sum, w) => 
    sum + (w.avg_conf || 0), 0) / dashboardData.value.weapon_totals.length
  return Math.round(avg * 100)
})

const weaponTotals = computed(() => {
  return dashboardData.value ? dashboardData.value.weapon_totals : []
})

const maxDetections = computed(() => {
  if (!weaponTotals.value.length) return 1
  return Math.max(...weaponTotals.value.map(w => w.total))
})

const dailySummary = computed(() => {
  return dashboardData.value ? dashboardData.value.daily_summary : []
})

const dailyTimeline = computed(() => {
  if (!dashboardData.value) return []
  
  const timeline = {}
  dashboardData.value.daily_summary.forEach(item => {
    if (!timeline[item.detection_date]) {
      timeline[item.detection_date] = {
        date: item.detection_date,
        weapons: [],
        total: 0
      }
    }
    timeline[item.detection_date].weapons.push({
      type: item.weapon_type,
      count: item.total_detections
    })
    timeline[item.detection_date].total += item.total_detections
  })
  
  return Object.values(timeline).sort((a, b) => new Date(b.date) - new Date(a.date))
})

onMounted(async () => {
  await loadCameras()
  await loadDashboard()
  
  // Auto-refresh every 30 seconds
  setInterval(loadDashboard, 30000)
})

function handleDateRangeChange() {
  if (dateRangeType.value === 'preset') {
    filterDays.value = 7
  } else {
    startDate.value = getDateDaysAgo(7)
    endDate.value = today
  }
  loadDashboard()
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

async function loadDashboard() {
  isLoading.value = true
  
  try {
    let days = filterDays.value
    
    if (dateRangeType.value === 'custom') {
      const start = new Date(startDate.value)
      const end = new Date(endDate.value)
      days = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1
    }
    
    let url = `/api/dashboard-data?days=${days}`
    if (filterCamera.value) url += `&camera_id=${filterCamera.value}`
    
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
        
        data.daily_summary = data.daily_summary.filter(item => {
          const itemDate = new Date(item.detection_date)
          return itemDate >= start && itemDate <= end
        })
      }
      
      dashboardData.value = data
    }
  } catch (error) {
    console.error('Could not load dashboard:', error)
  }
  
  isLoading.value = false
}

function formatWeaponName(weaponType) {
  const names = {
    'knife': 'Knife',
    'pistol': 'Pistol',
    'heavy_weapon': 'Heavy Weapon'
  }
  return names[weaponType] || weaponType
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString()
  } catch {
    return dateString
  }
}

function formatTime(timeString) {
  if (!timeString) return 'N/A'
  try {
    return new Date(timeString).toLocaleTimeString()
  } catch {
    return 'N/A'
  }
}

function getConfidenceClass(score) {
  if (score >= 0.9) return 'high'
  if (score >= 0.75) return 'medium'
  return 'low'
}

function getConfidenceLabel(score) {
  if (score >= 0.9) return 'Excellent'
  if (score >= 0.75) return 'Good'
  return 'Fair'
}
</script>

<style scoped>
.dashboard-tab {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  flex-wrap: wrap;
  gap: 15px;
}

.dashboard-header h3 {
  color: #2c3e50;
}

.dashboard-filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-select,
.date-select,
.date-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
}

.date-input {
  min-width: 140px;
}

.refresh-btn {
  padding: 8px 16px;
  background: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.refresh-btn:hover {
  background: #357ab7;
}

.loading-state {
  background: white;
  padding: 60px;
  border-radius: 12px;
  text-align: center;
  color: #7f8c8d;
  font-style: italic;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.date-range-display {
  background: #e8f4fd;
  padding: 15px 20px;
  border-radius: 8px;
  color: #2c3e50;
  font-size: 1.1rem;
  border-left: 4px solid #4a90e2;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.summary-card {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.summary-card h4 {
  color: #7f8c8d;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 10px;
}

.card-value {
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 8px;
}

.card-subtitle {
  font-size: 0.9rem;
  color: #7f8c8d;
}

.card-subtitle.high { color: #27ae60; }
.card-subtitle.medium { color: #f39c12; }
.card-subtitle.low { color: #e74c3c; }

.charts-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 25px;
}

.chart-container {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chart-container h4 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.no-data-chart {
  text-align: center;
  padding: 40px;
  color: #7f8c8d;
  font-style: italic;
}

.weapon-chart {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.weapon-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.weapon-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.weapon-label {
  font-weight: 600;
  color: #2c3e50;
}

.weapon-confidence {
  font-size: 0.85rem;
  color: #7f8c8d;
}

.bar-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar {
  height: 24px;
  background: linear-gradient(90deg, #4a90e2, #357ab7);
  border-radius: 12px;
  min-width: 4px;
  transition: width 0.3s ease;
}

.bar-value {
  font-weight: 600;
  color: #2c3e50;
  min-width: 40px;
}

.timeline-chart {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 400px;
  overflow-y: auto;
}

.timeline-day {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px 0;
  border-bottom: 1px solid #ecf0f1;
}

.day-label {
  min-width: 100px;
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.9rem;
}

.day-detections {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.weapon-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  transition: transform 0.2s ease;
}

.weapon-dot:hover {
  transform: scale(1.5);
  cursor: help;
}

.weapon-dot.knife { background: #e74c3c; }
.weapon-dot.pistol { background: #f39c12; }
.weapon-dot.heavy_weapon { background: #8e44ad; }

.day-total {
  font-weight: 600;
  color: #2c3e50;
  margin-left: auto;
  min-width: 40px;
  text-align: right;
}

.details-section {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.details-section h4 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.details-table-container {
  overflow-x: auto;
  max-height: 500px;
  overflow-y: auto;
}

.details-table {
  width: 100%;
  border-collapse: collapse;
}

.details-table th {
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

.details-table td {
  padding: 12px;
  border-bottom: 1px solid #e9ecef;
  color: #2c3e50;
}

.details-table tr:hover {
  background: #f8f9fa;
}

.no-data {
  text-align: center;
  padding: 40px !important;
  color: #7f8c8d;
  font-style: italic;
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

@media (max-width: 1024px) {
  .charts-section {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .dashboard-filters {
    flex-direction: column;
    width: 100%;
  }
  
  .filter-select,
  .date-select,
  .date-input,
  .refresh-btn {
    width: 100%;
  }
  
  .summary-cards {
    grid-template-columns: 1fr 1fr;
  }
}
</style>