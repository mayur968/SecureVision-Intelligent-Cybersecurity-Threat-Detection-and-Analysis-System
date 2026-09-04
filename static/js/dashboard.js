// Dashboard JavaScript

let safeVsThreatChart = null;
let threatsByTypeChart = null;

// Load dashboard data
async function loadDashboard() {
    try {
        // Load statistics
        const statsResponse = await fetch('/api/statistics');
        const statsData = await statsResponse.json();
        
        if (statsData.success) {
            updateStatistics(statsData.statistics);
            updateCharts(statsData.statistics);
        }
        
        // Load recent scans
        const historyResponse = await fetch('/api/history?limit=10');
        const historyData = await historyResponse.json();
        
        if (historyData.success) {
            updateRecentScans(historyData.scans);
        }
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Update statistics cards
function updateStatistics(stats) {
    document.getElementById('total-scans').textContent = stats.total_scans;
    document.getElementById('threats-detected').textContent = stats.threats_detected;
    document.getElementById('safe-results').textContent = stats.safe_results;
    
    // Calculate detection rate
    const rate = stats.total_scans > 0 
        ? ((stats.threats_detected / stats.total_scans) * 100).toFixed(1)
        : 0;
    document.getElementById('detection-rate').textContent = rate + '%';
    
    // Update scan type counts
    document.getElementById('url-scans').textContent = stats.url_scans;
    document.getElementById('message-scans').textContent = stats.message_scans;
    document.getElementById('apk-scans').textContent = stats.apk_scans;
}

// Update charts
function updateCharts(stats) {
    // Safe vs Threat Pie Chart
    const safeVsThreatCtx = document.getElementById('safeVsThreatChart').getContext('2d');
    
    if (safeVsThreatChart) {
        safeVsThreatChart.destroy();
    }
    
    safeVsThreatChart = new Chart(safeVsThreatCtx, {
        type: 'doughnut',
        data: {
            labels: ['Safe', 'Threats'],
            datasets: [{
                data: [stats.safe_results, stats.threats_detected],
                backgroundColor: ['#198754', '#dc3545'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: false
                }
            }
        }
    });
    
    // Threats by Type Bar Chart
    const threatsByTypeCtx = document.getElementById('threatsByTypeChart').getContext('2d');
    
    if (threatsByTypeChart) {
        threatsByTypeChart.destroy();
    }
    
    threatsByTypeChart = new Chart(threatsByTypeCtx, {
        type: 'bar',
        data: {
            labels: ['URL', 'Message', 'APK'],
            datasets: [{
                label: 'Threats Detected',
                data: [
                    stats.threat_breakdown.url,
                    stats.threat_breakdown.message,
                    stats.threat_breakdown.apk
                ],
                backgroundColor: ['#0d6efd', '#0dcaf0', '#198754'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Update recent scans table
function updateRecentScans(scans) {
    const tbody = document.getElementById('recent-scans-body');
    
    if (scans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No scans yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = scans.map(scan => {
        const date = new Date(scan.created_at).toLocaleString();
        const predictionClass = scan.prediction === 'SAFE' ? 'success' : 'danger';
        const riskClass = getRiskClass(scan.risk_level);
        
        return `
            <tr>
                <td><small>${date}</small></td>
                <td><span class="badge bg-secondary">${scan.scan_type}</span></td>
                <td><small>${escapeHtml(scan.input_value)}</small></td>
                <td><span class="badge bg-${predictionClass}">${scan.prediction}</span></td>
                <td><span class="risk-badge ${riskClass}">${scan.risk_level}</span></td>
            </tr>
        `;
    }).join('');
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

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    
    // Refresh every 30 seconds
    setInterval(loadDashboard, 30000);
});
