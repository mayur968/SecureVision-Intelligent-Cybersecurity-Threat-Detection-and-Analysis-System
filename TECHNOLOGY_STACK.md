# SecureVision - Technology Stack

**Project:** SecureVision - Intelligent Cybersecurity Threat Detection System  
**Phase:** 1 (30% Implementation)  
**Date:** September 4, 2026

---

## 📚 Complete Technology Stack

### 🔧 **Backend Technologies**

#### Core Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10+ | Primary programming language |
| **Flask** | 3.0.0 | Web application framework |
| **Werkzeug** | 3.0.1 | WSGI utility library (Flask dependency) |

#### Database
| Technology | Version | Purpose |
|------------|---------|---------|
| **SQLite** | 3.x | Embedded relational database |
| **SQLAlchemy** | 2.0.23 | SQL toolkit and ORM |
| **Flask-SQLAlchemy** | 3.1.1 | Flask extension for SQLAlchemy |

---

### 🤖 **Machine Learning & Data Science**

#### ML Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| **scikit-learn** | 1.3.2 | Machine learning library (classification models) |
| **NumPy** | 1.26.2 | Numerical computing (arrays, matrices) |
| **pandas** | 2.1.4 | Data manipulation and analysis |
| **joblib** | 1.3.2 | Model serialization and persistence |
| **SciPy** | 1.15.3+ | Scientific computing (dependency) |

#### Natural Language Processing
| Technology | Version | Purpose |
|------------|---------|---------|
| **NLTK** | 3.8.1 | Natural language toolkit |
| **TF-IDF** | (scikit-learn) | Text vectorization for message analysis |

#### ML Models Used
- **Logistic Regression** - Binary classification (Message, APK)
- **Random Forest** - Ensemble learning (URL detection)
- **TF-IDF Vectorizer** - Text feature extraction

---

### 📱 **APK Analysis**

| Technology | Version | Purpose |
|------------|---------|---------|
| **Androguard** | 4.1.0 | Android APK static analysis (optional) |
| **python-magic-bin** | 0.4.14 | File type identification (Windows) |
| **lxml** | 4.3.0+ | XML parsing for Android manifests |

**Note:** Androguard dependencies include:
- PyQt5 (GUI components)
- asn1crypto (cryptography)
- Frida (dynamic instrumentation - not used in Phase 1)
- networkx (graph analysis)
- pydot (graph visualization)

---

### 🎨 **Frontend Technologies**

#### HTML/CSS/JavaScript
| Technology | Version | Purpose |
|------------|---------|---------|
| **HTML5** | - | Markup language |
| **CSS3** | - | Styling and layout |
| **JavaScript (ES6+)** | - | Client-side scripting |

#### Frontend Frameworks & Libraries
| Technology | Version | Purpose |
|------------|---------|---------|
| **Bootstrap** | 5.3.0 | Responsive UI framework |
| **Bootstrap Icons** | 1.11.0 | Icon library |
| **Chart.js** | 4.4.0 | Data visualization and charts |

#### Frontend Architecture
- **Vanilla JavaScript** - No heavy frameworks (React, Vue, Angular)
- **AJAX/Fetch API** - Asynchronous API calls
- **DOM Manipulation** - Dynamic content updates
- **Event-Driven** - User interaction handling

---

### 🔐 **Security & Validation**

| Technology | Version | Purpose |
|------------|---------|---------|
| **email-validator** | 2.1.0 | Email format validation |
| **python-magic** | 0.4.27 | File type detection (Linux/Mac) |
| **Werkzeug Security** | 3.0.1 | Secure filename handling |

**Security Features Implemented:**
- Input validation and sanitization
- File upload security (extension, size, MIME type)
- SQL injection prevention (parameterized queries)
- XSS protection (HTML escaping)
- Secure file naming (random generation)
- CSRF protection (Flask built-in)
- No code execution (APKs not executed)

---

### 🧪 **Testing & Quality Assurance**

| Technology | Version | Purpose |
|------------|---------|---------|
| **pytest** | 7.4.3 | Testing framework |
| **pytest-flask** | 1.3.0 | Flask-specific test utilities |

**Testing Coverage:**
- Unit tests for detectors
- Feature extraction tests
- Validation tests
- Model prediction tests

---

### 📊 **Data & Visualization**

#### Data Handling
| Technology | Purpose |
|------------|---------|
| **CSV** | Dataset storage format |
| **JSON** | API data exchange format |
| **SQLite** | Persistent data storage |

