let currentStep = 1;
const totalSteps = 7;

// Inicializar com 1 experiência e 1 educação
window.addEventListener('DOMContentLoaded', () => {
    addExperience();
    addEducation();
    updateProgress();
});

function updateProgress() {
    const pct = (currentStep / totalSteps) * 100;
    document.getElementById('progressFill').style.width = pct + '%';
    const stepsEl = document.getElementById('progressSteps');
    const labels = ['Dados','Resumo','Experiência','Projetos','Educação','Skills','Download'];
    stepsEl.innerHTML = labels.map((l, i) => {
        const cls = i + 1 === currentStep ? 'active' : i + 1 < currentStep ? 'done' : '';
        return `<div class="progress-step ${cls}">${i + 1}. ${l}</div>`;
    }).join('');
    document.getElementById('btnPrev').disabled = currentStep === 1;
    const nextBtn = document.getElementById('btnNext');
    nextBtn.textContent = currentStep === totalSteps ? 'Concluir' : 'Próximo →';
}

function changeStep(dir) {
    if (dir === 1 && !validateStep(currentStep)) return;
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.remove('active');
    currentStep = Math.max(1, Math.min(totalSteps, currentStep + dir));
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.add('active');
    updateProgress();
    if (currentStep === 7) updatePreview();
}

function validateStep(step) {
    const active = document.querySelector(`.step[data-step="${step}"]`);
    const required = active.querySelectorAll('[required]');
    for (const el of required) {
        if (!el.value.trim()) {
            el.focus();
            el.style.borderColor = 'var(--danger)';
            setTimeout(() => el.style.borderColor = '', 2000);
            return false;
        }
    }
    return true;
}

// Experiências
function addExperience() {
    const container = document.getElementById('experiencesContainer');
    const idx = container.children.length;
    const div = document.createElement('div');
    div.className = 'dynamic-item';
    div.innerHTML = `
        <button type="button" class="remove-btn" onclick="this.parentElement.remove()">Remover</button>
        <div class="form-grid">
            <div class="field"><label>Cargo *</label><input type="text" class="exp-role" placeholder="Desenvolvedor Full Stack" required></div>
            <div class="field"><label>Empresa *</label><input type="text" class="exp-company" placeholder="LNCC" required></div>
            <div class="field"><label>Local</label><input type="text" class="exp-location" placeholder="Petrópolis, RJ — Remoto"></div>
            <div class="field"><label>Data Início (MM/AAAA) *</label><input type="text" class="exp-start" placeholder="02/2024" required></div>
            <div class="field"><label>Data Fim (MM/AAAA ou Atual) *</label><input type="text" class="exp-end" placeholder="Atual" required></div>
        </div>
        <div class="field full">
            <label>Bullets (1 por linha) — Use a Fórmula XYZ</label>
            <textarea class="exp-bullets" rows="4" placeholder="Desenvolvi aplicação web full stack com Node.js e React, resultando em visualização 3D de dados científicos.
Construí APIs RESTful com autenticação JWT e controle de acesso RBAC." required></textarea>
        </div>
    `;
    container.appendChild(div);
}

// Projetos
function addProject() {
    const container = document.getElementById('projectsContainer');
    const div = document.createElement('div');
    div.className = 'dynamic-item';
    div.innerHTML = `
        <button type="button" class="remove-btn" onclick="this.parentElement.remove()">Remover</button>
        <div class="form-grid">
            <div class="field"><label>Nome do Projeto *</label><input type="text" class="proj-name" placeholder="Sistema de Gerenciamento" required></div>
            <div class="field"><label>Data Início (MM/AAAA)</label><input type="text" class="proj-start" placeholder="06/2023"></div>
            <div class="field"><label>Data Fim (MM/AAAA)</label><input type="text" class="proj-end" placeholder="01/2024"></div>
            <div class="field"><label>Link (https://...)</label><input type="text" class="proj-link" placeholder="https://github.com/usuario/projeto"></div>
        </div>
        <div class="field full">
            <label>Descrição — Fórmula XYZ + Tecnologias</label>
            <textarea class="proj-desc" rows="3" placeholder="Desenvolvi backend com Python e Flask, criando APIs RESTful completas com modelagem MySQL."></textarea>
        </div>
    `;
    container.appendChild(div);
}

