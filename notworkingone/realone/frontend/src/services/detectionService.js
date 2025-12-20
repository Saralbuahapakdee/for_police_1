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
    }, 2000)
    
    console.log('🔍 Detection service started - polling every 2 seconds')
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
          console.log('🚨 NEW DETECTION:', data)
          
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
          
          // Log EACH weapon type separately to backend
          await this.logAllDetectionsToBackend(data)
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

  // NEW: Log each weapon type separately
  async logAllDetectionsToBackend(detection) {
    if (!this.token) {
      console.log('⚠️ No token available for logging detection')
      return
    }
    
    try {
      // Process each weapon type separately
      for (const [weaponType, data] of Object.entries(detection.objects)) {
        const count = data.count || 0
        const confidences = data.confidences || []
        
        if (count > 0 && confidences.length > 0) {
          const avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length
          
          const normalizedType = this.normalizeWeaponType(weaponType)
          
          console.log(`📝 Logging detection: ${normalizedType} (${(avgConfidence * 100).toFixed(1)}% confidence)`)
          
          // Log to backend - this will auto-create incident if confidence >= 0.80
          const response = await fetch('/api/log-detection', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({
              camera_id: 1,
              weapon_type: normalizedType,
              confidence_score: avgConfidence
            })
          })
          
          if (response.ok) {
            const result = await response.json()
            console.log(`✅ Logged ${normalizedType} detection:`, result.message)
            
            if (result.incident_id) {
              console.log(`🚨 Incident #${result.incident_id} created for ${normalizedType}`)
            }
          } else {
            const error = await response.json()
            console.error(`❌ Failed to log ${normalizedType} detection:`, error)
          }
          
          // Small delay between requests to avoid overwhelming backend
          await new Promise(resolve => setTimeout(resolve, 100))
        }
      }
    } catch (error) {
      console.error('Error logging detections to backend:', error)
    }
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
      this.playBeep(audioContext, 880, 0.2, 0.3)
      this.playBeep(audioContext, 880, 0.4, 0.6)
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
      isConnected: this.isConnected
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
      isConnected: this.isConnected
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
      isConnected: this.isConnected
    }
  }
}

const detectionService = new DetectionService()

export default detectionService