#### Visualization
| Technology | Purpose |
|------------|---------|
| **Chart.js** | Pie charts, bar charts |
| **HTML Tables** | Data presentation |
| **CSS Grid/Flexbox** | Responsive layouts |

---

### 🛠️ **Development Tools**

#### Version Control
| Technology | Purpose |
|------------|---------|
| **Git** | Version control system |
| **.gitignore** | Exclude unnecessary files |

#### Environment Management
| Technology | Purpose |
|------------|---------|
| **venv** | Python virtual environment |
| **pip** | Package management |
| **requirements.txt** | Dependency specification |

#### IDE / Editor (Recommended)
- Visual Studio Code
- PyCharm
- Sublime Text
- Any Python-compatible IDE

---

### 📦 **Project Structure & Architecture**

#### Design Patterns
| Pattern | Application |
|---------|-------------|
| **MVC** | Model-View-Controller separation |
| **Modular Architecture** | Independent detector modules |
| **Service Layer** | Business logic separation |
| **Repository Pattern** | Database abstraction |

#### File Organization
```
Layered Architecture:
├── Presentation Layer (templates/, static/)
├── API Layer (app.py routes)
├── Service Layer (detection/, explanation/)
├── Data Layer (preprocessing/, features/)
├── Persistence Layer (database/, models/)
└── Utility Layer (utils/)
```

---

### 🌐 **Web Technologies**

#### HTTP/Web Standards
| Technology | Purpose |
|------------|---------|
| **REST API** | API architecture style |
| **JSON** | Data interchange format |
| **HTTP Methods** | GET, POST request handling |
| **CORS** | Cross-origin resource sharing (if needed) |

#### Web Server
| Technology | Purpose |
|------------|---------|
| **Flask Development Server** | Built-in WSGI server (development) |
| **Werkzeug WSGI** | Web server gateway interface |

**Note:** For production, consider:
- Gunicorn (Python WSGI server)
- Nginx (reverse proxy)
- uWSGI (application server)

---

### 📝 **Configuration & Logging**

| Technology | Purpose |
|------------|---------|
| **Python logging** | Application logging |
| **Python configparser** | Configuration management |
| **Environment Variables** | Secret management |

---

## 🔄 **Data Flow Architecture**

### URL Detection Stack
```
User Input (URL)
    ↓
Flask Route (/api/scan/url)
    ↓
Input Validator (utils/validators.py)
    ↓
URL Preprocessor (preprocessing/url_preprocessing.py)
    ↓
Feature Extractor (features/url_features.py)
    → 20 numerical features
    ↓
ML Model (Random Forest)
    → Prediction + Confidence
    ↓
Risk Scorer (explanation/risk_score.py)
    → Risk score (0-100) + Level
    ↓
Threat Explainer (explanation/threat_explainer.py)
    → Human-readable explanation
    ↓
Recommendation Engine (explanation/recommendations.py)
    → Security recommendations
    ↓
Database Storage (SQLite)
    ↓
JSON Response → Frontend
```

### Message Detection Stack
```
User Input (Text)
    ↓
Flask Route (/api/scan/message)
    ↓
Input Validator
    ↓
Text Preprocessor (preprocessing/text_preprocessing.py)
    → Clean text, remove punctuation
    ↓
TF-IDF Vectorizer
    → 1000 features (unigrams + bigrams)
    ↓
Feature Extractor (features/text_features.py)
    → 21 additional features
    ↓
ML Model (Logistic Regression)
    ↓
[Same analysis pipeline as URL]
```

### APK Detection Stack
```
User Upload (APK file)
    ↓
Flask Route (/api/scan/apk)
    ↓
File Security Check (utils/file_security.py)
    → Extension, size, type validation
    ↓
Temporary Storage (uploads/)
    ↓
APK Preprocessor (preprocessing/apk_preprocessing.py)
    → Validate APK structure
    ↓
Feature Extractor (features/apk_features.py)
    → Androguard OR ZIP inspection
    → 10 numerical features
    ↓
ML Model (Logistic Regression)
    ↓
[Same analysis pipeline]
    ↓
File Cleanup (secure deletion)
```

---

## 🎯 **Feature Extraction Technologies**

### URL Features (20 features)
- **String Analysis:** Length, character counts
- **Pattern Matching:** Regex for IP, subdomain detection
- **Keyword Analysis:** Suspicious word detection
- **Protocol Analysis:** HTTPS detection

