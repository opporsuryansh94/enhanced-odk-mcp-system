# Enhanced ODK MCP Mobile Application

## Overview

The Enhanced ODK MCP Mobile Application is a cutting-edge React Native application designed for offline-first data collection in challenging field environments. Built specifically for NGOs, think tanks, and CSR organizations, this mobile app provides a comprehensive solution for collecting, validating, and synchronizing data with enterprise-grade security and AI-powered features.

## Key Features

### 🚀 Core Capabilities

**Offline-First Architecture**
- Complete functionality without internet connectivity
- Local SQLite database for data storage
- Intelligent synchronization when network is available
- Conflict resolution for concurrent data modifications
- Automatic retry mechanisms for failed sync operations

**Advanced Data Collection**
- Dynamic form rendering from server configurations
- Real-time validation with immediate feedback
- Support for all field types: text, number, date, select, multi-select, file upload
- Conditional logic and skip patterns
- Calculated fields and data transformations

**Media Integration**
- High-quality photo capture with automatic compression
- Audio recording with noise reduction
- Video recording with configurable quality settings
- File picker for document attachments
- Automatic media optimization for storage efficiency

**Geolocation Services**
- GPS coordinate capture with configurable accuracy
- Offline mapping with cached map tiles
- Geofencing for location-based form access
- Privacy controls for location data
- Integration with popular mapping services

**QR Code Integration**
- Quick form access via QR code scanning
- Automatic form download and caching
- QR code generation for data sharing
- Batch operations via QR code scanning
- Integration with form management system

### 🔒 Security Features

**Data Protection**
- End-to-end encryption for sensitive data
- Biometric authentication (fingerprint, face recognition)
- Secure local storage with encryption at rest
- Session management with automatic timeout
- Device binding for enhanced security

**Privacy Controls**
- Granular permissions for data access
- User consent management
- Data anonymization options
- GDPR compliance features
- Audit trail for all data operations

### 🎨 User Experience

**Modern Interface Design**
- Material Design 3 components
- Dark mode support with automatic switching
- Responsive layout for phones and tablets
- Accessibility features for users with disabilities
- Intuitive navigation with gesture support

**Multilingual Support**
- Localization for 20+ languages
- Right-to-left (RTL) language support
- Dynamic language switching
- Cultural adaptation for different regions
- Voice input in multiple languages

## Technical Architecture

### Technology Stack

**Core Framework**
- React Native 0.72+
- TypeScript for type safety
- React Navigation 6 for routing
- React Query for data management
- Zustand for state management

**Database and Storage**
- SQLite for local data storage
- React Native MMKV for key-value storage
- Encrypted storage for sensitive data
- File system management for media files
- Background sync with conflict resolution

**UI Components**
- React Native Elements for base components
- React Native Vector Icons for iconography
- React Native Reanimated for animations
- React Native Gesture Handler for interactions
- Custom components for form rendering

**Device Integration**
- React Native Camera for photo/video capture
- React Native Audio Recorder for audio capture
- React Native Geolocation for GPS services
- React Native QR Code Scanner for QR functionality
- React Native Biometrics for authentication

### Project Structure

```
mobile-app/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── forms/          # Form-specific components
│   │   ├── media/          # Media capture components
│   │   ├── navigation/     # Navigation components
│   │   └── ui/             # Base UI components
│   ├── screens/            # Application screens
│   │   ├── auth/           # Authentication screens
│   │   ├── forms/          # Form-related screens
│   │   ├── settings/       # Settings and configuration
│   │   └── sync/           # Data synchronization screens
│   ├── services/           # Business logic and API calls
│   │   ├── api/            # API service layer
│   │   ├── database/       # Local database operations
│   │   ├── sync/           # Data synchronization logic
│   │   └── storage/        # File and media storage
│   ├── utils/              # Utility functions and helpers
│   ├── contexts/           # React contexts for state management
│   ├── hooks/              # Custom React hooks
│   ├── types/              # TypeScript type definitions
│   └── config/             # Configuration files
├── android/                # Android-specific code
├── ios/                    # iOS-specific code
├── assets/                 # Static assets (images, fonts)
└── docs/                   # Documentation files
```

## Installation and Setup

