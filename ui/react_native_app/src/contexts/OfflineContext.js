/**
 * Enhanced Offline Context for ODK MCP Mobile App
 * Provides offline data storage, sync capabilities, and network status management
 */

import React, { createContext, useContext, useReducer, useEffect } from 'react';
import NetInfo from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';

// Services
import { DatabaseService } from '../services/DatabaseService';
import { SyncService } from '../services/SyncService';
import { NotificationService } from '../services/NotificationService';

// Initial state
const initialState = {
  isOnline: true,
  isConnected: false,
  connectionType: null,
  syncStatus: 'idle', // idle, syncing, success, error
  pendingUploads: [],
  pendingDownloads: [],
  lastSyncTime: null,
  syncProgress: 0,
  offlineData: {
    forms: [],
    submissions: [],
    projects: [],
    media: []
  },
  syncSettings: {
    autoSync: true,
    syncOnWifiOnly: false,
    syncInterval: 300000, // 5 minutes
    maxRetries: 3
  }
};

// Action types
const OFFLINE_ACTIONS = {
  SET_NETWORK_STATUS: 'SET_NETWORK_STATUS',
  SET_SYNC_STATUS: 'SET_SYNC_STATUS',
  SET_SYNC_PROGRESS: 'SET_SYNC_PROGRESS',
  ADD_PENDING_UPLOAD: 'ADD_PENDING_UPLOAD',
  REMOVE_PENDING_UPLOAD: 'REMOVE_PENDING_UPLOAD',
  ADD_PENDING_DOWNLOAD: 'ADD_PENDING_DOWNLOAD',
  REMOVE_PENDING_DOWNLOAD: 'REMOVE_PENDING_DOWNLOAD',
  UPDATE_OFFLINE_DATA: 'UPDATE_OFFLINE_DATA',
  SET_LAST_SYNC_TIME: 'SET_LAST_SYNC_TIME',
  UPDATE_SYNC_SETTINGS: 'UPDATE_SYNC_SETTINGS',
  CLEAR_PENDING_ITEMS: 'CLEAR_PENDING_ITEMS'
};

// Reducer
const offlineReducer = (state, action) => {
  switch (action.type) {
    case OFFLINE_ACTIONS.SET_NETWORK_STATUS:
      return {
        ...state,
        isOnline: action.payload.isOnline,
        isConnected: action.payload.isConnected,
        connectionType: action.payload.connectionType
      };
    
    case OFFLINE_ACTIONS.SET_SYNC_STATUS:
      return {
        ...state,
        syncStatus: action.payload
      };
    
    case OFFLINE_ACTIONS.SET_SYNC_PROGRESS:
      return {
        ...state,
        syncProgress: action.payload
      };
    
    case OFFLINE_ACTIONS.ADD_PENDING_UPLOAD:
      return {
        ...state,
        pendingUploads: [...state.pendingUploads, action.payload]
      };
    
    case OFFLINE_ACTIONS.REMOVE_PENDING_UPLOAD:
      return {
        ...state,
        pendingUploads: state.pendingUploads.filter(item => item.id !== action.payload)
      };
    
    case OFFLINE_ACTIONS.ADD_PENDING_DOWNLOAD:
      return {
        ...state,
        pendingDownloads: [...state.pendingDownloads, action.payload]
      };
    
    case OFFLINE_ACTIONS.REMOVE_PENDING_DOWNLOAD:
      return {
        ...state,
        pendingDownloads: state.pendingDownloads.filter(item => item.id !== action.payload)
      };
    
    case OFFLINE_ACTIONS.UPDATE_OFFLINE_DATA:
      return {
        ...state,
        offlineData: {
          ...state.offlineData,
          [action.payload.type]: action.payload.data
        }
      };
    
    case OFFLINE_ACTIONS.SET_LAST_SYNC_TIME:
      return {
        ...state,
        lastSyncTime: action.payload
      };
    
    case OFFLINE_ACTIONS.UPDATE_SYNC_SETTINGS:
      return {
        ...state,
        syncSettings: {
          ...state.syncSettings,
          ...action.payload
        }
      };
    
    case OFFLINE_ACTIONS.CLEAR_PENDING_ITEMS:
      return {
        ...state,
        pendingUploads: [],
        pendingDownloads: []
      };
    
    default:
      return state;
  }
};

// Context
const OfflineContext = createContext();