// Educação
function addEducation() {
    const container = document.getElementById('educationContainer');
    const div = document.createElement('div');
    div.className = 'dynamic-item';
    div.innerHTML = `
        <button type="button" class="remove-btn" onclick="this.parentElement.remove()">Remover</button>
        <div class="form-grid">
            <div class="field"><label>Curso / Grau *</label><input type="text" class="edu-degree" placeholder="Graduação Tecnóloga em TIC" required></div>
            <div class="field"><label>Instituição *</label><input type="text" class="edu-school" placeholder="FAETERJ" required></div>
            <div class="field"><label>Data Início (MM/AAAA)</label><input type="text" class="edu-start" placeholder="02/2022"></div>
            <div class="field"><label>Data Fim (MM/AAAA ou Previsto)</label><input type="text" class="edu-end" placeholder="12/2026 (previsto)"></div>
            <div class="field"><label>Nível</label>
                <select class="edu-level">
                    <option value="tecnico">Técnico</option>
                    <option value="tecnologo" selected>Tecnólogo</option>
                    <option value="graduacao">Bacharel/Licenciatura</option>
                    <option value="mestrado">Mestrado/Pós</option>
                    <option value="phd">Doutorado/PhD</option>
                </select>
            </div>
        </div>
    `;
    container.appendChild(div);
}