### Prerequisites

**Development Environment**
- Node.js 18+ with npm or yarn
- React Native CLI or Expo CLI
- Android Studio (for Android development)
- Xcode (for iOS development, macOS only)
- Java Development Kit (JDK) 11+

**Device Requirements**
- Android 7.0+ (API level 24+) or iOS 12.0+
- Minimum 2GB RAM (4GB recommended)
- 1GB available storage space
- Camera and microphone access
- GPS capability (optional but recommended)

### Development Setup

**1. Clone Repository**
```bash
git clone https://github.com/opporsuryansh94/enhanced-odk-mcp-system.git
cd enhanced-odk-mcp-system/mobile-app
```

**2. Install Dependencies**
```bash
# Install Node.js dependencies
npm install

# Install iOS dependencies (macOS only)
cd ios && pod install && cd ..
```

**3. Configure Environment**
```bash
# Copy environment configuration
cp .env.example .env

# Edit configuration file
nano .env
```

**Environment Configuration**
```bash
# API Configuration
API_BASE_URL=http://localhost:5003
API_TIMEOUT=30000
API_RETRY_ATTEMPTS=3

# Database Configuration
DB_NAME=odk_mcp_mobile.db
DB_VERSION=1
ENCRYPTION_KEY=your-encryption-key

# Feature Flags
ENABLE_BIOMETRICS=true
ENABLE_OFFLINE_MAPS=true
ENABLE_ANALYTICS=false
DEBUG_MODE=true

# Media Configuration
MAX_PHOTO_SIZE=5242880  # 5MB
MAX_VIDEO_DURATION=300  # 5 minutes
AUDIO_QUALITY=high
COMPRESSION_QUALITY=0.8

# Sync Configuration
SYNC_INTERVAL=300000    # 5 minutes
MAX_RETRY_ATTEMPTS=5
BATCH_SIZE=50
```

**4. Run Application**
```bash
# Start Metro bundler
npx react-native start

# Run on Android
npx react-native run-android

# Run on iOS (macOS only)
npx react-native run-ios
```

### Building for Production

**Android APK**
```bash
cd android
./gradlew assembleRelease

# APK location: android/app/build/outputs/apk/release/app-release.apk
```

**Android App Bundle (for Google Play)**
```bash
cd android
./gradlew bundleRelease

# Bundle location: android/app/build/outputs/bundle/release/app-release.aab
```

**iOS Build (macOS only)**
```bash
# Open Xcode project
open ios/ODKMCPMobile.xcworkspace

# Build using Xcode or command line
xcodebuild -workspace ios/ODKMCPMobile.xcworkspace \
           -scheme ODKMCPMobile \
           -configuration Release \
           -archivePath build/ODKMCPMobile.xcarchive \
           archive
```

## Core Features Implementation

### Form Rendering Engine

The mobile app includes a sophisticated form rendering engine that dynamically creates native UI components based on server-side form configurations.

**Supported Field Types**
```typescript
interface FormField {
  name: string;
  type: 'text' | 'number' | 'date' | 'select' | 'multi-select' | 
        'photo' | 'audio' | 'video' | 'file' | 'geopoint' | 'barcode';
  label: string;
  required: boolean;
  validation?: ValidationRules;
  conditional?: ConditionalLogic;
  appearance?: FieldAppearance;
}

interface ValidationRules {
  min?: number;
  max?: number;
  pattern?: string;
  custom?: string;
}

interface ConditionalLogic {
  condition: string;
  action: 'show' | 'hide' | 'require' | 'disable';
  target?: string[];
}
```

**Form Component Example**
```typescript
import React from 'react';
import { FormRenderer } from '../components/forms/FormRenderer';

const DataCollectionScreen: React.FC = () => {
  const [formData, setFormData] = useState({});
  const [formConfig, setFormConfig] = useState(null);

  const handleSubmit = async (data: FormData) => {
    try {
      await submitFormData(data);
      showSuccessMessage('Form submitted successfully');
    } catch (error) {
      showErrorMessage('Failed to submit form');
    }
  };

  return (
    <FormRenderer
      config={formConfig}
      data={formData}
      onDataChange={setFormData}
      onSubmit={handleSubmit}
      offline={!isConnected}
    />
  );
};
```