### Message Features (1000+ features)
- **TF-IDF:** Term frequency-inverse document frequency
- **N-grams:** Unigrams and bigrams
- **Text Statistics:** Length, word count, punctuation
- **Pattern Detection:** URLs, emails, phone numbers
- **Keyword Categories:** Urgent, financial, security, threat words

### APK Features (10 features)
- **Static Analysis:** Permission extraction
- **Manifest Parsing:** Component counting
- **File Analysis:** DEX files, structure
- **Permission Risk:** Dangerous permission identification

---

## 📊 **Machine Learning Pipeline**

### Training Pipeline
```
Raw Dataset (CSV)
    ↓
Data Loading (pandas)
    ↓
Feature Extraction
    ↓
Train/Test Split (80/20)
    ↓
Model Training
    ├── Logistic Regression
    └── Random Forest
    ↓
Model Evaluation
    ├── Accuracy
    ├── Precision
    ├── Recall
    └── F1-Score
    ↓
Best Model Selection
    ↓
Model Serialization (joblib)
    ↓
Save to models/
```

### Prediction Pipeline
```
New Input
    ↓
Feature Extraction
    ↓
Load Trained Model (joblib)
    ↓
Predict
    ↓
Get Confidence (predict_proba)
    ↓
Return Result
```

---

## 🔌 **API Architecture**

### REST API Endpoints
```
POST /api/scan/url
POST /api/scan/message
POST /api/scan/apk
GET  /api/history
GET  /api/statistics
```

### Data Format
- **Request:** JSON (application/json) or multipart/form-data (APK)
- **Response:** JSON with standard structure
  ```json
  {
    "success": true,
    "prediction": "PHISHING",
    "confidence": 0.94,
    "risk_score": 94,
    "risk_level": "HIGH",
    "explanation": "...",
    "recommendations": [...]
  }
  ```

---

## 🗄️ **Database Schema**

### Technology
- **DBMS:** SQLite 3.x
- **ORM:** SQLAlchemy 2.0.23

### Schema
```sql
CREATE TABLE scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_type VARCHAR(20) NOT NULL,
    input_value TEXT NOT NULL,
    prediction VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    explanation TEXT,
    recommendation TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🌍 **Deployment Stack (Phase 1 - Development)**

### Current Environment
- **OS:** Windows 10/11 (or Linux/Mac)
- **Python:** 3.10+
- **Server:** Flask Development Server
- **Database:** SQLite (file-based)
- **Host:** localhost (127.0.0.1)
- **Port:** 5000

### Future Production Stack (Phase 2+)
- **Web Server:** Gunicorn + Nginx
- **Database:** PostgreSQL or MySQL
- **Caching:** Redis
- **Cloud Platform:** AWS, Azure, or GCP
- **Containerization:** Docker
- **Orchestration:** Kubernetes (optional)
- **CDN:** CloudFlare or AWS CloudFront

---

## 📦 **Dependency Tree (Simplified)**

```
SecureVision
├── Flask 3.0.0
│   ├── Werkzeug 3.0.1
│   ├── Jinja2 3.1.6
│   ├── Click 8.5.0
│   └── Blinker 1.9.0
│
├── SQLAlchemy 2.0.23
│   ├── greenlet 3.5.5
│   └── typing-extensions 4.16.0
│
├── scikit-learn 1.3.2
│   ├── NumPy 1.26.2
│   ├── SciPy 1.15.3
│   ├── joblib 1.3.2
│   └── threadpoolctl 3.6.0
│
├── pandas 2.1.4
│   ├── NumPy 1.26.2
│   ├── python-dateutil 2.9.0
│   └── pytz 2026.3
│
├── NLTK 3.8.1
│   ├── regex 2026.9.3
│   └── tqdm 4.70.0
│
└── Androguard 4.1.0 (optional)
    ├── PyQt5 5.15.11
    ├── lxml 6.1.3
    ├── pydot 4.0.1
    └── [many more...]
