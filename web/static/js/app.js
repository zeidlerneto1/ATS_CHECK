// ===== DOM Elements =====
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const jobSelect = document.getElementById('jobSelect');
const jobPreview = document.getElementById('jobPreview');
const logsSection = document.getElementById('logsSection');
const logsContent = document.getElementById('logsContent');
const progressFill = document.getElementById('progressFill');
const statusBadge = document.getElementById('statusBadge');
const resultsSection = document.getElementById('resultsSection');

// Tabs
const jobTabs = document.querySelectorAll('.job-tab');
const jobPanels = document.querySelectorAll('.job-panel');

// Custom form fields
const customTitle = document.getElementById('customTitle');
const customCompany = document.getElementById('customCompany');
const customExp = document.getElementById('customExp');
const customEdu = document.getElementById('customEdu');
const customRequired = document.getElementById('customRequired');
const customPreferred = document.getElementById('customPreferred');
const customResp = document.getElementById('customResp');

let currentFile = null;
let jobsData = {};

// ===== Load Jobs Data =====
fetch('/api/jobs')
    .then(r => r.json())
    .then(data => {
        jobsData = data;
        updateJobPreview();
    })
    .catch(() => {
        jobPreview.innerHTML = '<p style="color: var(--text-secondary)">Carregando vagas...</p>';
    });

// ===== Tabs =====
jobTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        jobTabs.forEach(t => t.classList.remove('active'));
        jobPanels.forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab + 'Panel').classList.add('active');
    });
});

// ===== Job Preview =====
jobSelect.addEventListener('change', updateJobPreview);

function updateJobPreview() {
    const key = jobSelect.value;
    const job = jobsData[key];
    if (!job) return;

    const eduLabels = {tecnico: 'Técnico/Tecnólogo', graduacao: 'Graduação', mestrado: 'Mestrado', phd: 'Doutorado'};

    jobPreview.innerHTML = `
        <h4>${job.title}</h4>
        <div class="preview-row">
            <span class="preview-label">Empresa:</span>
            <span class="preview-value">${job.company}</span>
        </div>
        <div class="preview-row">
            <span class="preview-label">XP Requerida:</span>
            <span class="preview-value">${job.required_experience_years} ano(s)</span>
        </div>
        <div class="preview-row">
            <span class="preview-label">Educação:</span>
            <span class="preview-value">${eduLabels[job.education_level] || job.education_level}</span>
        </div>
        <div class="preview-row">
            <span class="preview-label">Skills obrigatórias:</span>
        </div>
        <div class="preview-skills">
            ${job.required_skills.map(s => `<span class="skill-tag req">${s}</span>`).join('')}
        </div>
        <div class="preview-row" style="margin-top: 0.5rem">
            <span class="preview-label">Skills desejáveis:</span>
        </div>
        <div class="preview-skills">
            ${job.preferred_skills.map(s => `<span class="skill-tag pref">${s}</span>`).join('')}
        </div>
    `;
}

// ===== File Upload =====
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault(); dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
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

// ===== Parse Text Button =====
const parseTextBtn = document.getElementById('parseTextBtn');
const jobText = document.getElementById('jobText');
const scrapeUrlBtn = document.getElementById('scrapeUrlBtn');
const urlField = document.getElementById('urlField');
const jobUrl = document.getElementById('jobUrl');
const scrapeBtn = document.getElementById('scrapeBtn');

// Toggle URL field
scrapeUrlBtn.addEventListener('click', () => {
    const isHidden = urlField.style.display === 'none';
    urlField.style.display = isHidden ? 'block' : 'none';
    scrapeUrlBtn.textContent = isHidden ? '❌ Cancelar URL' : '🕷️ Extrair da URL';
});