### Offline Data Management

**Local Database Schema**
```sql
-- Forms table
CREATE TABLE forms (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  version INTEGER NOT NULL,
  config TEXT NOT NULL,
  status TEXT DEFAULT 'active',
  downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Submissions table
CREATE TABLE submissions (
  id TEXT PRIMARY KEY,
  form_id TEXT NOT NULL,
  data TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  synced_at DATETIME,
  FOREIGN KEY (form_id) REFERENCES forms (id)
);

-- Media files table
CREATE TABLE media_files (
  id TEXT PRIMARY KEY,
  submission_id TEXT NOT NULL,
  field_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  synced BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (submission_id) REFERENCES submissions (id)
);
```

**Sync Service Implementation**
```typescript
class SyncService {
  private db: SQLiteDatabase;
  private api: ApiService;

  async syncPendingSubmissions(): Promise<SyncResult> {
    const pendingSubmissions = await this.db.getPendingSubmissions();
    const results: SyncResult[] = [];

    for (const submission of pendingSubmissions) {
      try {
        // Upload media files first
        await this.uploadMediaFiles(submission.id);
        
        // Submit form data
        const response = await this.api.submitForm(submission);
        
        // Mark as synced
        await this.db.markSubmissionSynced(submission.id, response.id);
        
        results.push({ id: submission.id, status: 'success' });
      } catch (error) {
        results.push({ id: submission.id, status: 'failed', error });
      }
    }

    return results;
  }

  async downloadForms(): Promise<void> {
    const availableForms = await this.api.getAvailableForms();
    
    for (const form of availableForms) {
      const localForm = await this.db.getForm(form.id);
      
      if (!localForm || localForm.version < form.version) {
        await this.db.saveForm(form);
      }
    }
  }
}
```

### Media Capture Integration

**Camera Component**
```typescript
import { Camera, useCameraDevices } from 'react-native-vision-camera';

const PhotoCaptureComponent: React.FC<PhotoCaptureProps> = ({
  onPhotoTaken,
  quality = 'high'
}) => {
  const devices = useCameraDevices();
  const device = devices.back;

  const takePhoto = async () => {
    if (camera.current) {
      const photo = await camera.current.takePhoto({
        quality: quality === 'high' ? 100 : 80,
        enableAutoRedEyeReduction: true,
        enableAutoStabilization: true,
      });

      // Compress and optimize photo
      const optimizedPhoto = await ImageResizer.createResizedImage(
        photo.path,
        1920,
        1080,
        'JPEG',
        80
      );

      onPhotoTaken(optimizedPhoto);
    }
  };

  return (
    <Camera
      ref={camera}
      style={StyleSheet.absoluteFill}
      device={device}
      isActive={true}
      photo={true}
    />
  );
};
```

**Audio Recording**
```typescript
import AudioRecorderPlayer from 'react-native-audio-recorder-player';

class AudioService {
  private audioRecorderPlayer = new AudioRecorderPlayer();

  async startRecording(filePath: string): Promise<void> {
    const audioSet = {
      AudioEncoderAndroid: AudioEncoderAndroidType.AAC,
      AudioSourceAndroid: AudioSourceAndroidType.MIC,
      AVEncoderAudioQualityKeyIOS: AVEncoderAudioQualityIOSType.high,
      AVNumberOfChannelsKeyIOS: 2,
      AVFormatIDKeyIOS: AVEncodingOption.aac,
    };

    await this.audioRecorderPlayer.startRecorder(filePath, audioSet);
  }

  async stopRecording(): Promise<string> {
    return await this.audioRecorderPlayer.stopRecorder();
  }
}
```

### QR Code Integration

