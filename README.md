# SecureVision - Intelligent Cybersecurity Threat Detection System

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Phase](https://img.shields.io/badge/Phase-1%20(30%25)-orange.svg)

**SecureVision** is a modular cybersecurity platform designed to detect and analyze various types of threats including phishing URLs, malicious messages, and Android APK malware. This repository contains the Phase 1 (30%) implementation, establishing a solid foundation for future enhancements.

## 🎯 Project Overview

SecureVision is a final-year engineering project that demonstrates practical application of machine learning in cybersecurity. The system provides:

- **URL Phishing Detection**: Analyzes URLs for phishing characteristics
- **Email/SMS Phishing Detection**: Identifies suspicious messages using NLP
- **APK Malware Detection**: Static analysis of Android applications
- **Threat Explanation**: Human-readable explanations for detections
- **Risk Scoring**: 0-100 risk scores with LOW/MEDIUM/HIGH classification
- **Security Recommendations**: Actionable guidance for users
- **Web Dashboard**: Interactive interface with visualizations

## ⚠️ Important Notes

### Current Implementation (Phase 1 - 30%)

This is the **foundational phase** of SecureVision. The system is functional and demonstrates core concepts, but should **NOT** be used as a production security tool without significant enhancements.

### Limitations

- **Demo Datasets**: Models are trained on small sample datasets (50-100 samples) for development purposes only
- **Static Analysis Only**: APK analysis does not execute applications
- **No Real-time URL Crawling**: URLs are analyzed by pattern matching, not by visiting them
- **Basic ML Models**: Uses traditional ML (Logistic Regression, Random Forest) rather than deep learning
- **No Authentication**: Single-user system without access control
- **Local Deployment**: Not configured for production cloud deployment

### Security Disclaimers

- ⚠️ **APK files are NOT executed** - analysis is purely static
- ⚠️ **URLs are NOT automatically visited** - analysis is pattern-based
- ⚠️ **Results are probabilistic** - not 100% accurate
- ⚠️ **Use responsible language** - predictions are "potentially malicious" not "definitely malicious"

## 🏗️ Architecture

```
SecureVision
├── Web Dashboard (Flask)
│   ├── URL Scanner
│   ├── Message Scanner
│   └── APK Scanner
│
├── Detection Modules
│   ├── URL Detector (20 features + ML)
│   ├── Message Detector (TF-IDF + ML)
│   └── APK Detector (Static analysis + ML)
│
├── Analysis Engine
│   ├── Risk Scorer
│   ├── Threat Explainer
│   └── Recommendation Engine
│
└── Database (SQLite)
    └── Scan History
```

## 📁 Project Structure

```
SecureVision/
│
├── app.py                      # Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── data/                       # Sample datasets
│   ├── urls/
│   │   └── sample_urls.csv
│   ├── messages/
│   │   └── sample_messages.csv
│   └── apk/
│       └── sample_apk_features.csv
│
├── models/                     # Trained ML models (generated)
│   ├── url_model.pkl
│   ├── message_model.pkl
│   └── apk_model.pkl
│
├── preprocessing/              # Data preprocessing
│   ├── url_preprocessing.py
│   ├── text_preprocessing.py
│   └── apk_preprocessing.py
│
├── features/                   # Feature extraction
│   ├── url_features.py
│   ├── text_features.py
│   └── apk_features.py
│
├── detection/                  # Detection services
│   ├── url_detector.py
│   ├── message_detector.py
│   └── apk_detector.py
│
├── training/                   # Model training scripts
│   ├── train_url_model.py
│   ├── train_message_model.py
│   └── train_apk_model.py
│
├── explanation/                # Threat explanation
│   ├── risk_score.py
│   ├── threat_explainer.py
│   └── recommendations.py
│
├── database/                   # Database models
│   └── models.py
│
├── utils/                      # Utility functions
│   ├── logger.py
│   ├── validators.py
│   └── file_security.py
│
├── templates/                  # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── url_scanner.html
│   ├── message_scanner.html
│   ├── apk_scanner.html
│   └── history.html
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── dashboard.js
│       └── scanner.js
│
└── tests/                      # Unit tests
    ├── test_url_detector.py
    ├── test_message_detector.py
    └── test_apk_detector.py
```

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Step 1: Clone Repository

```bash
cd SecureVision
```

### Step 2: Create Virtual Environment

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

**Note:** If `androguard` installation fails (optional dependency), the system will still work with basic APK analysis.

### Step 4: Train Models

Train the machine learning models using the provided sample datasets:

```powershell
# Train URL phishing detector
python training/train_url_model.py

# Train message phishing detector
python training/train_message_model.py

# Train APK malware detector
python training/train_apk_model.py
```

Each training script will:
- Load the sample dataset
- Extract features
- Train multiple models (Logistic Regression, Random Forest)
- Compare performance metrics
- Save the best model

### Step 5: Run Application

```powershell
python app.py
```

The application will be available at: **http://localhost:5000**

## 📊 Using SecureVision

### Dashboard

Navigate to `http://localhost:5000` to access the dashboard showing:
- Total scans performed
- Threats detected
- Safe results
- Detection rate
- Charts and recent scan history

### URL Scanner

1. Navigate to **URL Scanner**
2. Enter a URL (e.g., `http://secure-login-verify.com`)
3. Click **Scan URL**
4. View results including:
   - Prediction (SAFE/PHISHING)
   - Confidence score
   - Risk level
   - Explanation
   - Security recommendations

### Message Scanner

1. Navigate to **Message Scanner**
2. Paste an email or SMS message
3. Click **Analyze Message**
4. View detected indicators and recommendations

### APK Scanner

1. Navigate to **APK Scanner**
2. Upload an APK file (max 50MB)
3. Click **Analyze APK**
4. View analysis results

**Important:** APK files are analyzed using static analysis only. The application is **NOT executed**.

### History

View all previous scans with filtering options by:
- Scan type (URL/MESSAGE/APK)
- Prediction result
- Risk level

## 🔬 Machine Learning Models

### URL Phishing Detection

**Features (20):**
- URL length, domain length
- Character counts (dots, hyphens, digits, special chars)
- HTTPS presence
- IP address detection
- Subdomain count
- Suspicious keywords (login, verify, account, etc.)

**Models:** Logistic Regression, Random Forest  
**Training Data:** 100 URLs (50 legitimate, 50 phishing)

### Message Phishing Detection

**Features:**
- TF-IDF vectorization (1000 features, unigrams + bigrams)
- Text characteristics (21 features)
- Keyword categories: urgent, financial, security, threat, request

**Models:** Logistic Regression, Random Forest  
**Training Data:** 100 messages (50 safe, 50 phishing)

### APK Malware Detection

**Features (10):**
- Permission counts
- Dangerous permission count
- Component counts (activities, services, receivers, providers)
- DEX file count
- File count

**Models:** Logistic Regression, Random Forest  
**Training Data:** 50 APK feature samples (25 safe, 25 malicious)

**Analysis Method:**
- Androguard (if available) for full static analysis
- ZIP inspection fallback for basic features

## 🧪 Running Tests

```powershell
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_url_detector.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## 🔧 Configuration

Configuration settings are in `config.py`:

```python
# Database
SQLALCHEMY_DATABASE_URI = 'sqlite:///securevision.db'

# File Upload
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
UPLOAD_FOLDER = 'uploads'

# Model Paths
URL_MODEL_PATH = 'models/url_model.pkl'
MESSAGE_MODEL_PATH = 'models/message_model.pkl'
APK_MODEL_PATH = 'models/apk_model.pkl'
```

## 📡 API Endpoints

### Scan URL
```http
POST /api/scan/url
Content-Type: application/json

{
  "url": "https://example.com"
}
```

### Scan Message
```http
POST /api/scan/message
Content-Type: application/json

{
  "message": "Your message text here..."
}
```

### Scan APK
```http
POST /api/scan/apk
Content-Type: multipart/form-data

file: <apk_file>
```

### Get History
```http
GET /api/history?limit=50
```

### Get Statistics
```http
GET /api/statistics
```

## 📈 Dataset Format

### URLs (CSV)
```csv
url,label
https://www.google.com,0
http://phishing-site.com/login,1
```

### Messages (CSV)
```csv
message,label
"Hello, how are you?",0
"URGENT: Your account will be suspended",1
```

### APK Features (CSV)
```csv
permission_count,dangerous_permission_count,...,label
10,2,...,0
35,15,...,1
```

## 🔒 Security Best Practices

1. **File Upload Security:**
   - Extension validation (.apk only)
   - File size limits (50MB)
   - Secure random filenames
   - Temporary file cleanup

2. **Input Validation:**
   - URL format validation
   - Message length limits
   - SQL injection prevention (parameterized queries)

3. **Safe Analysis:**
   - No APK execution
   - No automatic URL visiting
   - Static analysis only

4. **Error Handling:**
   - User-friendly error messages
   - Technical errors logged securely
   - No stack trace exposure

## 🚧 Future Enhancements (Phase 2+)

### Planned Features

- **Enhanced ML Models:** Deep learning, BERT, ensemble methods
- **Larger Datasets:** Real-world datasets with 10,000+ samples
- **Dynamic APK Analysis:** Sandbox execution in isolated environment
- **Real-time URL Checking:** Actual website crawling and analysis
- **Network Intrusion Detection:** Traffic analysis module
- **User Authentication:** Multi-user support with RBAC
- **Advanced XAI:** SHAP, LIME for model interpretability
- **PDF Report Generation:** Automated threat reports
- **Cloud Deployment:** Scalable cloud infrastructure
- **API Rate Limiting:** Protection against abuse
- **Real-time Threat Feeds:** Integration with threat intelligence

### Extensibility

The modular architecture allows easy addition of new detectors:

```python
# Example: Add new detector
from detection.base_detector import BaseDetector

class NewDetector(BaseDetector):
    def predict(self, input_data):
        # Implementation
        pass
```

## 🐛 Troubleshooting

### Androguard Import Error
**Solution:** Androguard is optional. System will use basic ZIP analysis if unavailable.

### Model Not Found Error
**Solution:** Run training scripts before starting the application.

### Port Already in Use
**Solution:** Change port in `app.py`:
```python
app.run(port=5001)
```

### Database Locked
**Solution:** Close any other instances accessing the SQLite database.

## 👥 Contributors

- **Your Name** - Final Year Engineering Student
- **Project Guide** - Guide Name
- **Institution** - Your College/University

## 📄 License

This project is created for educational purposes as part of a final-year engineering project.

## 📞 Contact

For questions or feedback:
- Email: your.email@example.com
- GitHub: github.com/yourusername

## 🙏 Acknowledgments

- Scikit-learn for machine learning tools
- Flask for web framework
- Androguard for APK analysis
- Bootstrap for UI components
- Chart.js for visualizations

---

**⚠️ Disclaimer:** This is an educational project demonstrating ML applications in cybersecurity. It is NOT intended for production use without significant enhancements and should NOT be relied upon as the sole security measure. Always use multiple security tools and follow industry best practices.

**Phase 1 (30%) - Foundation Complete** ✅
#   S e c u r e V i s i o n - I n t e l l i g e n t - C y b e r s e c u r i t y - T h r e a t - D e t e c t i o n - a n d - A n a l y s i s - S y s t e m  
 