// Gerar HTML do CV
function generateCVHTML() {
    const name = document.getElementById('fullName').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    const linkedin = document.getElementById('linkedin').value;
    const location = document.getElementById('location').value;
    const summary = document.getElementById('summary').value;
    const contextBleed = document.getElementById('contextBleed').value;
    const languages = document.getElementById('languages').value;

    // Experiências
    let expHTML = '';
    document.querySelectorAll('#experiencesContainer .dynamic-item').forEach(item => {
        const role = item.querySelector('.exp-role').value;
        const company = item.querySelector('.exp-company').value;
        const loc = item.querySelector('.exp-location').value;
        const start = item.querySelector('.exp-start').value;
        const end = item.querySelector('.exp-end').value;
        const bullets = item.querySelector('.exp-bullets').value.split('\n').filter(b => b.trim());
        expHTML += `
            <div style="margin-bottom:18px;">
                <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;">
                    <div><strong style="font-size:1.05rem;">${role}</strong> <span style="color:#4a5568;">— ${company}</span></div>
                    <span style="color:#718096;font-size:0.9rem;">${start} — ${end}</span>
                </div>
                ${loc ? `<div style="color:#718096;font-size:0.9rem;margin-bottom:6px;">${loc}</div>` : ''}
                <ul style="padding-left:22px;margin-top:6px;">
                    ${bullets.map(b => `<li style="margin-bottom:4px;">${b.trim()}</li>`).join('')}
                </ul>
            </div>
        `;
    });

    // Projetos
    let projHTML = '';
    document.querySelectorAll('#projectsContainer .dynamic-item').forEach(item => {
        const name = item.querySelector('.proj-name').value;
        const start = item.querySelector('.proj-start').value;
        const end = item.querySelector('.proj-end').value;
        const link = item.querySelector('.proj-link').value;
        const desc = item.querySelector('.proj-desc').value;
        if (!name && !desc) return;
        projHTML += `
            <div style="margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;">
                    <strong>${name}</strong>
                    <span style="color:#718096;font-size:0.9rem;">${start}${end ? ' — ' + end : ''}</span>
                </div>
                ${desc ? `<div style="margin-top:4px;">${desc}</div>` : ''}
                ${link ? `<div style="margin-top:4px;"><a href="${link}" style="color:#2c5282;">${link}</a></div>` : ''}
            </div>
        `;
    });

    // Educação
    let eduHTML = '';
    document.querySelectorAll('#educationContainer .dynamic-item').forEach(item => {
        const degree = item.querySelector('.edu-degree').value;
        const school = item.querySelector('.edu-school').value;
        const start = item.querySelector('.edu-start').value;
        const end = item.querySelector('.edu-end').value;
        eduHTML += `
            <div style="margin-bottom:12px;">
                <div style="font-weight:700;">${degree}</div>
                <div style="color:#4a5568;">${school}</div>
                <div style="color:#718096;font-size:0.9rem;">${start}${end ? ' — ' + end : ''}</div>
            </div>
        `;
    });

    // Skills
    const cats = [
        { label: 'Linguagens', val: document.getElementById('skillsLang').value },
        { label: 'Frameworks / Bibliotecas', val: document.getElementById('skillsFrameworks').value },
        { label: 'Bancos de Dados', val: document.getElementById('skillsDbs').value },
        { label: 'Infra / DevOps', val: document.getElementById('skillsInfra').value },
        { label: 'Ferramentas / Outros', val: document.getElementById('skillsTools').value },
    ];
    let skillsHTML = '';
    cats.forEach(c => {
        if (c.val.trim()) {
            const items = c.val.split(',').map(s => s.trim()).filter(Boolean);
            skillsHTML += `<div style="margin-bottom:10px;"><strong style="font-size:0.85rem;color:#4a5568;text-transform:uppercase;">${c.label}:</strong> ${items.join(', ')}</div>`;
        }
    });

    return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>${name} - CV</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',Arial,sans-serif; background:#f5f5f5; color:#333; line-height:1.6; padding:40px 20px; }
.container { max-width:800px; margin:0 auto; background:white; padding:50px 60px; box-shadow:0 2px 10px rgba(0,0,0,0.1); }
.header { border-bottom:2px solid #2c5282; padding-bottom:20px; margin-bottom:25px; }
.header h1 { font-size:2.2rem; color:#2c5282; margin-bottom:8px; }
.contact-line { display:flex; flex-wrap:wrap; gap:20px; font-size:0.95rem; color:#555; }
h2 { font-size:1.15rem; color:#2c5282; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid #e2e8f0; padding-bottom:6px; margin:25px 0 15px 0; }
.summary { text-align:justify; }
ul { padding-left:22px; }
li { margin-bottom:4px; }
@media print { body { background:white; padding:0; } .container { box-shadow:none; padding:30px; } }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>${name}</h1>
        <div class="contact-line">
            <span>&#9993; ${email}</span>
            <span>&#9742; ${phone}</span>
            ${linkedin ? `<span>&#127758; ${linkedin}</span>` : ''}
            ${location ? `<span>&#128205; ${location}</span>` : ''}
        </div>
    </div>

    <h2>Resumo Profissional</h2>
    <p class="summary">${summary.replace(/\n/g, '<br>')}</p>
    ${contextBleed ? `<p class="summary" style="margin-top:8px;"><strong>${contextBleed}</strong></p>` : ''}

    <h2>Experiência Profissional</h2>
    ${expHTML}

    ${projHTML ? `<h2>Projetos / Portfólio</h2>${projHTML}` : ''}

    <h2>Formação Acadêmica</h2>
    ${eduHTML}

    <h2>Habilidades Técnicas</h2>
    ${skillsHTML}

    ${languages ? `<h2>Idiomas</h2><p>${languages}</p>` : ''}
</div>
</body>
</html>`;
}

function updatePreview() {
    const html = generateCVHTML();
    const blob = new Blob([html], { type: 'text/html' });
    document.getElementById('previewFrame').src = URL.createObjectURL(blob);
}

function downloadHTML() {
    const html = generateCVHTML();
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cv_ats_optimized.html';
    a.click();
    URL.revokeObjectURL(url);
}

function downloadText() {
    const html = generateCVHTML();
    // Extrair texto puro para testar no ATS
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const text = doc.body.innerText;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cv_ats_optimized.txt';
    a.click();
    URL.revokeObjectURL(url);
}