**QR Scanner Component**
```typescript
import { RNCamera } from 'react-native-camera';

const QRScannerScreen: React.FC = () => {
  const [scanned, setScanned] = useState(false);

  const onBarCodeRead = async (scanResult: BarCodeReadEvent) => {
    if (scanned) return;
    
    setScanned(true);
    
    try {
      const qrData = JSON.parse(scanResult.data);
      
      if (qrData.type === 'form_access') {
        await downloadAndOpenForm(qrData.formId);
      } else if (qrData.type === 'data_validation') {
        await validateSubmission(qrData.submissionId);
      }
    } catch (error) {
      showErrorMessage('Invalid QR code format');
    }
    
    setTimeout(() => setScanned(false), 2000);
  };

  return (
    <RNCamera
      style={styles.camera}
      onBarCodeRead={onBarCodeRead}
      barCodeTypes={[RNCamera.Constants.BarCodeType.qr]}
      captureAudio={false}
    >
      <View style={styles.overlay}>
        <Text style={styles.instructions}>
          Scan QR code to access form or validate data
        </Text>
      </View>
    </RNCamera>
  );
};
```

## Configuration and Customization

### App Configuration

**Main Configuration File**
```typescript
// src/config/app.config.ts
export const AppConfig = {
  // API Configuration
  api: {
    baseUrl: process.env.API_BASE_URL || 'https://api.yourdomain.com',
    timeout: parseInt(process.env.API_TIMEOUT || '30000'),
    retryAttempts: parseInt(process.env.API_RETRY_ATTEMPTS || '3'),
  },

  // Database Configuration
  database: {
    name: process.env.DB_NAME || 'odk_mcp_mobile.db',
    version: parseInt(process.env.DB_VERSION || '1'),
    encryptionKey: process.env.ENCRYPTION_KEY,
  },

  // Feature Flags
  features: {
    biometrics: process.env.ENABLE_BIOMETRICS === 'true',
    offlineMaps: process.env.ENABLE_OFFLINE_MAPS === 'true',
    analytics: process.env.ENABLE_ANALYTICS === 'true',
    debugMode: process.env.DEBUG_MODE === 'true',
  },

  // Media Configuration
  media: {
    maxPhotoSize: parseInt(process.env.MAX_PHOTO_SIZE || '5242880'),
    maxVideoDuration: parseInt(process.env.MAX_VIDEO_DURATION || '300'),
    audioQuality: process.env.AUDIO_QUALITY || 'high',
    compressionQuality: parseFloat(process.env.COMPRESSION_QUALITY || '0.8'),
  },

  // Sync Configuration
  sync: {
    interval: parseInt(process.env.SYNC_INTERVAL || '300000'),
    maxRetryAttempts: parseInt(process.env.MAX_RETRY_ATTEMPTS || '5'),
    batchSize: parseInt(process.env.BATCH_SIZE || '50'),
  },
};
```

### Theme Customization

**Theme Configuration**
```typescript
// src/config/theme.ts
export const lightTheme = {
  colors: {
    primary: '#2563eb',
    secondary: '#059669',
    background: '#ffffff',
    surface: '#f8fafc',
    text: '#1f2937',
    textSecondary: '#6b7280',
    border: '#e5e7eb',
    error: '#dc2626',
    warning: '#f59e0b',
    success: '#10b981',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  typography: {
    h1: { fontSize: 32, fontWeight: 'bold' },
    h2: { fontSize: 24, fontWeight: 'bold' },
    h3: { fontSize: 20, fontWeight: '600' },
    body: { fontSize: 16, fontWeight: 'normal' },
    caption: { fontSize: 14, fontWeight: 'normal' },
  },
};

export const darkTheme = {
  ...lightTheme,
  colors: {
    ...lightTheme.colors,
    background: '#111827',
    surface: '#1f2937',
    text: '#f9fafb',
    textSecondary: '#d1d5db',
    border: '#374151',
  },
};
```

## Testing

### Unit Testing

**Test Configuration**
```javascript
// jest.config.js
module.exports = {
  preset: 'react-native',
  setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
  testMatch: ['**/__tests__/**/*.test.{js,ts,tsx}'],
  collectCoverageFrom: [
    'src/**/*.{js,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/test/**',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

**Example Test**
```typescript
// src/services/__tests__/SyncService.test.ts
import { SyncService } from '../SyncService';
import { MockDatabase } from '../../test/mocks/MockDatabase';
import { MockApiService } from '../../test/mocks/MockApiService';

