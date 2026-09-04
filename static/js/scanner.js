// Common scanner functions

// Show/hide loading spinner
function showLoading() {
    document.getElementById('loading').classList.add('active');
    document.getElementById('results').style.display = 'none';
}

function hideLoading() {
    document.getElementById('loading').classList.remove('active');
}

// Scan URL
async function scanURL(url) {
    showLoading();
    
    try {
        const response = await fetch('/api/scan/url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            displayResults(data, 'URL', url);
        } else {
            displayError(data.error || 'Scan failed');
        }
    } catch (error) {
        hideLoading();
        displayError('Network error occurred');
        console.error('Error:', error);
    }
}

// Scan Message
async function scanMessage(message) {
    showLoading();
    
    try {
        const response = await fetch('/api/scan/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            displayResults(data, 'MESSAGE', message.substring(0, 100) + '...');
        } else {
            displayError(data.error || 'Scan failed');
        }
    } catch (error) {
        hideLoading();
        displayError('Network error occurred');
        console.error('Error:', error);
    }
}

// Scan APK
async function scanAPK(file) {
    showLoading();
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/scan/apk', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            displayResults(data, 'APK', data.filename);
        } else {
            displayError(data.error || 'Scan failed');
        }
    } catch (error) {
        hideLoading();
        displayError('Network error occurred');
        console.error('Error:', error);
    }
}

// Display results
function displayResults(data, scanType, input) {
    const resultsDiv = document.getElementById('results');
    const isThreat = data.prediction !== 'SAFE';
    const resultClass = isThreat ? 'threat' : 'safe';
    const iconClass = isThreat ? 'bi-exclamation-triangle-fill text-danger' : 'bi-check-circle-fill text-success';
    
    const confidencePercent = (data.confidence * 100).toFixed(1);
    const riskClass = getRiskClass(data.risk_level);
    
    let html = `
        <div class="result-box ${resultClass} fade-in">
            <div class="result-title">
                <i class="bi ${iconClass}"></i>
                Scan Result: ${data.prediction}
            </div>
            
            <div class="row mt-3">
                <div class="col-md-6">
                    <h6>Confidence</h6>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confidencePercent}%">
                            ${confidencePercent}%
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6>Risk Level</h6>
                    <span class="risk-badge ${riskClass} fs-5">${data.risk_level}</span>
                    <p class="mt-2 mb-0"><small>Risk Score: ${data.risk_score}/100</small></p>
                </div>
            </div>
            
            <hr class="my-4">
            
            <h5><i class="bi bi-info-circle"></i> Explanation</h5>
            <div class="alert alert-light">
                <p class="mb-0">${escapeHtml(data.explanation).replace(/\\n/g, '<br>')}</p>
            </div>
    `;
    
    // Add indicators if available
    if (data.indicators && data.indicators.length > 0) {
        html += `
            <h5 class="mt-4"><i class="bi bi-list-check"></i> Detected Indicators</h5>
            <ul class="indicators-list">
                ${data.indicators.map(indicator => `<li>${escapeHtml(indicator)}</li>`).join('')}
            </ul>
        `;
    }
    
    // Add recommendations
    if (data.recommendations && data.recommendations.length > 0) {
        html += `
            <h5 class="mt-4"><i class="bi bi-shield-check"></i> Security Recommendations</h5>
            <ol class="recommendations-list">
                ${data.recommendations.map(rec => `<li>${escapeHtml(rec)}</li>`).join('')}
            </ol>
        `;
    }
    
    // Add analysis note for APK
    if (data.analysis_note) {
        html += `
            <div class="alert alert-warning mt-3">
                <i class="bi bi-exclamation-circle"></i>
                ${escapeHtml(data.analysis_note)}
            </div>
        `;
    }
    
    html += `
            <div class="d-grid gap-2 mt-4">
                <a href="/${scanType.toLowerCase() === 'apk' ? 'scan/apk' : 'scan/' + scanType.toLowerCase()}" class="btn btn-outline-primary">
                    <i class="bi bi-arrow-left"></i> Scan Another
                </a>
                <a href="/history" class="btn btn-outline-secondary">
                    <i class="bi bi-clock-history"></i> View History
                </a>
            </div>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

// Display error
function displayError(message) {
    const resultsDiv = document.getElementById('results');
    
    resultsDiv.innerHTML = `
        <div class="alert alert-danger fade-in">
            <h5><i class="bi bi-exclamation-triangle"></i> Error</h5>
            <p class="mb-0">${escapeHtml(message)}</p>
        </div>
    `;
    
    resultsDiv.style.display = 'block';
}

// Helper functions
function getRiskClass(riskLevel) {
    const classes = {
        'LOW': 'risk-low',
        'MEDIUM': 'risk-medium',
        'HIGH': 'risk-high'
    };
    return classes[riskLevel] || 'risk-medium';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
