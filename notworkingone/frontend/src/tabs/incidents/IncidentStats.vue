<!-- src/tabs/incidents/IncidentStats.vue -->
<template>
  <div class="stats-row">
    <div class="stat-card pending">
      <div class="stat-icon">🔴</div>
      <div class="stat-info">
        <div class="stat-value">{{ stats.pending }}</div>
        <div class="stat-label">Pending</div>
      </div>
    </div>
    <div class="stat-card responding">
      <div class="stat-icon">🟡</div>
      <div class="stat-info">
        <div class="stat-value">{{ stats.responding }}</div>
        <div class="stat-label">Responding</div>
      </div>
    </div>
    <div class="stat-card resolved">
      <div class="stat-icon">🟢</div>
      <div class="stat-info">
        <div class="stat-value">{{ stats.resolved }}</div>
        <div class="stat-label">Resolved</div>
      </div>
    </div>
    <div class="stat-card total">
      <div class="stat-icon">📊</div>
      <div class="stat-info">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">Total Incidents</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  stats: {
    type: Object,
    required: true,
    default: () => ({
      pending: 0,
      responding: 0,
      resolved: 0,
      total: 0
    })
  }
})
</script>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 15px;
  border-left: 4px solid #ddd;
}

.stat-card.pending { border-left-color: #e74c3c; }
.stat-card.responding { border-left-color: #f39c12; }
.stat-card.resolved { border-left-color: #27ae60; }
.stat-card.total { border-left-color: #3498db; }

.stat-icon {
  font-size: 2.5rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
}

.stat-label {
  font-size: 0.9rem;
  color: #7f8c8d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>