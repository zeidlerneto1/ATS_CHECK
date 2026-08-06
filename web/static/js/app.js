// ===== DOM Elements =====
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const jobSelect = document.getElementById('jobSelect');
const logsSection = document.getElementById('logsSection');
const logsContent = document.getElementById('logsContent');
const progressFill = document.getElementById('progressFill');
const statusBadge = document.getElementById('statusBadge');
const resultsSection = document.getElementById('resultsSection');

let currentFile = null;

// ===== File Upload =====
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

function handleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(ext)) {
        alert('Formato não suportado. Use PDF ou DOCX.');
        return;
    }
    currentFile = file;
    dropZone.classList.add('has-file');
    dropZone.querySelector('.drop-zone-content').innerHTML = `
        <span class="icon">✅</span>
        <p class="file-name">${file.name}</p>
        <small>${(file.size / 1024).toFixed(1)} KB</small>
    `;
    analyzeBtn.disabled = false;
}

// ===== Analyze =====
analyzeBtn.addEventListener('click', startAnalysis);

function startAnalysis() {
    if (!currentFile) return;

    // Reset UI
    logsContent.innerHTML = '';
    resultsSection.style.display = 'none';
    logsSection.style.display = 'block';
    progressFill.style.width = '0%';
    statusBadge.textContent = 'Processando...';
    statusBadge.classList.remove('done');
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '⏳ Analisando...';

    const formData = new FormData();
    formData.append('cv', currentFile);
    formData.append('job', jobSelect.value);

    // Use SSE para streaming de logs
    const evtSource = new EventSource('/api/analyze/stream?' + new URLSearchParams({
        // SSE não suporta POST com FormData nativamente
        // Vamos usar fetch normal e simular logs
    }));

    // Como SSE com POST é complicado, vamos usar fetch e mostrar logs simulados
    // Na prática real, você usaria um endpoint SSE separado ou WebSocket

    fetch('/api/analyze', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Mostra logs
            showLogs(data.logs);
            // Mostra resultados
            showResults(data.result);
            statusBadge.textContent = '✅ Concluído';
            statusBadge.classList.add('done');
        } else {
            showError(data.error);
        }
    })
    .catch(err => {
        showError('Erro na análise: ' + err.message);
    })
    .finally(() => {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🔍 Analisar CV';
        progressFill.style.width = '100%';
    });
}

function showLogs(logs) {
    logs.forEach((log, index) => {
        setTimeout(() => {
            addLogEntry(log);
            const progress = ((index + 1) / logs.length) * 100;
            progressFill.style.width = progress + '%';
        }, index * 80);
    });
}

function addLogEntry(log) {
    const entry = document.createElement('div');
    entry.className = `log-entry ${log.severity.toLowerCase()}`;

    const time = new Date(log.timestamp).toLocaleTimeString('pt-BR');

    let detailsHtml = '';
    if (log.details && Object.keys(log.details).length > 0) {
        const detailsStr = JSON.stringify(log.details, null, 2).substring(0, 200);
        detailsHtml = `<div class="log-details">${detailsStr}</div>`;
    }

    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-stage">${log.stage_name}</span>
        <div>
            <span class="log-action">${log.action}</span>
            ${detailsHtml}
        </div>
    `;

    logsContent.appendChild(entry);
    logsContent.scrollTop = logsContent.scrollHeight;
}

function showResults(result) {
    resultsSection.style.display = 'block';

    // Score circle
    const score = result.overall_score;
    const scoreCircle = document.getElementById('scoreCircle');
    const scoreValue = document.getElementById('scoreValue');
    const scoreBar = document.getElementById('scoreBar');
    const resultTitle = document.getElementById('resultTitle');
    const resultSubtitle = document.getElementById('resultSubtitle');

    scoreValue.textContent = score;

    let status = 'reject';
    let statusText = 'REJECT';
    let statusColor = 'var(--danger)';

    if (score >= 70) {
        status = 'pass';
        statusText = 'PASS';
        statusColor = 'var(--success)';
    } else if (score >= 50) {
        status = 'review';
        statusText = 'REVIEW';
        statusColor = 'var(--warning)';
    }

    scoreCircle.className = `score-circle ${status}`;
    scoreCircle.style.setProperty('--score-percent', score + '%');
    scoreBar.className = `score-bar ${status}`;
    scoreBar.style.width = score + '%';

    resultTitle.textContent = `Decisão: ${statusText}`;
    resultTitle.style.color = statusColor;
    resultSubtitle.textContent = `${result.candidate_name} vs ${result.job_title}`;

    // Detail cards
    animateValue('skillScore', result.skill_match_score);
    animateValue('expScore', result.experience_score);
    animateValue('eduScore', result.education_score);
    animateValue('fmtScore', result.formatting_score);
    animateValue('semScore', result.semantic_score);
    animateValue('densScore', result.keyword_density_score);

    setTimeout(() => {
        document.getElementById('skillBar').style.width = result.skill_match_score + '%';
        document.getElementById('expBar').style.width = result.experience_score + '%';
        document.getElementById('eduBar').style.width = result.education_score + '%';
        document.getElementById('fmtBar').style.width = result.formatting_score + '%';
        document.getElementById('semBar').style.width = result.semantic_score + '%';
        document.getElementById('densBar').style.width = Math.min(result.keyword_density_score * 5, 100) + '%';
    }, 300);

    // Keywords
    const matchedContainer = document.getElementById('matchedKeywords');
    const missingContainer = document.getElementById('missingKeywords');

    matchedContainer.innerHTML = result.matched_keywords
        .map(k => `<span class="keyword-tag matched">${k}</span>`)
        .join('');

    missingContainer.innerHTML = result.missing_keywords
        .map(k => `<span class="keyword-tag missing">${k}</span>`)
        .join('');

    // Red flags
    const flagsSection = document.getElementById('flagsSection');
    const flagsList = document.getElementById('flagsList');

    if (result.red_flags.length > 0) {
        flagsSection.style.display = 'block';
        flagsList.innerHTML = result.red_flags
            .map(f => `<div class="flag-item">${f}</div>`)
            .join('');
    } else {
        flagsSection.style.display = 'none';
    }

    // Recommendations
    document.getElementById('recommendationsList').innerHTML = result.recommendations
        .map(r => `<div class="rec-item">${r}</div>`)
        .join('');

    // Scroll to results
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 500);
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    let current = 0;
    const step = target / 30;
    const timer = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        el.textContent = Math.round(current);
    }, 30);
}

function showError(message) {
    statusBadge.textContent = '❌ Erro';
    statusBadge.style.background = 'var(--danger)';
    logsContent.innerHTML += `<div class="log-entry error"><span class="log-action">${message}</span></div>`;
}
