<!-- src/tabs/IncidentsTab.vue - UPDATED with time filter support -->
<template>
  <div class="incidents-tab">
    <IncidentFilters
      :cameras="cameras"
      :officers="officers"
      :filters="filters"
      :view-mode="viewMode"
      :show-officer-filter="userData.role === 'admin'"
      @update:filters="handleFiltersUpdate"
      @update:view-mode="viewMode = $event"
      @refresh="loadIncidents"
    />

    <IncidentStats :stats="stats" />

    <div class="incidents-list">
      <div v-if="isLoading" class="loading">Loading incidents...</div>
      <div v-else-if="sortedIncidents.length === 0" class="no-incidents">
        No incidents found for selected filters
      </div>

      <IncidentTable
        v-else-if="viewMode === 'vertical'"
        :incidents="sortedIncidents"
        :sort-column="sortColumn"
        :sort-direction="sortDirection"
        @select="selectIncident"
        @sort="sortBy"
      />

      <IncidentCards
        v-else
        :incidents="sortedIncidents"
        @select="selectIncident"
      />
    </div>

    <IncidentModal
      v-if="selectedIncident"
      :incident="selectedIncident"
      :officers="officers"
      :is-admin="userData.role === 'admin'"
      @close="closeModal"
      @update-status="updateStatus"
      @view-image="openImageFullscreen"
    />

    <ImageModal
      v-if="fullscreenImage"
      :image-url="fullscreenImage"
      @close="closeFullscreen"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import IncidentFilters from './incidents/IncidentFilters.vue'
import IncidentStats from './incidents/IncidentStats.vue'
import IncidentTable from './incidents/IncidentTable.vue'
import IncidentCards from './incidents/IncidentCards.vue'
import IncidentModal from './incidents/IncidentModal.vue'
import ImageModal from './incidents/ImageModal.vue'

const props = defineProps({
  token: String,
  userData: Object
})

const cameras = ref([])
const incidents = ref([])
const officers = ref([])
const selectedIncident = ref(null)
const isLoading = ref(false)
const viewMode = ref('horizontal')
const fullscreenImage = ref(null)

const filters = ref({
  camera: null,
  weapon: null,
  status: '',
  officer: '',
  dateRangeType: 'preset',
  days: 7,
  startDate: getDateDaysAgo(7),
  endDate: new Date().toISOString().split('T')[0],
  startTime: '',  // NEW: Time filter
  endTime: ''     // NEW: Time filter
})

const sortColumn = ref('detected_at')
const sortDirection = ref('desc')

function getDateDaysAgo(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date.toISOString().split('T')[0]
}

const filteredIncidents = computed(() => {
  let filtered = [...incidents.value]
  
  if (filters.value.camera) {
    filtered = filtered.filter(incident => incident.camera_id === filters.value.camera)
  }
  
  if (filters.value.weapon) {
    filtered = filtered.filter(incident => incident.weapon_type === filters.value.weapon)
  }
  
  if (filters.value.dateRangeType === 'custom') {
    const start = new Date(filters.value.startDate)
    start.setHours(0, 0, 0, 0)
    const end = new Date(filters.value.endDate)
    end.setHours(23, 59, 59, 999)
    
    filtered = filtered.filter(incident => {
      const incidentDate = new Date(incident.detected_at)
      return incidentDate >= start && incidentDate <= end
    })
  } else {
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - filters.value.days)
    cutoffDate.setHours(0, 0, 0, 0)
    
    filtered = filtered.filter(incident => {
      const incidentDate = new Date(incident.detected_at)
      return incidentDate >= cutoffDate
    })
  }
  
  // NEW: Filter by time of day
  if (filters.value.startTime || filters.value.endTime) {
    filtered = filtered.filter(incident => {
      try {
        const incidentTime = new Date(incident.detected_at).toTimeString().slice(0, 5) // HH:MM format
        
        if (filters.value.startTime && filters.value.endTime) {
          if (filters.value.startTime <= filters.value.endTime) {
            // Normal range (e.g., 09:00 to 17:00)
            return incidentTime >= filters.value.startTime && incidentTime <= filters.value.endTime
          } else {
            // Overnight range (e.g., 22:00 to 06:00)
            return incidentTime >= filters.value.startTime || incidentTime <= filters.value.endTime
          }
        } else if (filters.value.startTime) {
          return incidentTime >= filters.value.startTime
        } else if (filters.value.endTime) {
          return incidentTime <= filters.value.endTime
        }
      } catch (error) {
        console.error('Error filtering incident by time:', error)
        return true
      }
      return true
    })
  }
  
  return filtered
})

