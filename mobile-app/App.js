/**
 * Enhanced ODK MCP Mobile Application
 * Main App Component with Navigation and State Management
 */

import React, { useEffect, useState } from 'react'
import { StatusBar, Platform, Alert, AppState } from 'react-native'
import { NavigationContainer } from '@react-navigation/native'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import SplashScreen from 'react-native-splash-screen'
import NetInfo from '@react-native-community/netinfo'
import PushNotification from 'react-native-push-notification'
import DeviceInfo from 'react-native-device-info'

// Navigation
import AppNavigator from './src/navigation/AppNavigator'

// Contexts
import { AuthProvider } from './src/contexts/AuthContext'
import { ThemeProvider } from './src/contexts/ThemeContext'
import { OfflineProvider } from './src/contexts/OfflineContext'
import { NotificationProvider } from './src/contexts/NotificationContext'
import { FormProvider } from './src/contexts/FormContext'

// Services
import { syncService } from './src/services/SyncService'
import { storageService } from './src/services/StorageService'
import { analyticsService } from './src/services/AnalyticsService'

// Utils
import { setupPushNotifications } from './src/utils/pushNotifications'
import { initializeDatabase } from './src/utils/database'
import { checkPermissions } from './src/utils/permissions'

const App = () => {
  const [isReady, setIsReady] = useState(false)
  const [appState, setAppState] = useState(AppState.currentState)

  useEffect(() => {
    initializeApp()
  }, [])

  useEffect(() => {
    const subscription = AppState.addEventListener('change', handleAppStateChange)
    return () => subscription?.remove()
  }, [])

  const initializeApp = async () => {
    try {
      // Initialize core services
      await Promise.all([
        initializeDatabase(),
        storageService.initialize(),
        checkPermissions(),
        setupPushNotifications()
      ])

      // Setup network monitoring
      setupNetworkMonitoring()

      // Initialize analytics
      await analyticsService.initialize()

      // Track app launch
      analyticsService.trackEvent('app_launched', {
        platform: Platform.OS,
        version: DeviceInfo.getVersion(),
        build: DeviceInfo.getBuildNumber()
      })

      setIsReady(true)
      
      // Hide splash screen
      if (Platform.OS === 'android') {
        SplashScreen.hide()
      }

    } catch (error) {
      console.error('App initialization failed:', error)
      Alert.alert(
        'Initialization Error',
        'Failed to initialize the app. Please restart the application.',
        [{ text: 'OK' }]
      )
    }
  }

  const setupNetworkMonitoring = () => {
    NetInfo.addEventListener(state => {
      if (state.isConnected && state.isInternetReachable) {
        // Trigger sync when connection is restored
        syncService.triggerSync()
      }
    })
  }

  const handleAppStateChange = (nextAppState) => {
    if (appState.match(/inactive|background/) && nextAppState === 'active') {
      // App has come to the foreground
      syncService.triggerSync()
      analyticsService.trackEvent('app_foregrounded')
    } else if (nextAppState.match(/inactive|background/)) {
      // App has gone to the background
      analyticsService.trackEvent('app_backgrounded')
    }
    
    setAppState(nextAppState)
  }

  if (!isReady) {
    return null // Splash screen is shown
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ThemeProvider>
        <AuthProvider>
          <OfflineProvider>
            <NotificationProvider>
              <FormProvider>
                <NavigationContainer>
                  <StatusBar
                    barStyle="dark-content"
                    backgroundColor="transparent"
                    translucent
                  />
                  <AppNavigator />
                </NavigationContainer>
              </FormProvider>
            </NotificationProvider>
          </OfflineProvider>
        </AuthProvider>
      </ThemeProvider>
    </GestureHandlerRootView>
  )
}

export default App