describe('SyncService', () => {
  let syncService: SyncService;
  let mockDb: MockDatabase;
  let mockApi: MockApiService;

  beforeEach(() => {
    mockDb = new MockDatabase();
    mockApi = new MockApiService();
    syncService = new SyncService(mockDb, mockApi);
  });

  describe('syncPendingSubmissions', () => {
    it('should sync pending submissions successfully', async () => {
      const pendingSubmissions = [
        { id: '1', formId: 'form1', data: '{}', status: 'pending' },
        { id: '2', formId: 'form1', data: '{}', status: 'pending' },
      ];

      mockDb.getPendingSubmissions.mockResolvedValue(pendingSubmissions);
      mockApi.submitForm.mockResolvedValue({ id: 'server-id' });

      const results = await syncService.syncPendingSubmissions();

      expect(results).toHaveLength(2);
      expect(results[0].status).toBe('success');
      expect(mockDb.markSubmissionSynced).toHaveBeenCalledTimes(2);
    });

    it('should handle sync failures gracefully', async () => {
      const pendingSubmissions = [
        { id: '1', formId: 'form1', data: '{}', status: 'pending' },
      ];

      mockDb.getPendingSubmissions.mockResolvedValue(pendingSubmissions);
      mockApi.submitForm.mockRejectedValue(new Error('Network error'));

      const results = await syncService.syncPendingSubmissions();

      expect(results[0].status).toBe('failed');
      expect(results[0].error).toBeInstanceOf(Error);
    });
  });
});
```

### Integration Testing

**E2E Testing with Detox**
```javascript
// e2e/formSubmission.e2e.js
describe('Form Submission Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  it('should complete form submission offline', async () => {
    // Navigate to forms list
    await element(by.id('forms-tab')).tap();
    
    // Select a form
    await element(by.id('form-item-1')).tap();
    
    // Fill form fields
    await element(by.id('field-name')).typeText('John Doe');
    await element(by.id('field-age')).typeText('30');
    
    // Take a photo
    await element(by.id('photo-capture-button')).tap();
    await element(by.id('camera-capture-button')).tap();
    await element(by.id('photo-confirm-button')).tap();
    
    // Submit form
    await element(by.id('submit-button')).tap();
    
    // Verify success message
    await expect(element(by.text('Form submitted successfully'))).toBeVisible();
    
    // Verify form appears in pending sync
    await element(by.id('sync-tab')).tap();
    await expect(element(by.id('pending-submission-1'))).toBeVisible();
  });
});
```

## Performance Optimization

### Memory Management

**Image Optimization**
```typescript
import ImageResizer from 'react-native-image-resizer';

class MediaOptimizer {
  static async optimizePhoto(photoPath: string): Promise<string> {
    const optimized = await ImageResizer.createResizedImage(
      photoPath,
      1920,
      1080,
      'JPEG',
      80,
      0,
      undefined,
      false,
      {
        mode: 'contain',
        onlyScaleDown: true,
      }
    );

    return optimized.path;
  }

  static async compressVideo(videoPath: string): Promise<string> {
    // Implement video compression logic
    return videoPath;
  }
}
```

**Database Optimization**
```typescript
class DatabaseOptimizer {
  static async cleanupOldData(db: SQLiteDatabase): Promise<void> {
    // Remove synced submissions older than 30 days
    await db.executeSql(`
      DELETE FROM submissions 
      WHERE status = 'synced' 
      AND synced_at < datetime('now', '-30 days')
    `);

    // Remove orphaned media files
    await db.executeSql(`
      DELETE FROM media_files 
      WHERE submission_id NOT IN (SELECT id FROM submissions)
    `);

    // Vacuum database to reclaim space
    await db.executeSql('VACUUM');
  }
}
```

### Battery Optimization

**Background Sync Management**
```typescript
import BackgroundJob from 'react-native-background-job';

class BackgroundSyncManager {
  static startBackgroundSync(): void {
    BackgroundJob.start({
      jobKey: 'syncData',
      period: 300000, // 5 minutes
      requiredNetworkType: 'unmetered', // WiFi only
      requiresCharging: false,
      requiresDeviceIdle: false,
    });
  }

