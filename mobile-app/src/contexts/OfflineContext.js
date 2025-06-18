/**
 * Enhanced Offline Context for Mobile App
 * Handles offline data storage, synchronization, and conflict resolution
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'
import NetInfo from '@react-native-community/netinfo'
import { Alert } from 'react-native'

// Services
import { syncService } from '../services/SyncService'
import { storageService } from '../services/StorageService'
import { formService } from '../services/FormService'

const OfflineContext = createContext()

export const useOffline = () => {
  const context = useContext(OfflineContext)
  if (!context) {
    throw new Error('useOffline must be used within an OfflineProvider')
  }
  return context
}

export const OfflineProvider = ({ children }) => {
  const [isOnline, setIsOnline] = useState(true)
  const [syncStatus, setSyncStatus] = useState('idle') // idle, syncing, success, error
  const [pendingSubmissions, setPendingSubmissions] = useState([])
  const [syncProgress, setSyncProgress] = useState(0)
  const [lastSyncTime, setLastSyncTime] = useState(null)
  const [conflictResolutions, setConflictResolutions] = useState([])

  useEffect(() => {
    initializeOfflineContext()
    setupNetworkListener()
    loadPendingSubmissions()
    loadLastSyncTime()
  }, [])

  const initializeOfflineContext = async () => {
    try {
      // Initialize offline storage
      await storageService.initialize()
      
      // Check initial network status
      const netInfo = await NetInfo.fetch()
      setIsOnline(netInfo.isConnected && netInfo.isInternetReachable)
      
    } catch (error) {
      console.error('Failed to initialize offline context:', error)
    }
  }

  const setupNetworkListener = () => {
    const unsubscribe = NetInfo.addEventListener(state => {
      const wasOnline = isOnline
      const nowOnline = state.isConnected && state.isInternetReachable
      
      setIsOnline(nowOnline)
      
      // Trigger sync when coming back online
      if (!wasOnline && nowOnline) {
        triggerSync()
      }
    })

    return unsubscribe
  }

  const loadPendingSubmissions = async () => {
    try {
      const pending = await storageService.getPendingSubmissions()
      setPendingSubmissions(pending)
    } catch (error) {
      console.error('Failed to load pending submissions:', error)
    }
  }

  const loadLastSyncTime = async () => {
    try {
      const lastSync = await AsyncStorage.getItem('lastSyncTime')
      if (lastSync) {
        setLastSyncTime(new Date(lastSync))
      }
    } catch (error) {
      console.error('Failed to load last sync time:', error)
    }
  }

  const saveSubmissionOffline = async (formId, submissionData) => {
    try {
      const submission = {
        id: `offline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        formId,
        data: submissionData,
        timestamp: new Date().toISOString(),
        status: 'pending',
        attachments: submissionData.attachments || []
      }

      // Save to local storage
      await storageService.saveSubmission(submission)
      
      // Update pending submissions
      const updatedPending = [...pendingSubmissions, submission]
      setPendingSubmissions(updatedPending)
      
      return submission

    } catch (error) {
      console.error('Failed to save submission offline:', error)
      throw error
    }
  }

  const triggerSync = useCallback(async () => {
    if (!isOnline || syncStatus === 'syncing') {
      return
    }

    try {
      setSyncStatus('syncing')
      setSyncProgress(0)

      // Get all pending submissions
      const pending = await storageService.getPendingSubmissions()
      
      if (pending.length === 0) {
        setSyncStatus('success')
        return
      }

      let syncedCount = 0
      const conflicts = []

      for (const submission of pending) {
        try {
          setSyncProgress((syncedCount / pending.length) * 100)

          // Attempt to sync submission
          const result = await syncService.syncSubmission(submission)
          
          if (result.success) {
            // Remove from local storage
            await storageService.removeSubmission(submission.id)
            syncedCount++
          } else if (result.conflict) {
            // Handle conflict
            conflicts.push({
              submission,
              serverData: result.serverData,
              conflictType: result.conflictType
            })
          }

        } catch (error) {
          console.error(`Failed to sync submission ${submission.id}:`, error)
        }
      }

      // Update pending submissions
      await loadPendingSubmissions()
      
      // Handle conflicts
      if (conflicts.length > 0) {
        setConflictResolutions(conflicts)
        setSyncStatus('conflict')
      } else {
        setSyncStatus('success')
      }

      // Update last sync time
      const now = new Date()
      setLastSyncTime(now)
      await AsyncStorage.setItem('lastSyncTime', now.toISOString())

      setSyncProgress(100)

    } catch (error) {
      console.error('Sync failed:', error)
      setSyncStatus('error')
    }
  }, [isOnline, syncStatus, pendingSubmissions])

  const resolveConflict = async (conflictId, resolution) => {
    try {
      const conflict = conflictResolutions.find(c => c.submission.id === conflictId)
      if (!conflict) return

      let finalData
      switch (resolution.type) {
        case 'use_local':
          finalData = conflict.submission.data
          break
        case 'use_server':
          finalData = conflict.serverData
          break
        case 'merge':
          finalData = { ...conflict.serverData, ...resolution.mergedData }
          break
        default:
          throw new Error('Invalid resolution type')
      }

      // Apply resolution
      const result = await syncService.resolveConflict(conflictId, finalData)
      
      if (result.success) {
        // Remove from conflicts
        setConflictResolutions(prev => 
          prev.filter(c => c.submission.id !== conflictId)
        )
        
        // Remove from local storage
        await storageService.removeSubmission(conflictId)
        
        // Update pending submissions
        await loadPendingSubmissions()
      }

    } catch (error) {
      console.error('Failed to resolve conflict:', error)
      Alert.alert('Error', 'Failed to resolve conflict. Please try again.')
    }
  }

  const downloadFormForOffline = async (formId) => {
    try {
      if (!isOnline) {
        throw new Error('Internet connection required to download forms')
      }

      const form = await formService.getForm(formId)
      await storageService.saveForm(form)
      
      return form

    } catch (error) {
      console.error('Failed to download form for offline use:', error)
      throw error
    }
  }

  const getOfflineForms = async () => {
    try {
      return await storageService.getOfflineForms()
    } catch (error) {
      console.error('Failed to get offline forms:', error)
      return []
    }
  }

  const clearOfflineData = async () => {
    try {
      await storageService.clearAll()
      setPendingSubmissions([])
      setConflictResolutions([])
      setLastSyncTime(null)
      await AsyncStorage.removeItem('lastSyncTime')
    } catch (error) {
      console.error('Failed to clear offline data:', error)
      throw error
    }
  }

  const getStorageInfo = async () => {
    try {
      const info = await storageService.getStorageInfo()
      return {
        ...info,
        pendingCount: pendingSubmissions.length,
        conflictCount: conflictResolutions.length
      }
    } catch (error) {
      console.error('Failed to get storage info:', error)
      return null
    }
  }

  const value = {
    // State
    isOnline,
    syncStatus,
    syncProgress,
    pendingSubmissions,
    lastSyncTime,
    conflictResolutions,

    // Actions
    saveSubmissionOffline,
    triggerSync,
    resolveConflict,
    downloadFormForOffline,
    getOfflineForms,
    clearOfflineData,
    getStorageInfo,

    // Computed
    hasPendingSubmissions: pendingSubmissions.length > 0,
    hasConflicts: conflictResolutions.length > 0,
    canSync: isOnline && syncStatus !== 'syncing'
  }

  return (
    <OfflineContext.Provider value={value}>
      {children}
    </OfflineContext.Provider>
  )
}

