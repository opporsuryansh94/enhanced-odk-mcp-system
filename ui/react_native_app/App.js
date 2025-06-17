/**
 * Enhanced Mobile App Entry Point for ODK MCP System
 * Features: Offline sync, QR scanning, push notifications, multilingual support
 */

import React, { useEffect, useState } from 'react';
import {
  StatusBar,
  Alert,
  Platform,
  PermissionsAndroid,
  AppState,
  Linking
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { Provider as PaperProvider } from 'react-native-paper';
import SplashScreen from 'react-native-splash-screen';
import PushNotification from 'react-native-push-notification';
import { I18nManager } from 'react-native';
import DeviceInfo from 'react-native-device-info';

// Contexts
import { AuthProvider } from './src/contexts/AuthContext';
import { ProjectProvider } from './src/contexts/ProjectContext';
import { OfflineProvider } from './src/contexts/OfflineContext';
import { NotificationProvider } from './src/contexts/NotificationContext';
import { LocalizationProvider } from './src/contexts/LocalizationContext';

// Navigation
import AppNavigator from './src/navigation/AppNavigator';

// Services
import { initializeDatabase } from './src/services/DatabaseService';
import { initializeNotifications } from './src/services/NotificationService';
import { initializeOfflineSync } from './src/services/OfflineSyncService';
import { initializeLocalization } from './src/services/LocalizationService';

// Utils
import { requestPermissions } from './src/utils/permissions';
import { setupCrashReporting } from './src/utils/crashReporting';

// Theme
import { theme } from './src/theme/theme';

const App = () => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [appState, setAppState] = useState(AppState.currentState);

  useEffect(() => {
    initializeApp();
    
    // App state change listener
    const subscription = AppState.addEventListener('change', handleAppStateChange);
    
    // Deep linking listener
    const linkingSubscription = Linking.addEventListener('url', handleDeepLink);
    
    return () => {
      subscription?.remove();
      linkingSubscription?.remove();
    };
  }, []);

  const initializeApp = async () => {
    try {
      // Show splash screen
      SplashScreen.show();
      
      // Request necessary permissions
      await requestPermissions();
      
      // Initialize core services
      await Promise.all([
        initializeDatabase(),
        initializeNotifications(),
        initializeOfflineSync(),
        initializeLocalization()
      ]);
      
      // Setup crash reporting
      await setupCrashReporting();
      
      // Configure push notifications
      configurePushNotifications();
      
      setIsInitialized(true);
      
      // Hide splash screen after initialization
      setTimeout(() => {
        SplashScreen.hide();
      }, 1000);
      
    } catch (error) {
      console.error('App initialization error:', error);
      Alert.alert(
        'Initialization Error',
        'Failed to initialize the app. Please restart the application.',
        [{ text: 'OK' }]
      );
    }
  };

  const configurePushNotifications = () => {
    PushNotification.configure({
      onRegister: function(token) {
        console.log('Push notification token:', token);
        // Send token to server for user registration
      },

      onNotification: function(notification) {
        console.log('Notification received:', notification);
        
        if (notification.userInteraction) {
          // User tapped on notification
          handleNotificationTap(notification);
        }
      },

      onAction: function(notification) {
        console.log('Notification action:', notification.action);
      },

      onRegistrationError: function(err) {
        console.error('Push notification registration error:', err.message);
      },

      permissions: {
        alert: true,
        badge: true,
        sound: true,
      },

      popInitialNotification: true,
      requestPermissions: Platform.OS === 'ios',
    });

    // Create notification channels for Android
    if (Platform.OS === 'android') {
      PushNotification.createChannel(
        {
          channelId: 'odk-mcp-default',
          channelName: 'ODK MCP Notifications',
          channelDescription: 'Default notifications for ODK MCP System',
          playSound: true,
          soundName: 'default',
          importance: 4,
          vibrate: true,
        },
        (created) => console.log(`Notification channel created: ${created}`)
      );
    }
  };

  const handleAppStateChange = (nextAppState) => {
    if (appState.match(/inactive|background/) && nextAppState === 'active') {
      // App has come to the foreground
      console.log('App has come to the foreground');
      // Trigger sync when app becomes active
      if (isInitialized) {
        // Sync offline data
        // This would be handled by OfflineContext
      }
    }
    setAppState(nextAppState);
  };

  const handleDeepLink = (event) => {
    console.log('Deep link received:', event.url);
    // Handle deep linking for form access, QR codes, etc.
    // Format: odkmc://form/{formId} or odkmc://qr/{qrData}
  };

  const handleNotificationTap = (notification) => {
    // Navigate to appropriate screen based on notification data
    const { data } = notification;
    
    if (data?.type === 'form_submission') {
      // Navigate to form submission details
    } else if (data?.type === 'sync_complete') {
      // Navigate to sync status
    } else if (data?.type === 'new_form') {
      // Navigate to new form
    }
  };

  if (!isInitialized) {
    // Return loading screen or splash screen component
    return null;
  }

  return (
    <PaperProvider theme={theme}>
      <LocalizationProvider>
        <AuthProvider>
          <ProjectProvider>
            <OfflineProvider>
              <NotificationProvider>
                <NavigationContainer>
                  <StatusBar
                    barStyle="dark-content"
                    backgroundColor={theme.colors.surface}
                    translucent={false}
                  />
                  <AppNavigator />
                </NavigationContainer>
              </NotificationProvider>
            </OfflineProvider>
          </ProjectProvider>
        </AuthProvider>
      </LocalizationProvider>
    </PaperProvider>
  );
};

export default App;

