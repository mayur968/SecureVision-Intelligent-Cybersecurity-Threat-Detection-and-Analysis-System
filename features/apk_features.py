"""APK feature extraction for malware detection (static analysis only)."""

from pathlib import Path
from typing import Dict, Optional
import zipfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import logger


class APKFeatureExtractor:
    """Extract features from APK files using safe static analysis."""
    
    # Dangerous Android permissions
    DANGEROUS_PERMISSIONS = {
        'READ_SMS', 'RECEIVE_SMS', 'SEND_SMS', 'READ_CONTACTS',
        'WRITE_CONTACTS', 'READ_CALL_LOG', 'WRITE_CALL_LOG',
        'CAMERA', 'RECORD_AUDIO', 'ACCESS_FINE_LOCATION',
        'ACCESS_COARSE_LOCATION', 'READ_PHONE_STATE', 'CALL_PHONE',
        'READ_EXTERNAL_STORAGE', 'WRITE_EXTERNAL_STORAGE',
        'INSTALL_PACKAGES', 'DELETE_PACKAGES', 'WRITE_SETTINGS',
        'SYSTEM_ALERT_WINDOW', 'REQUEST_INSTALL_PACKAGES'
    }
    
    def __init__(self):
        """Initialize feature extractor."""
        self.androguard_available = False
        
        # Try to import androguard
        try:
            from androguard.core.bytecodes.apk import APK
            self.APK = APK
            self.androguard_available = True
            logger.info("Androguard available for APK analysis")
        except ImportError:
            logger.warning("Androguard not available. APK analysis will use basic ZIP inspection only.")
            self.APK = None
    
    def extract_features(self, apk_path: Path) -> Dict:
        """
        Extract features from APK file.
        
        Args:
            apk_path: Path to APK file
            
        Returns:
            Dictionary of features
        """
        if self.androguard_available:
            return self._extract_with_androguard(apk_path)
        else:
            return self._extract_basic_features(apk_path)
    
    def _extract_with_androguard(self, apk_path: Path) -> Dict:
        """Extract features using Androguard library."""
        try:
            # Load APK (static analysis only, no execution)
            apk = self.APK(str(apk_path))
            
            # Extract permissions
            permissions = apk.get_permissions()
            permission_count = len(permissions)
            
            # Count dangerous permissions
            dangerous_count = sum(
                1 for perm in permissions 
                if any(dangerous in perm for dangerous in self.DANGEROUS_PERMISSIONS)
            )
            
            # Get components
            activities = apk.get_activities()
            services = apk.get_services()
            receivers = apk.get_receivers()
            providers = apk.get_providers()
            
            # Package info
            package_name = apk.get_package()
            app_name = apk.get_app_name()
            
            features = {
                'package_name': package_name,
                'app_name': app_name,
                'permission_count': permission_count,
                'dangerous_permission_count': dangerous_count,
                'activity_count': len(activities),
                'service_count': len(services),
                'receiver_count': len(receivers),
                'provider_count': len(providers),
                'component_count': len(activities) + len(services) + len(receivers) + len(providers),
                'permissions': list(permissions)[:20],  # Limit for display
                'has_dangerous_permissions': dangerous_count > 0,
                'analysis_method': 'androguard'
            }
            
            logger.info(f"APK features extracted using Androguard: {package_name}")
            return features
            
        except Exception as e:
            logger.error(f"Error extracting APK features with Androguard: {str(e)}")
            return self._extract_basic_features(apk_path)
    
    def _extract_basic_features(self, apk_path: Path) -> Dict:
        """
        Extract basic features using ZIP inspection.
        This is a fallback when Androguard is not available.
        """
        try:
            features = {
                'package_name': 'unknown',
                'app_name': apk_path.stem,
                'permission_count': 0,
                'dangerous_permission_count': 0,
                'activity_count': 0,
                'service_count': 0,
                'receiver_count': 0,
                'provider_count': 0,
                'component_count': 0,
                'permissions': [],
                'has_dangerous_permissions': False,
                'analysis_method': 'basic_zip',
                'file_count': 0,
                'dex_count': 0
            }
            
            # Inspect as ZIP archive
            with zipfile.ZipFile(apk_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                features['file_count'] = len(file_list)
                
                # Count DEX files
                dex_files = [f for f in file_list if f.endswith('.dex')]
                features['dex_count'] = len(dex_files)
                
                # Check for manifest
                if 'AndroidManifest.xml' in file_list:
                    features['has_manifest'] = True
                else:
                    features['has_manifest'] = False
                
                # Check for native libraries
                native_libs = [f for f in file_list if f.startswith('lib/')]
                features['has_native_libs'] = len(native_libs) > 0
                features['native_lib_count'] = len(native_libs)
            
            logger.info(f"APK basic features extracted: {apk_path.name}")
            return features
            
        except Exception as e:
            logger.error(f"Error extracting basic APK features: {str(e)}")
            return {
                'error': str(e),
                'analysis_method': 'failed',
                'permission_count': 0,
                'dangerous_permission_count': 0,
                'component_count': 0
            }
    
    def get_feature_vector(self, features: Dict) -> list:
        """
        Convert features to numerical vector for ML model.
        
        Args:
            features: Dictionary of extracted features
            
        Returns:
            List of numerical features
        """
        return [
            features.get('permission_count', 0),
            features.get('dangerous_permission_count', 0),
            features.get('activity_count', 0),
            features.get('service_count', 0),
            features.get('receiver_count', 0),
            features.get('provider_count', 0),
            features.get('component_count', 0),
            1 if features.get('has_dangerous_permissions', False) else 0,
            features.get('file_count', 0),
            features.get('dex_count', 0),
        ]
    
    def get_feature_names(self) -> list:
        """Get list of feature names."""
        return [
            'permission_count',
            'dangerous_permission_count',
            'activity_count',
            'service_count',
            'receiver_count',
            'provider_count',
            'component_count',
            'has_dangerous_permissions',
            'file_count',
            'dex_count'
        ]