// Parse from text
parseTextBtn.addEventListener('click', async () => {
    const text = jobText.value.trim();
    if (!text || text.length < 50) {
        alert('Cole a descrição completa da vaga (mínimo 50 caracteres).');
        jobText.focus();
        return;
    }

    parseTextBtn.disabled = true;
    parseTextBtn.textContent = '⏳ Analisando texto...';
    parseTextBtn.classList.add('loading');

    try {
        const resp = await fetch('/api/parse-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const data = await resp.json();

        if (data.success) {
            // Preenche formulário
            customTitle.value = data.title || '';
            customCompany.value = data.company || '';
            customExp.value = data.required_experience_years || '0';
            customEdu.value = data.education_level || 'graduacao';
            customRequired.value = data.required_skills.join(', ') || '';
            customPreferred.value = data.preferred_skills.join(', ') || '';
            customResp.value = data.responsibilities.join('\n') || '';

            showParseMessage(
                `✅ ${data.raw_skills_found.length} skills detectadas! ` +
                `${data.required_skills.length} obrigatórias, ${data.preferred_skills.length} desejáveis.`,
                'success'
            );
        } else {
            showParseMessage(`⚠️ ${data.error || 'Não foi possível extrair dados.'}`, 'error');
        }
    } catch (err) {
        showParseMessage(`❌ Erro: ${err.message}`, 'error');
    } finally {
        parseTextBtn.disabled = false;
        parseTextBtn.textContent = '✨ Extrair Dados do Texto';
        parseTextBtn.classList.remove('loading');
    }
});

// Scrape from URL (fallback)
scrapeBtn.addEventListener('click', async () => {
    const url = jobUrl.value.trim();
    if (!url) {
        alert('Cole a URL da vaga primeiro.');
        return;
    }

    scrapeBtn.disabled = true;
    scrapeBtn.textContent = '⏳...';

    try {
        const resp = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        const data = await resp.json();

        if (data.success) {
            customTitle.value = data.title || '';
            customCompany.value = data.company || '';
            customExp.value = data.required_experience_years || '0';
            customEdu.value = data.education_level || 'graduacao';
            customRequired.value = data.required_skills.join(', ') || '';
            customPreferred.value = data.preferred_skills.join(', ') || '';
            customResp.value = data.responsibilities.join('\n') || '';

            showParseMessage(`✅ Dados extraídos da URL! ${data.required_skills.length} skills encontradas.`, 'success');
        } else {
            showParseMessage(`⚠️ URL falhou: ${data.error}. Use o campo de texto acima.`, 'error');
        }
    } catch (err) {
        showParseMessage(`❌ URL falhou. Use o campo de texto.`, 'error');
    } finally {
        scrapeBtn.disabled = false;
        scrapeBtn.textContent = 'Extrair';
    }
});

function showParseMessage(msg, type) {
    const old = document.querySelector('.scrape-success, .scrape-error');
    if (old) old.remove();

    const div = document.createElement('div');
    div.className = type === 'success' ? 'scrape-success' : 'scrape-error';
    div.textContent = msg;
    jobText.parentElement.appendChild(div);

    setTimeout(() => div.remove(), 10000);
}

function startAnalysis() {
    if (!currentFile) return;

    // Detecta qual tab está ativa
    const activeTab = document.querySelector('.job-tab.active').dataset.tab;

    // Validação para vaga customizada
    if (activeTab === 'custom') {
        if (!customTitle.value.trim()) {
            alert('Preencha o título da vaga.');
            customTitle.focus();
            return;
        }
        if (!customRequired.value.trim()) {
            alert('Preencha pelo menos uma skill obrigatória.');
            customRequired.focus();
            return;
        }
    }

    // Reset UI
    logsContent.innerHTML = '';
    resultsSection.style.display = 'none';
    logsSection.style.display = 'block';
    progressFill.style.width = '0%';
    statusBadge.textContent = 'Processando...';
    statusBadge.classList.remove('done');
    statusBadge.style.background = 'var(--warning)';
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '⏳ Analisando...';

    const formData = new FormData();
    formData.append('cv', currentFile);
    formData.append('job_type', activeTab);

    if (activeTab === 'preset') {
        formData.append('job', jobSelect.value);
    } else {
        formData.append('custom_title', customTitle.value);
        formData.append('custom_company', customCompany.value || 'Empresa');
        formData.append('custom_required', customRequired.value);
        formData.append('custom_preferred', customPreferred.value || '');
        formData.append('custom_exp', customExp.value || '0');
        formData.append('custom_edu', customEdu.value);
        formData.append('custom_resp', customResp.value || '');
    }

    fetch('/api/analyze', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showLogs(data.logs);
            showResults(data.result, data.job);
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
        }, index * 60);
    });
}

function addLogEntry(log) {
    const entry = document.createElement('div');
    entry.className = `log-entry ${log.severity.toLowerCase()}`;

    const time = new Date(log.timestamp).toLocaleTimeString('pt-BR', {hour12: false});

    let detailsHtml = '';
    if (log.details && Object.keys(log.details).length > 0) {
        const detailsStr = JSON.stringify(log.details, null, 2);
        const truncated = detailsStr.length > 150 ? detailsStr.substring(0, 150) + '...' : detailsStr;
        detailsHtml = `<div class="log-details">${truncated}</div>`;
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

function showResults(result, job) {
    resultsSection.style.display = 'block';

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
        status = 'pass'; statusText = 'PASS'; statusColor = 'var(--success)';
    } else if (score >= 50) {
        status = 'review'; statusText = 'REVIEW'; statusColor = 'var(--warning)';
    }

    scoreCircle.className = `score-circle ${status}`;
    scoreCircle.style.setProperty('--score-percent', score + '%');
    scoreBar.className = `score-bar ${status}`;
    scoreBar.style.width = score + '%';

    resultTitle.textContent = `Decisão: ${statusText}`;
    resultTitle.style.color = statusColor;
    resultSubtitle.textContent = `${result.candidate_name} vs ${result.job_title}`;

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

    // Keywords com contadores
    const matchedContainer = document.getElementById('matchedKeywords');
    const missingContainer = document.getElementById('missingKeywords');
    const totalReq = job.required_skills.length;
    const matchedReq = result.matched_keywords.filter(k => job.required_skills.includes(k)).length;

    document.getElementById('matchedCount').textContent = `(${matchedReq}/${totalReq} obrigatórias)`;
    document.getElementById('missingCount').textContent = `(${result.missing_keywords.filter(k => job.required_skills.includes(k)).length}/${totalReq} obrigatórias)`;

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

    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 600);
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    let current = 0;
    const step = target / 25;
    const timer = setInterval(() => {
        current += step;
        if (current >= target) { current = target; clearInterval(timer); }
        el.textContent = Math.round(current);
    }, 30);
}

function showError(message) {
    statusBadge.textContent = '❌ Erro';
    statusBadge.style.background = 'var(--danger)';
    logsContent.innerHTML += `<div class="log-entry error"><span class="log-action">${message}</span></div>`;
}
