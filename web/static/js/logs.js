document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const cvFile = document.getElementById('cvFile');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultsArea = document.getElementById('resultsArea');
    const jobSelect = document.getElementById('jobSelect');

    let currentFile = null;

    // Upload handlers
    dropZone.addEventListener('click', () => cvFile.click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length) handleFile(files[0]);
    });
    cvFile.addEventListener('change', (e) => { if (e.target.files.length) handleFile(e.target.files[0]); });

    function handleFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['pdf','docx'].includes(ext)) {
            alert('Formato não suportado. Use PDF ou DOCX.');
            return;
        }
        currentFile = file;
        dropZone.querySelector('.upload-content').innerHTML = `
            <div class="upload-icon">✅</div>
            <p><strong>${file.name}</strong></p>
            <span class="upload-hint">${(file.size/1024).toFixed(1)} KB</span>
        `;
        analyzeBtn.disabled = false;
    }

    analyzeBtn.addEventListener('click', async () => {
        if (!currentFile) return;
        analyzeBtn.disabled = true;
        analyzeBtn.querySelector('.btn-text').classList.add('hidden');
        analyzeBtn.querySelector('.btn-loader').classList.remove('hidden');
        resultsArea.classList.add('hidden');

        const formData = new FormData();
        formData.append('cv', currentFile);
        formData.append('job_type', 'preset');
        formData.append('job', jobSelect.value);

        try {
            const res = await fetch('/api/analyze', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            renderResults(data);
            resultsArea.classList.remove('hidden');
            resultsArea.scrollIntoView({ behavior: 'smooth' });
        } catch (err) {
            alert('Erro: ' + err.message);
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.querySelector('.btn-text').classList.remove('hidden');
            analyzeBtn.querySelector('.btn-loader').classList.add('hidden');
        }
    });

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
    });

    function renderResults(data) {
        const r = data.result;
        const logs = data.logs || [];
        const job = data.job;

        // Score badge
        const badge = document.getElementById('scoreBadge');
        badge.textContent = r.overall_score + '/100';
        badge.className = 'score-badge ' + (r.overall_score >= 70 ? 'pass' : r.overall_score >= 50 ? 'review' : 'reject');

        // Pipeline tab
        renderPipeline(logs, data);

        // Raw text tab
        renderRaw(data);

        // Entities tab
        renderEntities(data);

        // Keywords tab
        renderKeywords(r, job);

        // Scores tab
        renderScores(r, data);

        // Logs raw tab
        document.getElementById('logsRaw').textContent = JSON.stringify({
            job: job,
            result: r,
            logs: logs,
            raw_text_preview: data.raw_text_preview
        }, null, 2);
    }

    function renderPipeline(logs, data) {
        const container = document.getElementById('pipelineTimeline');
        container.innerHTML = '';

        const stages = ['INGEST','PARSE','EXTRACT','MATCH','SCORE','FILTER','DECISION'];
        const stageLogs = {};
        logs.forEach(l => { if (!stageLogs[l.stage]) stageLogs[l.stage] = []; stageLogs[l.stage].push(l); });

        stages.forEach(stage => {
            const entries = stageLogs[stage] || [];
            const step = document.createElement('div');
            step.className = 'pipeline-step done';
            if (entries.some(e => e.severity === 'WARN')) step.classList.add('warn');
            if (entries.some(e => e.severity === 'ERROR')) step.classList.add('error');

            const titles = { INGEST: '📥 Ingestão', PARSE: '🔍 Parsing', EXTRACT: '🧬 Extração',
                MATCH: '🎯 Matching', SCORE: '📊 Scoring', FILTER: '🚧 Filtros', DECISION: '✅ Decisão' };

            let bodyHtml = '';
            entries.forEach(e => {
                bodyHtml += `<div style="margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid var(--border);">`;
                bodyHtml += `<strong>${e.action}</strong>`;
                if (e.severity !== 'INFO') bodyHtml += ` <span style="color:var(--${e.severity==='WARN'?'warning':'danger'})">[${e.severity}]</span>`;
                bodyHtml += `<pre style="margin-top:6px;font-size:0.8rem;">${JSON.stringify(e.details, null, 2)}</pre>`;
                bodyHtml += `</div>`;
            });

            if (stage === 'PARSE' && data.raw_text_preview) {
                bodyHtml += `<div style="margin-top:10px;"><label style="color:var(--text-muted);font-size:0.8rem;">Texto bruto (primeiros 500 chars):</label><pre>${escapeHtml(data.raw_text_preview)}</pre></div>`;
            }

            step.innerHTML = `
                <div class="step-header">
                    <span class="step-icon">${titles[stage]?.split(' ')[0] || '•'}</span>
                    <span class="step-title">${titles[stage] || stage}</span>
                    <span class="step-time">${entries.length} log(s)</span>
                </div>
                <div class="step-body">${bodyHtml || '<em style="color:var(--text-muted)">Nenhum log nesta etapa</em>'}</div>
            `;
            container.appendChild(step);
        });
    }

    function renderRaw(data) {
        const meta = document.getElementById('rawMeta');
        const preview = data.raw_text_preview || '';
        const fullText = data.raw_text || preview.replace('...','');

        // Tenta extrair metadados dos logs
        const parseLogs = (data.logs || []).filter(l => l.stage === 'PARSE');
        const ingestLogs = (data.logs || []).filter(l => l.stage === 'INGEST');
        const engine = parseLogs[0]?.details?.engine || parseLogs[0]?.details?.engines_available?.join(', ') || '—';
        const pages = parseLogs[0]?.details?.pages || '—';
        const chars = parseLogs[0]?.details?.chars || fullText.length;
        const size = ingestLogs[0]?.details?.size_bytes ? (ingestLogs[0].details.size_bytes/1024).toFixed(1) + ' KB' : '—';
        const isImage = parseLogs.some(l => l.details?.is_image_pdf) ? 'Sim ⚠️' : 'Não ✅';

        meta.innerHTML = `
            <div class="meta-card"><label>Engine</label><value>${engine}</value></div>
            <div class="meta-card"><label>Páginas</label><value>${pages}</value></div>
            <div class="meta-card"><label>Caracteres</label><value>${chars.toLocaleString()}</value></div>
            <div class="meta-card"><label>Tamanho</label><value>${size}</value></div>
            <div class="meta-card"><label>PDF Imagem?</label><value>${isImage}</value></div>
            <div class="meta-card"><label>Formato</label><value>${ingestLogs[0]?.details?.format?.toUpperCase() || '—'}</value></div>
        `;
        document.getElementById('rawText').textContent = fullText;
    }

    function renderEntities(data) {
        const r = data.result;
        const logs = data.logs || [];
        const extractLogs = logs.filter(l => l.stage === 'EXTRACT');
        const logContact = extractLogs[0]?.details || {};
        // Merge: result has priority, then debug contact, then logs
        const contact = {
            name: r?.candidate_name || data.debug?.contact?.name || logContact.name || '',
            email: data.debug?.contact?.email || logContact.email || '',
            phone: data.debug?.contact?.phone || logContact.phone || '',
            linkedin: data.debug?.contact?.linkedin || logContact.linkedin || '',
        };

        const grid = document.getElementById('entitiesGrid');
        grid.innerHTML = `
            <div class="entity-card">
                <div class="entity-label">Nome</div>
                <div class="entity-value ${contact.name ? '' : 'missing'}">${contact.name || 'Não detectado'}</div>
            </div>
            <div class="entity-card">
                <div class="entity-label">Email</div>
                <div class="entity-value ${contact.email ? '' : 'missing'}">${contact.email || 'Não detectado'}</div>
            </div>
            <div class="entity-card">
                <div class="entity-label">Telefone</div>
                <div class="entity-value ${contact.phone ? '' : 'missing'}">${contact.phone || 'Não detectado'}</div>
            </div>
            <div class="entity-card">
                <div class="entity-label">LinkedIn</div>
                <div class="entity-value ${contact.linkedin ? '' : 'missing'}">${contact.linkedin || 'Não detectado'}</div>
            </div>
        `;

        // Seções detectadas (simuladas a partir do texto)
        const sectionsList = document.getElementById('sectionsList');
        const raw = (data.raw_text || data.raw_text_preview || '').toLowerCase();
        const sections = [];
        if (raw.includes('resumo') || raw.includes('objetivo')) sections.push({name: 'Resumo/Objetivo', lines: 'detectado'});
        if (raw.includes('experiência') || raw.includes('experiencia') || raw.includes('profissional')) sections.push({name: 'Experiência Profissional', lines: 'detectado'});
        if (raw.includes('formação') || raw.includes('formacao') || raw.includes('educação') || raw.includes('educacao')) sections.push({name: 'Formação/Educação', lines: 'detectado'});
        if (raw.includes('skill') || raw.includes('habilidade') || raw.includes('competência') || raw.includes('tecnologia')) sections.push({name: 'Skills/Habilidades', lines: 'detectado'});
        if (raw.includes('projeto')) sections.push({name: 'Projetos', lines: 'detectado'});
        if (raw.includes('idioma') || raw.includes('language')) sections.push({name: 'Idiomas', lines: 'detectado'});
        if (raw.includes('certifica')) sections.push({name: 'Certificações', lines: 'detectado'});

        sectionsList.innerHTML = sections.map(s => `
            <div class="section-item">
                <span class="section-name">${s.name}</span>
                <span class="section-lines">${s.lines}</span>
            </div>
        `).join('') || '<em style="color:var(--text-muted)">Nenhuma seção detectada automaticamente</em>';
    }

    function renderKeywords(result, job) {
        const summary = document.getElementById('keywordsSummary');
        const totalReq = job.required_skills.length;
        const totalPref = job.preferred_skills.length;
        const matchedReq = result.matched_keywords.filter(k => job.required_skills.includes(k)).length;
        const matchedPref = result.matched_keywords.filter(k => job.preferred_skills.includes(k)).length;
        const density = result.keyword_density_score;

        summary.innerHTML = `
            <div class="kw-stat matched"><div class="kw-number">${matchedReq}/${totalReq}</div><div class="kw-label">Obrigatórias</div></div>
            <div class="kw-stat matched"><div class="kw-number">${matchedPref}/${totalPref}</div><div class="kw-label">Desejáveis</div></div>
            <div class="kw-stat missing"><div class="kw-number">${result.missing_keywords.length}</div><div class="kw-label">Faltando</div></div>
            <div class="kw-stat density"><div class="kw-number">${density}%</div><div class="kw-label">Densidade</div></div>
        `;

        const tables = document.getElementById('keywordsTables');
        let html = '';

        // Tabela de obrigatórias
        html += '<div class="kw-table-wrap"><h4>⭐ Skills Obrigatórias</h4>';
        html += '<table class="kw-table"><thead><tr><th>Skill</th><th>Status</th><th>Tipo</th></tr></thead><tbody>';
        job.required_skills.forEach(sk => {
            const found = result.matched_keywords.includes(sk);
            html += `<tr><td>${sk}</td><td><span class="badge ${found ? 'badge-found' : 'badge-missing'}">${found ? '✅ Encontrada' : '❌ Faltando'}</span></td><td><span class="badge badge-exact">exact</span></td></tr>`;
        });
        html += '</tbody></table></div>';

        // Tabela de desejáveis
        if (job.preferred_skills.length) {
            html += '<div class="kw-table-wrap"><h4>✨ Skills Desejáveis</h4>';
            html += '<table class="kw-table"><thead><tr><th>Skill</th><th>Status</th><th>Tipo</th></tr></thead><tbody>';
            job.preferred_skills.forEach(sk => {
                const found = result.matched_keywords.includes(sk);
                html += `<tr><td>${sk}</td><td><span class="badge ${found ? 'badge-found' : 'badge-missing'}">${found ? '✅ Encontrada' : '❌ Faltando'}</span></td><td><span class="badge badge-exact">exact</span></td></tr>`;
            });
            html += '</tbody></table></div>';
        }

        // Faltando
        if (result.missing_keywords.length) {
            html += '<div class="kw-table-wrap"><h4>❌ Keywords Faltando</h4>';
            html += '<div style="display:flex;flex-wrap:wrap;gap:8px;">';
            result.missing_keywords.forEach(k => {
                html += `<span class="badge badge-missing" style="font-size:0.9rem;padding:6px 12px;">${k}</span>`;
            });
            html += '</div></div>';
        }

        tables.innerHTML = html;
    }

    function renderScores(result, data) {
        const breakdown = document.getElementById('scoresBreakdown');
        const scores = [
            { name: '🎯 Skill Match', score: result.skill_match_score, weight: 0.35, formula: 'required_match + preferred_match/2' },
            { name: '💼 Experiência', score: result.experience_score, weight: 0.25, formula: 'anos_detectados / anos_requeridos * 100' },
            { name: '🎓 Educação', score: result.education_score, weight: 0.15, formula: 'nível_detectado >= nível_requerido ? 100 : 70' },
            { name: '📝 Formatação', score: result.formatting_score, weight: 0.10, formula: '100 - penalidades' },
            { name: '🧠 Semântico', score: result.semantic_score, weight: 0.15, formula: 'responsabilidades_match / total * 100' },
        ];

        let html = '';
        scores.forEach(s => {
            const cls = s.score >= 70 ? 'high' : s.score >= 50 ? 'medium' : 'low';
            html += `
                <div class="score-row">
                    <div class="score-name">${s.name}</div>
                    <div class="score-bar-wrap"><div class="score-bar ${cls}" style="width:${s.score}%"></div></div>
                    <div class="score-value">${s.score.toFixed(1)}</div>
                    <div class="score-weight">${(s.weight*100).toFixed(0)}%</div>
                </div>
                <div class="score-formula">Fórmula: ${s.formula} | Peso: ${s.weight}</div>
            `;
        });

        // Overall
        html += `
            <div class="score-row" style="margin-top:12px;padding-top:16px;border-top:2px solid var(--border);">
                <div class="score-name" style="font-weight:700;font-size:1.1rem;">🏆 Score Final</div>
                <div class="score-bar-wrap"><div class="score-bar ${result.overall_score >= 70 ? 'high' : result.overall_score >= 50 ? 'medium' : 'low'}" style="width:${result.overall_score}%"></div></div>
                <div class="score-value" style="font-size:1.2rem;">${result.overall_score.toFixed(1)}</div>
                <div class="score-weight">100%</div>
            </div>
            <div class="score-formula">Fórmula: Σ(score × peso) / Σ(pesos)</div>
        `;
        breakdown.innerHTML = html;

        // Red flags
        if (result.red_flags && result.red_flags.length) {
            let flagsHtml = '<h4 style="margin:20px 0 12px;">🚩 Red Flags</h4>';
            result.red_flags.forEach(f => {
                flagsHtml += `<div class="red-flag">${f}</div>`;
            });
            breakdown.innerHTML = breakdown.innerHTML + flagsHtml;
        }

        // Recommendations
        const recs = document.getElementById('recommendations');
        if (result.recommendations && result.recommendations.length) {
            recs.innerHTML = '<h4>💡 Recomendações</h4><ul>' +
                result.recommendations.map(r => `<li>${r}</li>`).join('') + '</ul>';
        } else {
            recs.innerHTML = '';
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