const sortedIncidents = computed(() => {
  return [...filteredIncidents.value].sort((a, b) => {
    let aVal = a[sortColumn.value]
    let bVal = b[sortColumn.value]
    
    if (sortColumn.value === 'detected_at') {
      aVal = new Date(aVal).getTime()
      bVal = new Date(bVal).getTime()
    }
    
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      aVal = aVal.toLowerCase()
      bVal = bVal.toLowerCase()
    }
    
    if (aVal === null || aVal === undefined) aVal = ''
    if (bVal === null || bVal === undefined) bVal = ''
    
    if (sortDirection.value === 'asc') {
      return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
    } else {
      return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
    }
  })
})

const stats = computed(() => {
  return {
    pending: filteredIncidents.value.filter(i => i.status === 'pending').length,
    responding: filteredIncidents.value.filter(i => i.status === 'responding').length,
    resolved: filteredIncidents.value.filter(i => i.status === 'resolved').length,
    total: filteredIncidents.value.length
  }
})

onMounted(async () => {
  await loadCameras()
  await loadOfficers()
  await loadIncidents()
  setInterval(loadIncidents, 30000)
})

function handleFiltersUpdate(newFilters) {
  filters.value = { ...newFilters }
  loadIncidents()
}

function sortBy(column) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = column === 'detected_at' ? 'desc' : 'asc'
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

async function loadOfficers() {
  if (props.userData.role !== 'admin') return
  
  try {
    const res = await fetch('/api/officers', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      officers.value = data.officers
    }
  } catch (error) {
    console.error('Could not load officers:', error)
  }
}

async function loadIncidents() {
  isLoading.value = true
  
  try {
    let url = '/api/incidents?limit=1000'
    if (filters.value.status) url += `&status=${filters.value.status}`
    if (filters.value.officer) url += `&assigned_to=${filters.value.officer}`
    
    // NEW: Add time filter parameters
    if (filters.value.startTime) url += `&start_time=${filters.value.startTime}`
    if (filters.value.endTime) url += `&end_time=${filters.value.endTime}`
    
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      incidents.value = data.incidents
    }
  } catch (error) {
    console.error('Could not load incidents:', error)
  }
  
  isLoading.value = false
}

function selectIncident(incident) {
  selectedIncident.value = incident
}

function closeModal() {
  selectedIncident.value = null
}

function openImageFullscreen(imageUrl) {
  fullscreenImage.value = imageUrl
}

function closeFullscreen() {
  fullscreenImage.value = null
}

async function updateStatus(newStatus, actionData) {
  if (!selectedIncident.value) return
  
  const updates = { status: newStatus }
  
  if (newStatus === 'responding') {
    if (actionData.assigned_to) {
      updates.assigned_to = actionData.assigned_to
    }
    if (actionData.response_notes) {
      updates.response_notes = actionData.response_notes
    }
  } else if (newStatus === 'resolved') {
    if (!actionData.resolution_notes) {
      alert('Please enter resolution notes')
      return
    }
    updates.resolution_notes = actionData.resolution_notes
  }
  
  try {
    const res = await fetch(`/api/incidents/${selectedIncident.value.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(updates)
    })
    
    if (res.ok) {
      await loadIncidents()
      closeModal()
    } else {
      alert('Failed to update incident')
    }
  } catch (error) {
    console.error('Could not update incident:', error)
    alert('Network error. Please try again.')
  }
}
</script>

<style scoped>
.incidents-tab {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.incidents-list {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 400px;
}

.loading,
.no-incidents {
  text-align: center;
  padding: 60px 20px;
  color: #7f8c8d;
  font-style: italic;
}
</style>