```

---

## 🎨 **UI/UX Technologies**

### Design System
- **Framework:** Bootstrap 5.3.0
- **Icons:** Bootstrap Icons 1.11.0
- **Color Scheme:** Custom CSS variables
- **Typography:** System fonts
- **Grid System:** Bootstrap Grid + CSS Flexbox

### Responsive Design
- **Mobile-First:** Bootstrap breakpoints
- **Viewport:** Responsive meta tags
- **Media Queries:** CSS3

### Interactivity
- **Charts:** Chart.js (Pie, Bar, Doughnut)
- **Forms:** HTML5 validation + JS
- **File Upload:** Drag-and-drop support
- **Loading States:** CSS animations
- **Toasts/Alerts:** Bootstrap alerts

---

## 🔒 **Security Stack**

### Application Security
- **Input Validation:** Custom validators
- **SQL Injection Prevention:** Parameterized queries (SQLAlchemy)
- **XSS Prevention:** HTML escaping (Jinja2 auto-escape)
- **File Upload Security:** 
  - Extension whitelist
  - File size limits
  - MIME type validation
  - Secure filename generation
  - Temporary storage with cleanup

### No Execution Policy
- **APK Analysis:** Static only (no execution)
- **URL Analysis:** Pattern-based (no browsing)
- **Sandboxing:** None (Phase 1)

---

## 📚 **Documentation Technologies**

- **Markdown:** README, guides, documentation
- **Docstrings:** Python code documentation
- **Comments:** Inline code comments
- **Type Hints:** Python type annotations (partial)

---

## 🧪 **Testing Stack**

### Testing Framework
```
pytest 7.4.3
├── pytest-flask 1.3.0
├── Test Discovery
├── Fixtures
└── Assertions
```

### Test Types
- **Unit Tests:** Individual function testing
- **Integration Tests:** API endpoint testing
- **Validation Tests:** Input/output validation

---

## 🚀 **Performance & Optimization**

### Performance Features
- **Model Loading:** Once at startup (singleton pattern)
- **Database:** Indexed queries (SQLite)
- **Static Files:** Browser caching
- **Compression:** Gzip (can be enabled)

### Optimization Techniques
- **Feature Vectorization:** NumPy arrays (fast)
- **Model Prediction:** Cached model instances
- **Database Queries:** Lazy loading with limits

---

## 📊 **Technology Selection Rationale**

### Why Flask?
- Lightweight and flexible
- Easy to learn and use
- Excellent for prototypes and MVPs
- Large ecosystem of extensions
- RESTful API support

### Why scikit-learn?
- Industry-standard ML library
- Well-documented
- Excellent for traditional ML
- Fast training and prediction
- Easy model serialization

### Why SQLite?
- Zero configuration
- Self-contained
- Perfect for development
- Easy to migrate to production DB
- Built into Python

### Why Bootstrap?
- Rapid UI development
- Responsive out-of-the-box
- Large component library
- Well-documented
- Industry standard

---

## 🎯 **Technology Alignment with Project Goals**

| Goal | Technology Choice | Reason |
|------|------------------|---------|
| **Rapid Development** | Flask + Bootstrap | Quick prototyping |
| **ML Implementation** | scikit-learn | Traditional ML focus |
| **Modularity** | Python packages | Easy to extend |
| **Security** | Static analysis | Safe in Phase 1 |
| **User Experience** | Chart.js + Bootstrap | Professional UI |
| **Data Storage** | SQLite | Simple persistence |
| **API Design** | REST + JSON | Standard interface |

---

## 📈 **Scalability Considerations**

### Current Limitations (By Design)
- Single-threaded Flask dev server
- SQLite (single-user database)
- No caching layer
- No load balancing
- Local file storage

### Phase 2+ Scalability Plan
- Multi-threaded WSGI server (Gunicorn)
- PostgreSQL (concurrent users)
- Redis caching
- Load balancer (Nginx)
- Cloud storage (S3, Azure Blob)
- Microservices architecture (optional)

---

## 🏆 **Technology Stack Summary**

### Core Technologies (Most Important)
1. **Python 3.10+** - Programming language
2. **Flask 3.0.0** - Web framework
3. **scikit-learn 1.3.2** - Machine learning
4. **SQLite + SQLAlchemy** - Database
5. **Bootstrap 5.3.0** - Frontend framework
6. **Chart.js 4.4.0** - Visualization

### Total Dependencies
- **Python Packages:** 50+ (including sub-dependencies)
- **Frontend Libraries:** 3 (Bootstrap, Bootstrap Icons, Chart.js)
- **Database:** 1 (SQLite)

### Technology Categories
- ✅ Backend: Flask, Python
- ✅ Frontend: HTML, CSS, JavaScript, Bootstrap
- ✅ ML/AI: scikit-learn, NumPy, pandas
- ✅ Database: SQLite, SQLAlchemy
- ✅ Security: Custom validators, Werkzeug
- ✅ Testing: pytest
- ✅ Visualization: Chart.js

---

**Technology Stack Document Complete** ✅

This stack provides a solid foundation for Phase 1 (30%) while remaining extensible for future enhancements.

---

*Last Updated: September 4, 2026*  
*For: SecureVision - Intelligent Cybersecurity Threat Detection System*
