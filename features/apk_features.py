"""APK feature extraction for malware detection (static analysis only)."""

from pathlib import Path
from typing import Dict, Optional, List, Set
import zipfile
import sys
import hashlib
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import logger


class APKFeatureExtractor:
    """Extract features from APK files using safe static analysis."""
    
    # Dangerous Android permissions (expanded)
    DANGEROUS_PERMISSIONS = {
        'READ_SMS', 'RECEIVE_SMS', 'SEND_SMS', 'RECEIVE_MMS', 'WRITE_SMS',
        'READ_CONTACTS', 'WRITE_CONTACTS', 'GET_ACCOUNTS',
        'READ_CALL_LOG', 'WRITE_CALL_LOG', 'PROCESS_OUTGOING_CALLS',
        'CAMERA', 'RECORD_AUDIO',
        'ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION', 'ACCESS_BACKGROUND_LOCATION',
        'READ_PHONE_STATE', 'CALL_PHONE', 'READ_PHONE_NUMBERS',
        'READ_EXTERNAL_STORAGE', 'WRITE_EXTERNAL_STORAGE', 'MANAGE_EXTERNAL_STORAGE',
        'INSTALL_PACKAGES', 'DELETE_PACKAGES', 'REQUEST_INSTALL_PACKAGES',
        'WRITE_SETTINGS', 'SYSTEM_ALERT_WINDOW', 'BIND_DEVICE_ADMIN',
        'BIND_ACCESSIBILITY_SERVICE', 'BIND_NOTIFICATION_LISTENER_SERVICE',
        'READ_CALENDAR', 'WRITE_CALENDAR', 'BODY_SENSORS',
        'BLUETOOTH_ADMIN', 'BLUETOOTH_PRIVILEGED', 'CHANGE_WIFI_STATE',
        'INTERNET', 'ACCESS_NETWORK_STATE', 'WAKE_LOCK'
    }
    
    # Suspicious API calls indicating malicious behavior
    SUSPICIOUS_APIS = {
        'reflection': ['java.lang.reflect', 'getDeclaredMethod', 'invoke'],
        'dynamic_code': ['DexClassLoader', 'PathClassLoader', 'dalvik.system'],
        'sms_interception': ['SmsManager', 'sendTextMessage', 'sendMultipartTextMessage'],
        'call_interception': ['PhoneStateListener', 'onCallStateChanged'],
        'crypto': ['Cipher', 'MessageDigest', 'SecretKey', 'encrypt', 'decrypt'],
        'root_detection': ['/system/bin/su', '/system/xbin/su', 'RootTools'],
        'emulator_detection': ['TelephonyManager.getDeviceId', 'Build.FINGERPRINT'],
        'runtime_exec': ['Runtime.exec', 'ProcessBuilder'],
        'native_code': ['System.loadLibrary', 'JNI'],
        'obfuscation': ['ProGuard', 'DexGuard', 'Base64.decode']
    }
    
    def __init__(self):
        """Initialize feature extractor."""
        self.androguard_available = False
        
        # Try to import androguard
        try:
            from androguard.core.apk import APK
            from androguard.core.dex import DEX
            from androguard.core.analysis.analysis import Analysis
            
            self.APK = APK
            self.DEX = DEX
            self.Analysis = Analysis
            self.androguard_available = True
            logger.info("Androguard available for advanced APK analysis")
        except ImportError as e:
            logger.warning(f"Androguard not available ({e}). APK analysis will use basic ZIP inspection only.")
            self.APK = None
            self.DEX = None
            self.Analysis = None
    
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
        """Extract comprehensive features using Androguard library."""
        try:
            # Load APK (static analysis only, no execution)
            apk = self.APK(str(apk_path))
            
            # Basic APK info
            package_name = apk.get_package()
            app_name = apk.get_app_name()
            version_code = apk.get_androidversion_code()
            min_sdk = apk.get_min_sdk_version()
            target_sdk = apk.get_target_sdk_version()
            
            # 1. PERMISSIONS ANALYSIS
            permissions = apk.get_permissions()
            permission_count = len(permissions)
            
            dangerous_count = sum(
                1 for perm in permissions 
                if any(dangerous in perm for dangerous in self.DANGEROUS_PERMISSIONS)
            )
            dangerous_ratio = dangerous_count / max(permission_count, 1)
            
            # Check for specific dangerous permission combinations
            has_sms_perms = any('SMS' in p for p in permissions)
            has_phone_perms = any('CALL' in p or 'PHONE' in p for p in permissions)
            has_location_perms = any('LOCATION' in p for p in permissions)
            has_storage_perms = any('STORAGE' in p for p in permissions)
            has_admin_perms = any('ADMIN' in p or 'DEVICE_ADMIN' in p for p in permissions)
            has_internet = 'android.permission.INTERNET' in permissions
            
            # 2. COMPONENTS ANALYSIS
            activities = apk.get_activities()
            services = apk.get_services()
            receivers = apk.get_receivers()
            providers = apk.get_providers()
            
            component_count = len(activities) + len(services) + len(receivers) + len(providers)
            
            # Check for suspicious components
            exported_activities = sum(1 for a in activities if apk.get_attribute_value(a, 'exported') == 'true')
            exported_services = sum(1 for s in services if apk.get_attribute_value(s, 'exported') == 'true')
            exported_receivers = sum(1 for r in receivers if apk.get_attribute_value(r, 'exported') == 'true')
            
            # 3. INTENT FILTERS & BROADCAST RECEIVERS
            intent_filters = []
            try:
                for receiver in receivers:
                    filters = apk.get_intent_filters('receiver', receiver)
                    if filters:
                        intent_filters.extend(filters)
            except Exception as e:
                logger.debug(f"Error extracting intent filters: {e}")
            
            # Check for suspicious receivers (SMS, boot, etc.)
            suspicious_receivers = []
            for receiver in receivers:
                receiver_lower = receiver.lower()
                if any(keyword in receiver_lower for keyword in ['sms', 'boot', 'alarm', 'phone']):
                    suspicious_receivers.append(receiver)
            
            # 4. DEX ANALYSIS - API CALLS
            dex_files = apk.get_all_dex()
            dex_count = len(dex_files)
            
            api_calls = self._analyze_api_calls(apk, dex_files)
            
            # 5. CERTIFICATE/SIGNING ANALYSIS
            cert_info = self._analyze_certificate(apk)
            
            # 6. NATIVE LIBRARIES
            native_libs = []
            for lib_dir in ['lib/armeabi', 'lib/armeabi-v7a', 'lib/arm64-v8a', 'lib/x86', 'lib/x86_64']:
                libs = apk.get_files_types().get(lib_dir, [])
                native_libs.extend(libs)
            has_native = len(native_libs) > 0
            
            # 7. FILE ANALYSIS
            file_count = len(apk.get_files())
            
            # Check for obfuscation indicators
            is_obfuscated = self._check_obfuscation(apk, package_name)
            
            # 8. MANIFEST ANOMALIES
            manifest_anomalies = self._check_manifest_anomalies(apk)
            
            # 9. STRING ANALYSIS
            suspicious_strings = self._analyze_strings(apk)
            
            features = {
                # Basic info
                'package_name': package_name,
                'app_name': app_name,
                'version_code': version_code if version_code else '0',
                'min_sdk': min_sdk if min_sdk else '0',
                'target_sdk': target_sdk if target_sdk else '0',
                
                # Permissions (14 features)
                'permission_count': permission_count,
                'dangerous_permission_count': dangerous_count,
                'dangerous_permission_ratio': round(dangerous_ratio, 3),
                'has_sms_permissions': 1 if has_sms_perms else 0,
                'has_phone_permissions': 1 if has_phone_perms else 0,
                'has_location_permissions': 1 if has_location_perms else 0,
                'has_storage_permissions': 1 if has_storage_perms else 0,
                'has_admin_permissions': 1 if has_admin_perms else 0,
                'has_internet': 1 if has_internet else 0,
                'permission_entropy': self._calculate_permission_entropy(permissions),
                
                # Components (10 features)
                'activity_count': len(activities),
                'service_count': len(services),
                'receiver_count': len(receivers),
                'provider_count': len(providers),
                'component_count': component_count,
                'exported_activity_count': exported_activities,
                'exported_service_count': exported_services,
                'exported_receiver_count': exported_receivers,
                'suspicious_receiver_count': len(suspicious_receivers),
                'intent_filter_count': len(intent_filters),
                
                # DEX & Code analysis (8 features)
                'dex_count': dex_count,
                'has_reflection_api': api_calls['reflection'],
                'has_dynamic_code_loading': api_calls['dynamic_code'],
                'has_crypto_api': api_calls['crypto'],
                'has_runtime_exec': api_calls['runtime_exec'],
                'has_native_code_loading': api_calls['native_code'],
                'suspicious_api_count': api_calls['total_suspicious'],
                'api_diversity_score': api_calls['diversity'],
                
                # Certificate (4 features)
                'cert_is_debug': cert_info['is_debug'],
                'cert_is_valid': cert_info['is_valid'],
                'cert_validity_days': cert_info['validity_days'],
                'cert_self_signed': cert_info['self_signed'],
                
                # Files & obfuscation (5 features)
                'file_count': file_count,
                'has_native_libs': 1 if has_native else 0,
                'native_lib_count': len(native_libs),
                'is_obfuscated': 1 if is_obfuscated else 0,
                'manifest_anomaly_count': len(manifest_anomalies),
                
                # Strings (3 features)
                'suspicious_string_count': suspicious_strings['count'],
                'has_url_strings': 1 if suspicious_strings['has_urls'] else 0,
                'has_ip_strings': 1 if suspicious_strings['has_ips'] else 0,
                
                # Risk indicators
                'permissions': list(permissions)[:30],  # Limit for display
                'suspicious_receivers': suspicious_receivers,
                'manifest_anomalies': manifest_anomalies,
                'has_dangerous_permissions': dangerous_count > 0,
                'analysis_method': 'androguard_advanced'
            }
            
            logger.info(f"Advanced APK features extracted: {package_name} ({len(features)} features)")
            return features
            
        except Exception as e:
            logger.error(f"Error extracting APK features with Androguard: {str(e)}")
            return self._extract_basic_features(apk_path)
    
    
    def _analyze_api_calls(self, apk, dex_files: List) -> Dict:
        """Analyze suspicious API calls in DEX files."""
        api_stats = {
            'reflection': 0,
            'dynamic_code': 0,
            'sms_interception': 0,
            'call_interception': 0,
            'crypto': 0,
            'runtime_exec': 0,
            'native_code': 0,
            'total_suspicious': 0,
            'diversity': 0
        }
        
        try:
            found_categories = set()
            
            # Analyze main DEX
            for dex in dex_files[:3]:  # Limit to first 3 DEX files for performance
                try:
                    dex_vm = self.DEX(dex)
                    
                    # Check for suspicious API patterns
                    for cls in dex_vm.get_classes():
                        cls_name = cls.get_name()
                        
                        for category, patterns in self.SUSPICIOUS_APIS.items():
                            if any(pattern in cls_name for pattern in patterns):
                                api_stats[category] += 1
                                found_categories.add(category)
                        
                        # Check methods
                        for method in cls.get_methods():
                            method_name = method.get_name()
                            for category, patterns in self.SUSPICIOUS_APIS.items():
                                if any(pattern in method_name for pattern in patterns):
                                    api_stats[category] += 1
                                    found_categories.add(category)
                except Exception as e:
                    logger.debug(f"Error analyzing DEX: {e}")
                    continue
            
            api_stats['total_suspicious'] = sum([
                api_stats['reflection'],
                api_stats['dynamic_code'],
                api_stats['crypto'],
                api_stats['runtime_exec'],
                api_stats['native_code']
            ])
            
            # Diversity score: how many different suspicious API categories found
            api_stats['diversity'] = len(found_categories)
            
        except Exception as e:
            logger.debug(f"Error in API analysis: {e}")
        
        return api_stats
    
    def _analyze_certificate(self, apk) -> Dict:
        """Analyze APK certificate/signing information."""
        cert_info = {
            'is_debug': 0,
            'is_valid': 1,
            'validity_days': 365,
            'self_signed': 0
        }
        
        try:
            # Get certificate
            cert = apk.get_certificate(apk.get_signature_name())
            
            if cert:
                # Check if debug certificate
                subject = cert.subject
                if subject and ('debug' in str(subject).lower() or 'android' in str(subject).lower()):
                    cert_info['is_debug'] = 1
                
                # Check validity period
                if hasattr(cert, 'not_valid_before') and hasattr(cert, 'not_valid_after'):
                    validity = (cert.not_valid_after - cert.not_valid_before).days
                    cert_info['validity_days'] = validity
                    
                    # Very short validity might indicate malware
                    if validity < 30:
                        cert_info['is_valid'] = 0
                
                # Check if self-signed (issuer == subject)
                if hasattr(cert, 'issuer') and hasattr(cert, 'subject'):
                    if cert.issuer == cert.subject:
                        cert_info['self_signed'] = 1
        
        except Exception as e:
            logger.debug(f"Error analyzing certificate: {e}")
        
        return cert_info
    
    def _check_obfuscation(self, apk, package_name: str) -> bool:
        """Check for code obfuscation indicators."""
        try:
            # Check for ProGuard/DexGuard patterns
            activities = apk.get_activities()
            services = apk.get_services()
            
            # Count short/single-letter class names (obfuscation indicator)
            short_names = 0
            all_components = activities + services
            
            for component in all_components[:20]:  # Sample
                class_name = component.split('.')[-1]
                if len(class_name) <= 2:  # Single or double letter class names
                    short_names += 1
            
            # If >30% have short names, likely obfuscated
            if all_components and (short_names / len(all_components[:20])) > 0.3:
                return True
            
            # Check for ProGuard mapping file
            if 'proguard-map.txt' in apk.get_files():
                return True
        
        except Exception as e:
            logger.debug(f"Error checking obfuscation: {e}")
        
        return False
    
    def _check_manifest_anomalies(self, apk) -> List[str]:
        """Check for manifest anomalies that might indicate malware."""
        anomalies = []
        
        try:
            # Check for debuggable flag in release
            if apk.get_attribute_value('application', 'debuggable') == 'true':
                anomalies.append('Debuggable flag enabled')
            
            # Check for backup allowed
            if apk.get_attribute_value('application', 'allowBackup') == 'true':
                anomalies.append('Backup allowed (data theft risk)')
            
            # Check for clear text traffic allowed
            if apk.get_attribute_value('application', 'usesCleartextTraffic') == 'true':
                anomalies.append('Cleartext traffic allowed')
            
            # Check target SDK - old SDKs bypass security
            target_sdk = apk.get_target_sdk_version()
            if target_sdk and int(target_sdk) < 23:  # < Android 6.0
                anomalies.append(f'Old target SDK ({target_sdk}) - security bypass risk')
        
        except Exception as e:
            logger.debug(f"Error checking manifest anomalies: {e}")
        
        return anomalies
    
    def _analyze_strings(self, apk) -> Dict:
        """Analyze strings for suspicious patterns."""
        suspicious_info = {
            'count': 0,
            'has_urls': False,
            'has_ips': False
        }
        
        try:
            import re
            
            # Get strings from DEX files (sample only for performance)
            dex_files = apk.get_all_dex()
            
            url_pattern = re.compile(r'https?://[^\s]+')
            ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
            
            suspicious_keywords = ['c2', 'botnet', 'exploit', 'payload', 'shell', 'root', 'su']
            
            for dex in dex_files[:2]:  # Sample first 2 DEX files
                try:
                    dex_vm = self.DEX(dex)
                    strings = dex_vm.get_strings()
                    
                    for s in list(strings)[:1000]:  # Sample 1000 strings
                        s_lower = s.lower()
                        
                        # Check for URLs
                        if url_pattern.search(s):
                            suspicious_info['has_urls'] = True
                        
                        # Check for IP addresses
                        if ip_pattern.search(s):
                            suspicious_info['has_ips'] = True
                        
                        # Check for suspicious keywords
                        if any(keyword in s_lower for keyword in suspicious_keywords):
                            suspicious_info['count'] += 1
                
                except Exception as e:
                    logger.debug(f"Error analyzing strings: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error in string analysis: {e}")
        
        return suspicious_info
    
    def _calculate_permission_entropy(self, permissions: List[str]) -> float:
        """Calculate entropy of permission distribution (diversity metric)."""
        if not permissions:
            return 0.0
        
        try:
            import math
            from collections import Counter
            
            # Group permissions by category prefix
            categories = [p.split('.')[-1].split('_')[0] for p in permissions]
            freq = Counter(categories)
            
            # Calculate Shannon entropy
            total = sum(freq.values())
            entropy = -sum((count/total) * math.log2(count/total) for count in freq.values())
            
            return round(entropy, 3)
        
        except Exception as e:
            logger.debug(f"Error calculating entropy: {e}")
            return 0.0
    
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
            List of numerical features (44 features total)
        """
        return [
            # Permissions (10 features)
            features.get('permission_count', 0),
            features.get('dangerous_permission_count', 0),
            features.get('dangerous_permission_ratio', 0.0),
            features.get('has_sms_permissions', 0),
            features.get('has_phone_permissions', 0),
            features.get('has_location_permissions', 0),
            features.get('has_storage_permissions', 0),
            features.get('has_admin_permissions', 0),
            features.get('has_internet', 0),
            features.get('permission_entropy', 0.0),
            
            # Components (10 features)
            features.get('activity_count', 0),
            features.get('service_count', 0),
            features.get('receiver_count', 0),
            features.get('provider_count', 0),
            features.get('component_count', 0),
            features.get('exported_activity_count', 0),
            features.get('exported_service_count', 0),
            features.get('exported_receiver_count', 0),
            features.get('suspicious_receiver_count', 0),
            features.get('intent_filter_count', 0),
            
            # DEX & API calls (8 features)
            features.get('dex_count', 0),
            features.get('has_reflection_api', 0),
            features.get('has_dynamic_code_loading', 0),
            features.get('has_crypto_api', 0),
            features.get('has_runtime_exec', 0),
            features.get('has_native_code_loading', 0),
            features.get('suspicious_api_count', 0),
            features.get('api_diversity_score', 0),
            
            # Certificate (4 features)
            features.get('cert_is_debug', 0),
            features.get('cert_is_valid', 1),
            features.get('cert_validity_days', 365) / 365.0,  # Normalize
            features.get('cert_self_signed', 0),
            
            # Files & obfuscation (5 features)
            features.get('file_count', 0) / 1000.0,  # Normalize
            features.get('has_native_libs', 0),
            features.get('native_lib_count', 0),
            features.get('is_obfuscated', 0),
            features.get('manifest_anomaly_count', 0),
            
            # Strings (3 features)
            features.get('suspicious_string_count', 0),
            features.get('has_url_strings', 0),
            features.get('has_ip_strings', 0),
            
            # Legacy features for compatibility (4 features)
            1 if features.get('has_dangerous_permissions', False) else 0,
            features.get('file_count', 0) / 1000.0,
            features.get('dex_count', 0),
            features.get('has_native_libs', 0),
        ]
    
    def get_feature_names(self) -> list:
        """Get list of feature names (44 features)."""
        return [
            # Permissions
            'permission_count',
            'dangerous_permission_count',
            'dangerous_permission_ratio',
            'has_sms_permissions',
            'has_phone_permissions',
            'has_location_permissions',
            'has_storage_permissions',
            'has_admin_permissions',
            'has_internet',
            'permission_entropy',
            
            # Components
            'activity_count',
            'service_count',
            'receiver_count',
            'provider_count',
            'component_count',
            'exported_activity_count',
            'exported_service_count',
            'exported_receiver_count',
            'suspicious_receiver_count',
            'intent_filter_count',
            
            # DEX & API
            'dex_count',
            'has_reflection_api',
            'has_dynamic_code_loading',
            'has_crypto_api',
            'has_runtime_exec',
            'has_native_code_loading',
            'suspicious_api_count',
            'api_diversity_score',
            
            # Certificate
            'cert_is_debug',
            'cert_is_valid',
            'cert_validity_days_normalized',
            'cert_self_signed',
            
            # Files & obfuscation
            'file_count_normalized',
            'has_native_libs',
            'native_lib_count',
            'is_obfuscated',
            'manifest_anomaly_count',
            
            # Strings
            'suspicious_string_count',
            'has_url_strings',
            'has_ip_strings',
            
            # Legacy compatibility
            'has_dangerous_permissions',
            'file_count_normalized_compat',
            'dex_count_compat',
            'has_native_libs_compat',
        ]
