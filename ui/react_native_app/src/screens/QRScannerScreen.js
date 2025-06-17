/**
 * QR Code Scanner Screen for ODK MCP Mobile App
 * Provides QR code scanning for quick form access and data collection
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Alert,
  Vibration,
  Dimensions,
  TouchableOpacity,
  Modal,
  ScrollView
} from 'react-native';
import QRCodeScanner from 'react-native-qrcode-scanner';
import { RNCamera } from 'react-native-camera';
import { Button, Card, Title, Paragraph, IconButton } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation } from '@react-navigation/native';
import { check, request, PERMISSIONS, RESULTS } from 'react-native-permissions';
import { Platform } from 'react-native';

// Contexts
import { useAuth } from '../contexts/AuthContext';
import { useProject } from '../contexts/ProjectContext';
import { useOffline } from '../contexts/OfflineContext';

// Services
import { FormService } from '../services/FormService';
import { QRCodeService } from '../services/QRCodeService';

// Utils
import { showToast } from '../utils/toast';

const { width, height } = Dimensions.get('window');

const QRScannerScreen = () => {
  const navigation = useNavigation();
  const { user } = useAuth();
  const { currentProject } = useProject();
  const { isOnline, offlineData } = useOffline();

  const [hasPermission, setHasPermission] = useState(false);
  const [isScanning, setIsScanning] = useState(true);
  const [flashOn, setFlashOn] = useState(false);
  const [scannedData, setScannedData] = useState(null);
  const [showDataModal, setShowDataModal] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    checkCameraPermission();
  }, []);

  const checkCameraPermission = async () => {
    try {
      const permission = Platform.OS === 'ios' 
        ? PERMISSIONS.IOS.CAMERA 
        : PERMISSIONS.ANDROID.CAMERA;

      const result = await check(permission);
      
      if (result === RESULTS.GRANTED) {
        setHasPermission(true);
      } else if (result === RESULTS.DENIED) {
        const requestResult = await request(permission);
        setHasPermission(requestResult === RESULTS.GRANTED);
      } else {
        setHasPermission(false);
        Alert.alert(
          'Camera Permission Required',
          'Please enable camera permission in settings to scan QR codes.',
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Settings', onPress: () => Linking.openSettings() }
          ]
        );
      }
    } catch (error) {
      console.error('Permission check error:', error);
      setHasPermission(false);
    }
  };

  const onSuccess = async (e) => {
    if (!isScanning || isProcessing) return;

    setIsScanning(false);
    setIsProcessing(true);
    Vibration.vibrate(200);

    try {
      const qrData = e.data;
      console.log('QR Code scanned:', qrData);

      // Parse QR code data
      const parsedData = await QRCodeService.parseQRCode(qrData);
      
      if (parsedData.isValid) {
        setScannedData(parsedData);
        await handleQRCodeData(parsedData);
      } else {
        Alert.alert(
          'Invalid QR Code',
          'This QR code is not recognized by ODK MCP System.',
          [{ text: 'OK', onPress: () => setIsScanning(true) }]
        );
      }
    } catch (error) {
      console.error('QR code processing error:', error);
      Alert.alert(
        'Error',
        'Failed to process QR code. Please try again.',
        [{ text: 'OK', onPress: () => setIsScanning(true) }]
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleQRCodeData = async (data) => {
    try {
      switch (data.type) {
        case 'form_access':
          await handleFormAccess(data);
          break;
        case 'project_join':
          await handleProjectJoin(data);
          break;
        case 'data_collection':
          await handleDataCollection(data);
          break;
        case 'form_submission':
          await handleFormSubmission(data);
          break;
        case 'survey_link':
          await handleSurveyLink(data);
          break;
        default:
          setShowDataModal(true);
          break;
      }
    } catch (error) {
      console.error('QR code handling error:', error);
      showToast('Failed to process QR code data', 'error');
      setIsScanning(true);
    }
  };

  const handleFormAccess = async (data) => {
    try {
      const { formId, projectId } = data.payload;
      
      // Check if form exists locally
      let form = offlineData.forms.find(f => f.id === formId);
      
      if (!form && isOnline) {
        // Download form if not available locally
        showToast('Downloading form...', 'info');
        form = await FormService.downloadForm(formId);
      }
      
      if (form) {
        // Navigate to form filling screen
        navigation.navigate('FormFilling', {
          formId: form.id,
          projectId: projectId || currentProject?.id,
          source: 'qr_scan'
        });
      } else {
        Alert.alert(
          'Form Not Available',
          'This form is not available offline. Please connect to the internet and try again.',
          [{ text: 'OK', onPress: () => setIsScanning(true) }]
        );
      }
    } catch (error) {
      console.error('Form access error:', error);
      showToast('Failed to access form', 'error');
      setIsScanning(true);
    }
  };

  const handleProjectJoin = async (data) => {
    try {
      const { projectId, inviteCode } = data.payload;
      
      Alert.alert(
        'Join Project',
        `Do you want to join the project with invite code: ${inviteCode}?`,
        [
          { text: 'Cancel', onPress: () => setIsScanning(true) },
          {
            text: 'Join',
            onPress: async () => {
              try {
                if (isOnline) {
                  // Join project online
                  await ProjectService.joinProject(projectId, inviteCode);
                  showToast('Successfully joined project', 'success');
                  navigation.navigate('Projects');
                } else {
                  showToast('Internet connection required to join project', 'error');
                  setIsScanning(true);
                }
              } catch (error) {
                showToast('Failed to join project', 'error');
                setIsScanning(true);
              }
            }
          }
        ]
      );
    } catch (error) {
      console.error('Project join error:', error);
      showToast('Failed to process project invitation', 'error');
      setIsScanning(true);
    }
  };

  const handleDataCollection = async (data) => {
    try {
      const { formId, prefilledData } = data.payload;
      
      // Find form
      const form = offlineData.forms.find(f => f.id === formId);
      
      if (form) {
        // Navigate to form with prefilled data
        navigation.navigate('FormFilling', {
          formId: form.id,
          prefilledData,
          source: 'qr_scan'
        });
      } else {
        Alert.alert(
          'Form Not Found',
          'The form referenced in this QR code is not available.',
          [{ text: 'OK', onPress: () => setIsScanning(true) }]
        );
      }
    } catch (error) {
      console.error('Data collection error:', error);
      showToast('Failed to process data collection QR code', 'error');
      setIsScanning(true);
    }
  };

  const handleFormSubmission = async (data) => {
    try {
      const { submissionId, formId } = data.payload;
      
      // Navigate to submission view
      navigation.navigate('SubmissionView', {
        submissionId,
        formId,
        source: 'qr_scan'
      });
    } catch (error) {
      console.error('Form submission error:', error);
      showToast('Failed to view form submission', 'error');
      setIsScanning(true);
    }
  };

  const handleSurveyLink = async (data) => {
    try {
      const { url, title } = data.payload;
      
      Alert.alert(
        'Open Survey',
        `Do you want to open the survey: ${title}?`,
        [
          { text: 'Cancel', onPress: () => setIsScanning(true) },
          {
            text: 'Open',
            onPress: () => {
              navigation.navigate('WebView', {
                url,
                title,
                source: 'qr_scan'
              });
            }
          }
        ]
      );
    } catch (error) {
      console.error('Survey link error:', error);
      showToast('Failed to open survey link', 'error');
      setIsScanning(true);
    }
  };

  const toggleFlash = () => {
    setFlashOn(!flashOn);
  };

  const resetScanner = () => {
    setIsScanning(true);
    setScannedData(null);
    setShowDataModal(false);
  };

  const renderDataModal = () => (
    <Modal
      visible={showDataModal}
      animationType="slide"
      transparent={true}
      onRequestClose={() => setShowDataModal(false)}
    >
      <View style={styles.modalContainer}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Title>QR Code Data</Title>
            <IconButton
              icon="close"
              onPress={() => setShowDataModal(false)}
            />
          </View>
          
          <ScrollView style={styles.modalBody}>
            {scannedData && (
              <Card style={styles.dataCard}>
                <Card.Content>
                  <Title>Type: {scannedData.type}</Title>
                  <Paragraph>
                    Raw Data: {JSON.stringify(scannedData.payload, null, 2)}
                  </Paragraph>
                </Card.Content>
              </Card>
            )}
          </ScrollView>
          
          <View style={styles.modalFooter}>
            <Button
              mode="outlined"
              onPress={() => setShowDataModal(false)}
              style={styles.modalButton}
            >
              Close
            </Button>
            <Button
              mode="contained"
              onPress={resetScanner}
              style={styles.modalButton}
            >
              Scan Again
            </Button>
          </View>
        </View>
      </View>
    </Modal>
  );

  if (!hasPermission) {
    return (
      <View style={styles.permissionContainer}>
        <Icon name="camera-alt" size={80} color="#ccc" />
        <Text style={styles.permissionText}>
          Camera permission is required to scan QR codes
        </Text>
        <Button
          mode="contained"
          onPress={checkCameraPermission}
          style={styles.permissionButton}
        >
          Grant Permission
        </Button>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <QRCodeScanner
        onRead={onSuccess}
        flashMode={flashOn ? RNCamera.Constants.FlashMode.torch : RNCamera.Constants.FlashMode.off}
        reactivate={isScanning}
        reactivateTimeout={2000}
        showMarker={true}
        markerStyle={styles.marker}
        cameraStyle={styles.camera}
        topContent={
          <View style={styles.topContent}>
            <Text style={styles.centerText}>
              Scan QR code to access forms, join projects, or collect data
            </Text>
          </View>
        }
        bottomContent={
          <View style={styles.bottomContent}>
            <TouchableOpacity
              style={styles.buttonTouchable}
              onPress={toggleFlash}
            >
              <Icon
                name={flashOn ? "flash-off" : "flash-on"}
                size={30}
                color="#fff"
              />
              <Text style={styles.buttonText}>
                {flashOn ? "Flash Off" : "Flash On"}
              </Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.buttonTouchable}
              onPress={() => navigation.goBack()}
            >
              <Icon name="arrow-back" size={30} color="#fff" />
              <Text style={styles.buttonText}>Back</Text>
            </TouchableOpacity>
          </View>
        }
      />
      
      {isProcessing && (
        <View style={styles.processingOverlay}>
          <Text style={styles.processingText}>Processing QR Code...</Text>
        </View>
      )}
      
      {renderDataModal()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  permissionContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  permissionText: {
    fontSize: 16,
    textAlign: 'center',
    marginVertical: 20,
    color: '#666',
  },
  permissionButton: {
    marginTop: 20,
  },
  camera: {
    height: height,
  },
  marker: {
    borderColor: '#fff',
    borderWidth: 2,
    borderRadius: 10,
  },
  topContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  centerText: {
    fontSize: 18,
    color: '#fff',
    textAlign: 'center',
    fontWeight: '600',
  },
  bottomContent: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 20,
    paddingHorizontal: 40,
  },
  buttonTouchable: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 15,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 10,
    minWidth: 80,
  },
  buttonText: {
    color: '#fff',
    fontSize: 12,
    marginTop: 5,
    fontWeight: '500',
  },
  processingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  processingText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 10,
    width: width * 0.9,
    maxHeight: height * 0.8,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  modalBody: {
    padding: 20,
    maxHeight: height * 0.5,
  },
  dataCard: {
    marginBottom: 10,
  },
  modalFooter: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  modalButton: {
    flex: 1,
    marginHorizontal: 10,
  },
});

export default QRScannerScreen;