  static stopBackgroundSync(): void {
    BackgroundJob.stop({
      jobKey: 'syncData',
    });
  }
}
```

## Deployment and Distribution

### App Store Deployment

**iOS App Store**
1. Configure app signing in Xcode
2. Update version and build numbers
3. Create app store listing with screenshots
4. Submit for review through App Store Connect
5. Monitor review status and respond to feedback

**Google Play Store**
1. Generate signed APK or App Bundle
2. Create store listing with metadata
3. Upload APK/Bundle to Google Play Console
4. Configure release tracks (internal, alpha, beta, production)
5. Submit for review and monitor release

### Enterprise Distribution

**iOS Enterprise Distribution**
```bash
# Build for enterprise distribution
xcodebuild -workspace ios/ODKMCPMobile.xcworkspace \
           -scheme ODKMCPMobile \
           -configuration Release \
           -archivePath build/ODKMCPMobile.xcarchive \
           archive

# Export IPA for enterprise distribution
xcodebuild -exportArchive \
           -archivePath build/ODKMCPMobile.xcarchive \
           -exportPath build/ \
           -exportOptionsPlist ExportOptions.plist
```

**Android Enterprise Distribution**
```bash
# Build signed APK
cd android
./gradlew assembleRelease

# Distribute via MDM or direct download
```

### Over-the-Air Updates

**CodePush Integration**
```typescript
import codePush from 'react-native-code-push';

const App: React.FC = () => {
  useEffect(() => {
    codePush.sync({
      updateDialog: {
        title: 'Update Available',
        optionalUpdateMessage: 'An update is available. Would you like to install it?',
        optionalInstallButtonLabel: 'Install',
        optionalIgnoreButtonLabel: 'Later',
      },
      installMode: codePush.InstallMode.ON_NEXT_RESTART,
    });
  }, []);

  return <MainNavigator />;
};

export default codePush({
  checkFrequency: codePush.CheckFrequency.ON_APP_START,
  installMode: codePush.InstallMode.ON_NEXT_RESTART,
})(App);
```

## Troubleshooting

### Common Issues

**Build Errors**
```bash
# Clear React Native cache
npx react-native start --reset-cache

# Clean Android build
cd android && ./gradlew clean && cd ..

# Clean iOS build (macOS only)
cd ios && xcodebuild clean && cd ..

# Reinstall dependencies
rm -rf node_modules && npm install
```

**Database Issues**
```typescript
// Reset local database
const resetDatabase = async () => {
  await SQLite.deleteDatabase({ name: 'odk_mcp_mobile.db' });
  await initializeDatabase();
};
```

**Sync Problems**
```typescript
// Force sync reset
const resetSync = async () => {
  await AsyncStorage.removeItem('lastSyncTime');
  await SyncService.fullSync();
};
```

### Performance Issues

**Memory Leaks**
- Use React DevTools Profiler to identify memory leaks
- Implement proper cleanup in useEffect hooks
- Optimize image loading and caching
- Monitor memory usage with Flipper

**Slow Performance**
- Enable Hermes JavaScript engine
- Optimize database queries with proper indexing
- Implement lazy loading for large lists
- Use FlatList for better performance with large datasets

### Debug Tools

**React Native Debugger**
```bash
# Install React Native Debugger
npm install -g react-native-debugger

# Start debugger
react-native-debugger
```

**Flipper Integration**
```typescript
// Add Flipper plugins for debugging
import { logger } from 'flipper';

logger.info('Debug message', { data: someData });
```

## Contributing

We welcome contributions to the Enhanced ODK MCP Mobile Application! Please see the main project [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

### Development Guidelines

**Code Style**
- Follow React Native and TypeScript best practices
- Use ESLint and Prettier for code formatting
- Write comprehensive unit and integration tests
- Follow the established project structure

**Pull Request Process**
1. Create feature branch from main
2. Implement changes with tests
3. Update documentation as needed
4. Submit pull request with detailed description
5. Address review feedback promptly

## License

This mobile application is part of the Enhanced ODK MCP System and is licensed under the MIT License. See the main project [LICENSE](../../LICENSE) file for details.

## Support

For technical support, bug reports, or feature requests:

- **GitHub Issues**: https://github.com/opporsuryansh94/enhanced-odk-mcp-system/issues
- **Email**: mobile-support@odk-mcp.com
- **Documentation**: https://docs.odk-mcp.com/mobile
- **Community**: https://community.odk-mcp.com

