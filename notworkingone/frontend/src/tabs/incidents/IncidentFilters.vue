<!-- src/tabs/incidents/IncidentFilters.vue - UPDATED with labeled time filter -->
<template>
  <div class="incidents-header">
    <h2>🚨 Incident Management</h2>
    <div class="header-actions">
      <select v-model="localFilters.camera" @change="emitChange" class="filter-select">
        <option :value="null">All Cameras</option>
        <option v-for="camera in cameras" :key="camera.id" :value="camera.id">
          {{ camera.camera_name }}
        </option>
      </select>

      <select v-model="localFilters.weapon" @change="emitChange" class="filter-select">
        <option :value="null">All Weapons</option>
        <option value="knife">Knife</option>
        <option value="pistol">Pistol</option>
        <option value="heavy_weapon">Heavy Weapon</option>
      </select>

      <select v-model="localFilters.status" @change="emitChange" class="filter-select">
        <option value="">All Status</option>
        <option value="pending">🔴 Pending</option>
        <option value="responding">🟡 Responding</option>
        <option value="resolved">🟢 Resolved</option>
      </select>
      
      <select v-if="showOfficerFilter" v-model="localFilters.officer" @change="emitChange" class="filter-select">
        <option value="">All Officers</option>
        <option v-for="officer in officers" :key="officer.id" :value="officer.id">
          {{ officer.first_name }} {{ officer.last_name }} ({{ officer.badge_number }})
        </option>
      </select>
      
      <select v-model="localFilters.dateRangeType" @change="handleDateRangeChange" class="filter-select">
        <option value="preset">Quick Select</option>
        <option value="custom">Custom Range</option>
      </select>

      <select v-if="localFilters.dateRangeType === 'preset'" v-model="localFilters.days" @change="emitChange" class="filter-select">
        <option :value="1">Today</option>
        <option :value="7">Last 7 days</option>
        <option :value="14">Last 2 weeks</option>
        <option :value="30">Last 30 days</option>
        <option :value="60">Last 2 months</option>
        <option :value="90">Last 3 months</option>
        <option :value="180">Last 6 months</option>
        <option :value="365">Last year</option>
      </select>

      <template v-if="localFilters.dateRangeType === 'custom'">
        <input 
          type="date" 
          v-model="localFilters.startDate" 
          @change="emitChange"
          :max="localFilters.endDate"
          class="date-input"
        />
        <input 
          type="date" 
          v-model="localFilters.endDate" 
          @change="emitChange"
          :min="localFilters.startDate"
          :max="today"
          class="date-input"
        />
      </template>
      
      <!-- Time filter with labels -->
      <div class="time-filter-group">
        <span class="time-filter-label">From</span>
        <input 
          type="time" 
          v-model="localFilters.startTime" 
          @change="emitChange"
          class="time-input"
          title="Filter from this time"
        />
      </div>
      <div class="time-filter-group">
        <span class="time-filter-label">To</span>
        <input 
          type="time" 
          v-model="localFilters.endTime" 
          @change="emitChange"
          class="time-input"
          title="Filter until this time"
        />
      </div>
      
      <button v-if="localFilters.startTime || localFilters.endTime" 
              @click="clearTimeFilter" 
              class="clear-time-btn"
              title="Clear time filter">
        ✕
      </button>
      
      <div class="view-toggle">
        <button 
          @click="toggleView('horizontal')" 
          :class="['toggle-btn', { active: viewMode === 'horizontal' }]"
          title="Card View"
        >
          ⊞ Cards
        </button>
        <button 
          @click="toggleView('vertical')" 
          :class="['toggle-btn', { active: viewMode === 'vertical' }]"
          title="List View"
        >
          ☰ List
        </button>
      </div>

      <button @click="$emit('refresh')" class="refresh-btn">🔄</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  cameras: Array,
  officers: Array,
  filters: Object,
  viewMode: String,
  showOfficerFilter: Boolean
})

const emit = defineEmits(['update:filters', 'update:viewMode', 'refresh'])

const localFilters = ref({ ...props.filters })
const today = new Date().toISOString().split('T')[0]

watch(() => props.filters, (newFilters) => {
  localFilters.value = { ...newFilters }
}, { deep: true })

function emitChange() {
  emit('update:filters', { ...localFilters.value })
}

function handleDateRangeChange() {
  if (localFilters.value.dateRangeType === 'preset') {
    localFilters.value.days = 7
  } else {
    localFilters.value.startDate = getDateDaysAgo(7)
    localFilters.value.endDate = today
  }
  emitChange()
}

function clearTimeFilter() {
  localFilters.value.startTime = ''
  localFilters.value.endTime = ''
  emitChange()
}

function toggleView(mode) {
  emit('update:viewMode', mode)
}

function getDateDaysAgo(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date.toISOString().split('T')[0]
}
</script>

<style scoped>
.incidents-header {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.incidents-header h2 {
  color: #2c3e50;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.view-toggle {
  display: flex;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}

.toggle-btn {
  padding: 8px 16px;
  background: white;
  border: none;
  cursor: pointer;
  font-size: 0.95rem;
  color: #2c3e50;
  transition: all 0.3s ease;
  border-right: 1px solid #e0e0e0;
}

.toggle-btn:last-child {
  border-right: none;
}

.toggle-btn.active {
  background: #4a90e2;
  color: white;
  font-weight: 600;
}

.toggle-btn:hover:not(.active) {
  background: #f8f9fa;
}

.filter-select,
.date-input {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  font-size: 0.95rem;
  cursor: pointer;
  height: 36px;
}

.date-input {
  min-width: 140px;
}

/* Time filter with label */
.time-filter-group {
  display: flex;
  align-items: center;
  gap: 5px;
  background: #f0f4ff;
  border: 1px solid #c5d3f0;
  border-radius: 6px;
  padding: 0 8px;
  height: 36px;
}

.time-filter-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: #4a6fa5;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
  user-select: none;
}

.time-input {
  border: none;
  background: transparent;
  font-size: 0.875rem;
  padding: 0;
  width: 90px;
  outline: none;
  cursor: pointer;
  color: #2c3e50;
}

.time-input:focus {
  outline: none;
}

.clear-time-btn {
  padding: 8px 10px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
  height: 36px;
}

.clear-time-btn:hover {
  background: #c0392b;
}

.refresh-btn {
  padding: 10px 12px;
  background: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
  height: 36px;
}

.refresh-btn:hover {
  background: #357ab7;
}

@media (max-width: 768px) {
  .incidents-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    flex-direction: column;
  }
  
  .filter-select,
  .date-input,
  .time-filter-group,
  .view-toggle,
  .refresh-btn,
  .clear-time-btn {
    width: 100%;
  }

  .time-filter-group {
    justify-content: space-between;
  }

  .time-input {
    flex: 1;
  }
}
</style>
