// OPTIMIZED for INSTANT bounding box updates when MQTT arrives
// Polling interval reduced to 500ms for near real-time response

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
    
    this.lastLoggedDetection = new Map()
    this.LOG_COOLDOWN = 5 * 60 * 1000
    
    this.currentAlert = null
    
    // Image capture canvas
    this.captureCanvas = null
    
    // Stream dimensions
    this.streamWidth = 640
    this.streamHeight = 480
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
    this.lastLoggedDetection.clear()
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
    
    // Check immediately on start
    this.checkDetection()
    
    // Poll every 500ms for instant updates (reduced from 2000ms)
    this.pollInterval = setInterval(() => {
      this.checkDetection()
    }, 40)
    
    console.log('🔍 Detection service started - polling every 500ms for INSTANT updates')
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
          
          // Capture image and log detections
          await this.captureAndLogDetections(data)
        }
        
        // Update current detection state (this triggers bounding box redraw)
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

  async captureAndLogDetections(detection) {
    if (!this.token) {
      console.log('⚠️ No token available for logging detection')
      return
    }
    
    const now = Date.now()
    const cameraId = 1
    
    try {
      // Capture image from video stream
      const imageData = await this.captureImageFromStream()
      
      for (const [weaponType, data] of Object.entries(detection.objects)) {
        const confidences = Array.isArray(data.confidences) ? data.confidences : [data.confidences]
        const count = confidences.length
        
        if (count > 0 && confidences.length > 0) {
          const normalizedType = this.normalizeWeaponType(weaponType)
          const logKey = `${cameraId}:${normalizedType}`
          
          const lastLogged = this.lastLoggedDetection.get(logKey)
          
          if (lastLogged && (now - lastLogged) < this.LOG_COOLDOWN) {
            const remainingTime = Math.ceil((this.LOG_COOLDOWN - (now - lastLogged)) / 1000)
            console.log(`⏳ Skipping ${normalizedType} log - last logged ${Math.round((now - lastLogged) / 1000)}s ago (cooldown: ${remainingTime}s remaining)`)
            continue
          }
          
          const avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length
          
          console.log(`📝 Logging detection with image: ${normalizedType} (${(avgConfidence * 100).toFixed(1)}% confidence)`)
          
          const response = await fetch('/api/log-detection', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({
              camera_id: cameraId,
              weapon_type: normalizedType,
              confidence_score: avgConfidence,
              image: imageData
            })
          })
          
          if (response.ok) {
            const result = await response.json()
            console.log(`✅ ${result.message}`)
            
            if (result.image_path) {
              console.log(`📸 Image saved: ${result.image_path}`)
            }
            
            if (result.is_new_log) {
              this.lastLoggedDetection.set(logKey, now)
              console.log(`🕐 Cooldown started for ${logKey}`)
              
              for (const [key, timestamp] of this.lastLoggedDetection.entries()) {
                if (now - timestamp > this.LOG_COOLDOWN) {
                  this.lastLoggedDetection.delete(key)
                }
              }
            }
            
            if (result.incident_id && result.is_new_incident) {
              console.log(`🚨 NEW INCIDENT #${result.incident_id} created for ${normalizedType}`)
              await this.fetchAndSetIncidentAlert(result.incident_id)
            }
          } else {
            const error = await response.json()
            console.error(`❌ Failed to log ${normalizedType} detection:`, error)
          }
          
          await new Promise(resolve => setTimeout(resolve, 100))
        }
      }
    } catch (error) {
      console.error('Error capturing and logging detections:', error)
    }
  }

  async captureImageFromStream() {
    return new Promise((resolve) => {
      try {
        const videoStream = document.querySelector('.video-stream')
        
        if (!videoStream) {
          console.warn('⚠️ No video stream found for image capture')
          resolve(null)
          return
        }
        
        if (!this.captureCanvas) {
          this.captureCanvas = document.createElement('canvas')
        }
        
        this.captureCanvas.width = videoStream.naturalWidth || videoStream.width || 640
        this.captureCanvas.height = videoStream.naturalHeight || videoStream.height || 480
        
        const ctx = this.captureCanvas.getContext('2d')
        ctx.drawImage(videoStream, 0, 0, this.captureCanvas.width, this.captureCanvas.height)
        
        const imageData = this.captureCanvas.toDataURL('image/jpeg', 0.8)
        
        console.log('📸 Captured frame from video stream')
        resolve(imageData)
      } catch (error) {
        console.error('Error capturing image:', error)
        resolve(null)
      }
    })
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