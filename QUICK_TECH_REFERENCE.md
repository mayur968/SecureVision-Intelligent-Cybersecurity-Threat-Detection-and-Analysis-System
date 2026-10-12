# SecureVision - Quick Technology Reference Card

## 🎯 **Core Tech Stack (Top 10)**

| # | Technology | Version | Category | Purpose |
|---|------------|---------|----------|---------|
| 1 | **Python** | 3.10+ | Language | Backend development |
| 2 | **Flask** | 3.0.0 | Framework | Web application |
| 3 | **scikit-learn** | 1.3.2 | ML | Machine learning models |
| 4 | **SQLite** | 3.x | Database | Data persistence |
| 5 | **Bootstrap** | 5.3.0 | Frontend | UI framework |
| 6 | **NumPy** | 1.26.2 | Data Science | Numerical computing |
| 7 | **pandas** | 2.1.4 | Data Science | Data manipulation |
| 8 | **Chart.js** | 4.4.0 | Visualization | Dashboard charts |
| 9 | **SQLAlchemy** | 2.0.23 | ORM | Database abstraction |
| 10 | **NLTK** | 3.8.1 | NLP | Text processing |

---

## 📦 **Complete Package List**

### Python Backend (requirements.txt)
```
Flask==3.0.0
Werkzeug==3.0.1
SQLAlchemy==2.0.23
Flask-SQLAlchemy==3.1.1
scikit-learn==1.3.2
pandas==2.1.4
numpy==1.26.2
joblib==1.3.2
nltk==3.8.1
androguard==4.1.0
python-magic-bin==0.4.14
email-validator==2.1.0
pytest==7.4.3
pytest-flask==1.3.0
```

### Frontend (CDN Links)
```html
<!-- Bootstrap CSS -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">

<!-- Bootstrap Icons -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">

<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<!-- Bootstrap JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
```

---

## 🔧 **Technology by Feature**

### URL Phishing Detection
- **Preprocessing:** Python regex, urllib.parse
- **Feature Extraction:** NumPy arrays (20 features)
- **ML Model:** Random Forest (scikit-learn)
- **Accuracy:** 100% (demo dataset)

### Message Phishing Detection
- **Preprocessing:** NLTK, regex
- **Vectorization:** TF-IDF (scikit-learn)
- **Feature Extraction:** Text statistics (21 features)
- **ML Model:** Logistic Regression (scikit-learn)
- **Accuracy:** 90% (demo dataset)

### APK Malware Detection
- **Preprocessing:** Androguard (optional), zipfile
- **Feature Extraction:** Manifest parsing (10 features)
- **ML Model:** Logistic Regression (scikit-learn)
- **Accuracy:** 100% (demo dataset)

---

## 📊 **ML Models Used**

| Model Type | Algorithm | Used For | Library |
|------------|-----------|----------|---------|
| Classification | Random Forest | URL Detection | scikit-learn |
| Classification | Logistic Regression | Message Detection | scikit-learn |
| Classification | Logistic Regression | APK Detection | scikit-learn |
| Vectorization | TF-IDF | Text Features | scikit-learn |

---

## 🗄️ **Database Stack**

```
SQLAlchemy (ORM)
    ↓
SQLite (DBMS)
    ↓
securevision.db (File)
    ↓
scan_history (Table)
```

**Schema:**
- id (INTEGER PRIMARY KEY)
- scan_type (VARCHAR)
- input_value (TEXT)
- prediction (VARCHAR)
- confidence (FLOAT)
- risk_level (VARCHAR)
- explanation (TEXT)
- recommendation (TEXT)
- created_at (DATETIME)

---

## 🎨 **Frontend Stack**

### HTML Templates (Jinja2)
- base.html
- dashboard.html
- url_scanner.html
- message_scanner.html
- apk_scanner.html
- history.html
- 404.html

### CSS
- Bootstrap 5.3.0 (framework)
- Custom styles (style.css)

### JavaScript
- Vanilla JS (ES6+)
- Chart.js (visualization)
- Fetch API (AJAX calls)

---

## 🔌 **API Endpoints**

| Method | Endpoint | Input | Output |
|--------|----------|-------|--------|
| POST | /api/scan/url | JSON: {url} | JSON: result |
| POST | /api/scan/message | JSON: {message} | JSON: result |
| POST | /api/scan/apk | multipart/form-data | JSON: result |
| GET | /api/history | Query: ?limit=50 | JSON: scans[] |
| GET | /api/statistics | - | JSON: stats |

---

## 🚀 **Quick Start Commands**

```bash
# Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Train models
python training/train_url_model.py
python training/train_message_model.py
python training/train_apk_model.py

# Run application
python app.py

# Run tests
pytest tests/ -v

# Access
http://localhost:5000
```

---

## 📁 **Key Files**