// Provider component
export const OfflineProvider = ({ children }) => {
  const [state, dispatch] = useReducer(offlineReducer, initialState);

  useEffect(() => {
    initializeOfflineContext();
    setupNetworkListener();
    setupAutoSync();
    
    return () => {
      // Cleanup listeners
    };
  }, []);

  const initializeOfflineContext = async () => {
    try {
      // Load sync settings from storage
      const savedSettings = await AsyncStorage.getItem('syncSettings');
      if (savedSettings) {
        dispatch({
          type: OFFLINE_ACTIONS.UPDATE_SYNC_SETTINGS,
          payload: JSON.parse(savedSettings)
        });
      }

      // Load last sync time
      const lastSync = await AsyncStorage.getItem('lastSyncTime');
      if (lastSync) {
        dispatch({
          type: OFFLINE_ACTIONS.SET_LAST_SYNC_TIME,
          payload: new Date(lastSync)
        });
      }

      // Load offline data
      await loadOfflineData();
      
    } catch (error) {
      console.error('Failed to initialize offline context:', error);
    }
  };

  const setupNetworkListener = () => {
    const unsubscribe = NetInfo.addEventListener(state => {
      const isOnline = state.isConnected && state.isInternetReachable;
      
      dispatch({
        type: OFFLINE_ACTIONS.SET_NETWORK_STATUS,
        payload: {
          isOnline,
          isConnected: state.isConnected,
          connectionType: state.type
        }
      });

      // Auto-sync when coming back online
      if (isOnline && state.syncSettings.autoSync) {
        setTimeout(() => {
          syncData();
        }, 2000); // Wait 2 seconds before syncing
      }
    });

    return unsubscribe;
  };

  const setupAutoSync = () => {
    if (state.syncSettings.autoSync) {
      const interval = setInterval(() => {
        if (state.isOnline) {
          syncData();
        }
      }, state.syncSettings.syncInterval);

      return () => clearInterval(interval);
    }
  };

  const loadOfflineData = async () => {
    try {
      // Load forms
      const forms = await DatabaseService.getAllForms();
      dispatch({
        type: OFFLINE_ACTIONS.UPDATE_OFFLINE_DATA,
        payload: { type: 'forms', data: forms }
      });

      // Load submissions
      const submissions = await DatabaseService.getAllSubmissions();
      dispatch({
        type: OFFLINE_ACTIONS.UPDATE_OFFLINE_DATA,
        payload: { type: 'submissions', data: submissions }
      });

      // Load projects
      const projects = await DatabaseService.getAllProjects();
      dispatch({
        type: OFFLINE_ACTIONS.UPDATE_OFFLINE_DATA,
        payload: { type: 'projects', data: projects }
      });

    } catch (error) {
      console.error('Failed to load offline data:', error);
    }
  };

  const syncData = async () => {
    if (!state.isOnline || state.syncStatus === 'syncing') {
      return;
    }

    try {
      dispatch({ type: OFFLINE_ACTIONS.SET_SYNC_STATUS, payload: 'syncing' });
      dispatch({ type: OFFLINE_ACTIONS.SET_SYNC_PROGRESS, payload: 0 });

      // Upload pending submissions
      await uploadPendingSubmissions();
      
      // Download new forms and updates
      await downloadUpdates();
      
      // Update last sync time
      const now = new Date();
      dispatch({ type: OFFLINE_ACTIONS.SET_LAST_SYNC_TIME, payload: now });
      await AsyncStorage.setItem('lastSyncTime', now.toISOString());

      dispatch({ type: OFFLINE_ACTIONS.SET_SYNC_STATUS, payload: 'success' });
      dispatch({ type: OFFLINE_ACTIONS.SET_SYNC_PROGRESS, payload: 100 });

      // Show success notification
      NotificationService.showLocalNotification({
        title: 'Sync Complete',
        message: 'All data has been synchronized successfully.',
        type: 'success'
      });

    } catch (error) {
      console.error('Sync failed:', error);
      dispatch({ type: OFFLINE_ACTIONS.SET_SYNC_STATUS, payload: 'error' });
      
      // Show error notification
      NotificationService.showLocalNotification({
        title: 'Sync Failed',
        message: 'Failed to synchronize data. Will retry automatically.',
        type: 'error'
      });
    }
  };

  const uploadPendingSubmissions = async () => {
    const pendingSubmissions = await DatabaseService.getPendingSubmissions();
    
    for (let i = 0; i < pendingSubmissions.length; i++) {
      const submission = pendingSubmissions[i];
      
      try {
        // Upload submission
        await SyncService.uploadSubmission(submission);
        
        // Mark as synced
        await DatabaseService.markSubmissionAsSynced(submission.id);
        
        // Update progress
        const progress = ((i + 1) / pendingSubmissions.length) * 50; // 50% for uploads
        dispatch({ type: OFFLINE_ACTIONS.SET_SYNC_PROGRESS, payload: progress });
        
      } catch (error) {
        console.error(`Failed to upload submission ${submission.id}:`, error);
        // Continue with other submissions
      }
    }
  };

  const downloadUpdates = async () => {
    try {
      // Download new forms
      const newForms = await SyncService.downloadNewForms();
      if (newForms.length > 0) {
        await DatabaseService.saveForms(newForms);
        dispatch({
          type: OFFLINE_ACTIONS.UPDATE_OFFLINE_DATA,
          payload: { type: 'forms', data: await DatabaseService.getAllForms() }
        });
      }

      // Download form updates
      const formUpdates = await SyncService.downloadFormUpdates();
      if (formUpdates.length > 0) {
        await DatabaseService.updateForms(formUpdates);
      }

      // Update progress
      dispatch({ type: OFFLINE_ACTIONS.SET_SYNC_PROGRESS, payload: 75 });

      // Download media files
      await downloadPendingMedia();

    } catch (error) {
      console.error('Failed to download updates:', error);
      throw error;
    }
  };

  const downloadPendingMedia = async () => {
    const pendingMedia = state.pendingDownloads.filter(item => item.type === 'media');
    
    for (let i = 0; i < pendingMedia.length; i++) {
      const mediaItem = pendingMedia[i];
      
      try {
        await SyncService.downloadMedia(mediaItem);
        dispatch({
          type: OFFLINE_ACTIONS.REMOVE_PENDING_DOWNLOAD,
          payload: mediaItem.id
        });
        
      } catch (error) {
        console.error(`Failed to download media ${mediaItem.id}:`, error);
      }
    }
  };

  const saveFormSubmission = async (formId, submissionData) => {
    try {
      // Save to local database
      const submission = {
        id: `submission_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        formId,
        data: submissionData,
        timestamp: new Date().toISOString(),
        synced: false,
        userId: submissionData.userId || 'anonymous'
      };

      await DatabaseService.saveSubmission(submission);

      // Add to pending uploads if online
      if (state.isOnline) {
        dispatch({
          type: OFFLINE_ACTIONS.ADD_PENDING_UPLOAD,
          payload: {
            id: submission.id,
            type: 'submission',
            data: submission
          }
        });
      }

      // Update offline data
      const submissions = await DatabaseService.getAllSubmissions();
      dispatch({
        type: OFFLINE_ACTIONS.UPDATE_OFFLINE_DATA,
        payload: { type: 'submissions', data: submissions }
      });

      return submission;

    } catch (error) {
      console.error('Failed to save form submission:', error);
      throw error;
    }
  };

  const saveMediaFile = async (mediaData) => {
    try {
      // Save media file locally
      const mediaFile = await DatabaseService.saveMediaFile(mediaData);

      // Add to pending uploads if online
      if (state.isOnline) {
        dispatch({
          type: OFFLINE_ACTIONS.ADD_PENDING_UPLOAD,
          payload: {
            id: mediaFile.id,
            type: 'media',
            data: mediaFile
          }
        });
      }

      return mediaFile;

    } catch (error) {
      console.error('Failed to save media file:', error);
      throw error;
    }
  };

  const updateSyncSettings = async (newSettings) => {
    try {
      const updatedSettings = { ...state.syncSettings, ...newSettings };
      
      dispatch({
        type: OFFLINE_ACTIONS.UPDATE_SYNC_SETTINGS,
        payload: updatedSettings
      });

      await AsyncStorage.setItem('syncSettings', JSON.stringify(updatedSettings));

    } catch (error) {
      console.error('Failed to update sync settings:', error);
    }
  };

  const forceSyncNow = async () => {
    if (!state.isOnline) {
      Alert.alert(
        'No Internet Connection',
        'Please check your internet connection and try again.',
        [{ text: 'OK' }]
      );
      return;
    }

    await syncData();
  };

  const clearOfflineData = async () => {
    try {
      await DatabaseService.clearAllData();
      dispatch({ type: OFFLINE_ACTIONS.CLEAR_PENDING_ITEMS });
      await loadOfflineData();
      
      Alert.alert(
        'Data Cleared',
        'All offline data has been cleared successfully.',
        [{ text: 'OK' }]
      );

    } catch (error) {
      console.error('Failed to clear offline data:', error);
      Alert.alert(
        'Error',
        'Failed to clear offline data. Please try again.',
        [{ text: 'OK' }]
      );
    }
  };

  const getOfflineDataSize = async () => {
    try {
      return await DatabaseService.getDataSize();
    } catch (error) {
      console.error('Failed to get offline data size:', error);
      return 0;
    }
  };

  const value = {
    ...state,
    syncData,
    saveFormSubmission,
    saveMediaFile,
    updateSyncSettings,
    forceSyncNow,
    clearOfflineData,
    getOfflineDataSize,
    loadOfflineData
  };

  return (
    <OfflineContext.Provider value={value}>
      {children}
    </OfflineContext.Provider>
  );
};

// Hook to use offline context
export const useOffline = () => {
  const context = useContext(OfflineContext);
  if (!context) {
    throw new Error('useOffline must be used within an OfflineProvider');
  }
  return context;
};

