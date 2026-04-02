




class DetectionService {
  constructor() {
    this.listeners = []
    this.currentDetection = {
      detected: false,
      objects: {},
      timestamp: null
    }
    this.detectionHistory = []
    this.isPolling = false
    this.pollInterval = null
    this.lastCheckTime = 'Never'
    this.isConnected = false
    this.token = null
    this.lastTimestamp = null
    this.lastIncidentId = null

    this.currentAlert = null
  }

  reset() {
    this.stopPolling()
    this.listeners = []
    this.currentDetection = {
      detected: false,
      objects: {},
      timestamp: null
    }
    this.detectionHistory = []
    this.lastCheckTime = 'Never'
    this.isConnected = false
    this.token = null
    this.lastTimestamp = null
    this.lastIncidentId = null
    this.currentAlert = null
    console.log('🔄 Detection service reset')
  }

  startPolling(token) {
    if (this.isPolling) {
      console.log('⚠️ Detection service already polling')
      return
    }

    this.isPolling = true
    this.token = token


    this.checkDetection()


    this.pollInterval = setInterval(() => {
      this.checkDetection()
    }, 1000)

    console.log('🔍 Detection service started - polling every 1000ms')
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval)
      this.pollInterval = null
    }
    this.isPolling = false
    console.log('🛑 Detection service stopped')
  }

  async checkDetection() {
    try {
      const response = await fetch('/api/detection-status', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        this.isConnected = true
        this.lastCheckTime = new Date().toLocaleTimeString()

        const hasObjects = data.objects && Object.keys(data.objects).length > 0
        const isNewDetection = data.detected && hasObjects &&
          data.timestamp &&
          data.timestamp !== this.lastTimestamp

        if (isNewDetection) {
          console.log('🚨 NEW DETECTION - UPDATING IMMEDIATELY:', data)

          this.lastTimestamp = data.timestamp

          this.detectionHistory.unshift({
            detected: data.detected,
            objects: data.objects,
            timestamp: data.timestamp
          })

          if (this.detectionHistory.length > 50) {
            this.detectionHistory = this.detectionHistory.slice(0, 50)
          }

          this.playAlertSound()
          this.showNotification(data)

          if (data.latest_incident_id && data.latest_incident_id !== this.lastIncidentId) {
            this.lastIncidentId = data.latest_incident_id;
            console.log(`🚨 NEW INCIDENT ALERT #${data.latest_incident_id} detected from backend`)
            await this.fetchAndSetIncidentAlert(data.latest_incident_id)
          }
        }


        this.currentDetection = data
        this.notifyListeners()
      } else {
        this.isConnected = false
        this.notifyListeners()
      }
    } catch (error) {
      console.error('Error checking detection:', error)
      this.isConnected = false
      this.notifyListeners()
    }
  }



  async fetchAndSetIncidentAlert(incidentId) {
    try {
      const response = await fetch(`/api/incidents/${incidentId}`, {
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      })

      if (response.ok) {
        const data = await response.json()

        this.currentAlert = {
          id: incidentId,
          incident: data.incident,
          timestamp: Date.now()
        }

        console.log('🔔 Alert REPLACED with new incident:', this.currentAlert)
        this.notifyListeners()
      }
    } catch (error) {
      console.error('Error fetching incident details:', error)
    }
  }

  dismissAlert() {
    console.log('❌ Alert dismissed')
    this.currentAlert = null
    this.notifyListeners()
  }

  normalizeWeaponType(weaponType) {
    const mapping = {
      'gun': 'pistol',
      'heavy-weapon': 'heavy_weapon',
      'knife': 'knife',
      'pistol': 'pistol',
      'heavy_weapon': 'heavy_weapon'
    }
    return mapping[weaponType.toLowerCase()] || weaponType.toLowerCase()
  }

  playAlertSound() {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()

      this.playBeep(audioContext, 880, 0.2, 0)
    } catch (error) {
      console.error('Could not play alert sound:', error)
    }
  }

  playBeep(audioContext, frequency, duration, delay) {
    setTimeout(() => {
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
    }, delay * 1000)
  }

  async showNotification(detection) {
    if ('Notification' in window && Notification.permission === 'granted') {
      const weaponList = Object.keys(detection.objects)
        .map(w => this.formatWeaponName(w))
        .join(', ')

      new Notification('🚨 Weapon Detected!', {
        body: `${weaponList} detected at ${new Date().toLocaleTimeString()}`,
        icon: '/favicon.ico',
        tag: 'weapon-detection',
        requireInteraction: true
      })
    } else if ('Notification' in window && Notification.permission === 'default') {
      await Notification.requestPermission()
    }
  }

  formatWeaponName(weaponType) {
    const names = {
      'gun': 'Pistol',
      'heavy-weapon': 'Heavy Weapon',
      'heavy_weapon': 'Heavy Weapon',
      'knife': 'Knife',
      'pistol': 'Pistol'
    }
    return names[weaponType] || weaponType.replace('-', ' ').replace('_', ' ')
  }

  subscribe(callback) {
    this.listeners.push(callback)

    callback({
      currentDetection: this.currentDetection,
      detectionHistory: this.detectionHistory,
      lastCheckTime: this.lastCheckTime,
      isConnected: this.isConnected,
      currentAlert: this.currentAlert
    })

    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback)
    }
  }

  notifyListeners() {
    const state = {
      currentDetection: this.currentDetection,
      detectionHistory: this.detectionHistory,
      lastCheckTime: this.lastCheckTime,
      isConnected: this.isConnected,
      currentAlert: this.currentAlert
    }

    this.listeners.forEach(callback => {
      try {
        callback(state)
      } catch (error) {
        console.error('Error in detection listener:', error)
      }
    })
  }

  getState() {
    return {
      currentDetection: this.currentDetection,
      detectionHistory: this.detectionHistory,
      lastCheckTime: this.lastCheckTime,
      isConnected: this.isConnected,
      currentAlert: this.currentAlert
    }
  }
}

const detectionService = new DetectionService()

export default detectionService