| File | Technology | Purpose |
|------|-----------|---------|
| app.py | Flask | Main application |
| config.py | Python | Configuration |
| requirements.txt | pip | Dependencies |
| models/*.pkl | joblib | Trained models |
| templates/*.html | Jinja2 | HTML pages |
| static/css/*.css | CSS3 | Styling |
| static/js/*.js | JavaScript | Interactivity |

---

## 🔒 **Security Technologies**

| Feature | Technology |
|---------|-----------|
| Input Validation | Custom validators (Python) |
| SQL Injection Prevention | SQLAlchemy (parameterized queries) |
| XSS Prevention | Jinja2 (auto-escape) |
| File Upload Security | Werkzeug (secure_filename) |
| File Type Detection | python-magic |
| CSRF Protection | Flask (built-in) |

---

## 🧪 **Testing Stack**

```
pytest 7.4.3
    ↓
pytest-flask 1.3.0
    ↓
tests/*.py (Unit tests)
```

**Test Files:**
- test_url_detector.py
- test_message_detector.py
- test_apk_detector.py

---

## 📦 **Dependencies Count**

- **Direct Dependencies:** 14 packages
- **Total Dependencies:** ~70 packages (including sub-dependencies)
- **Frontend Libraries:** 3 (Bootstrap, Icons, Chart.js)
- **Lines of Code:** ~5,000+
- **Python Modules:** 25+
- **HTML Templates:** 7
- **JavaScript Files:** 2

---

## 🎯 **Technology Selection Criteria**

| Criterion | Technology Choice |
|-----------|------------------|
| **Ease of Learning** | Flask, Bootstrap |
| **Performance** | NumPy, scikit-learn |
| **Scalability** | Modular architecture |
| **Security** | Input validation, ORM |
| **Maintainability** | Clean code, documentation |
| **Cost** | All open-source, free |

---

## 🔄 **Version Compatibility**

| Technology | Minimum Version | Tested Version |
|------------|----------------|----------------|
| Python | 3.10 | 3.10.11 |
| Flask | 3.0.0 | 3.0.0 |
| scikit-learn | 1.3.0 | 1.3.2 |
| Bootstrap | 5.0 | 5.3.0 |
| SQLAlchemy | 2.0 | 2.0.23 |

---

## 📊 **Performance Characteristics**

| Operation | Avg Time | Technology |
|-----------|----------|-----------|
| URL Scan | ~100ms | Flask + scikit-learn |
| Message Scan | ~150ms | Flask + TF-IDF |
| APK Scan | ~200ms | Flask + Androguard |
| Model Load | ~1s | joblib (on startup) |
| Database Query | <50ms | SQLite |

---

## 🌐 **Supported Platforms**

| Platform | Status | Notes |
|----------|--------|-------|
| Windows | ✅ Tested | Primary development |
| Linux | ✅ Compatible | Should work |
| macOS | ✅ Compatible | Should work |
| Docker | 🔄 Phase 2+ | Not yet implemented |
| Cloud | 🔄 Phase 2+ | Future deployment |

---

## 📚 **Documentation Technologies**

- **Code Docs:** Python docstrings
- **README:** Markdown
- **Guides:** Plain text, Markdown
- **Comments:** Inline Python/JS comments
- **API Docs:** This file + README

---

## 🎓 **For Project Presentation**

**Key Technologies to Highlight:**

1. **Flask** - Why we chose it (lightweight, flexible)
2. **scikit-learn** - Industry-standard ML library
3. **Bootstrap** - Professional UI framework
4. **SQLite** - Perfect for prototype/MVP
5. **Modular Design** - Easy to extend

**Architecture Buzzwords:**
- RESTful API
- MVC Pattern
- ORM (Object-Relational Mapping)
- TF-IDF Vectorization
- Static Code Analysis
- Responsive Web Design

---

## 💡 **Technology Alternatives (Not Used)**

| Category | Alternative | Why Not Used |
|----------|-------------|--------------|
| Web Framework | Django | Too heavy for MVP |
| Frontend | React/Vue | Unnecessary complexity |
| Database | PostgreSQL | Overkill for Phase 1 |
| ML | TensorFlow | Traditional ML sufficient |
| NLP | BERT | Too resource-intensive |

---

## 🎯 **Technology Roadmap (Future)**

**Phase 2+ (70% remaining):**
- Deep Learning (TensorFlow/PyTorch)
- BERT for NLP
- PostgreSQL for production
- Redis for caching
- Docker containerization
- Kubernetes orchestration
- AWS/Azure cloud deployment

---

**Technology Stack Quick Reference - Complete** ✅

This reference provides all technology information in a quick, scannable format for presentations and documentation.

---

*Version: 1.0*  
*Last Updated: September 4, 2026*  
*SecureVision - Phase 1 (30%)*
