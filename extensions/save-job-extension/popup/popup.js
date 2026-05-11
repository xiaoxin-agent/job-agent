/**
 * Popup script for Job Saver extension.
 * 1. Requests extraction from content script
 * 2. Shows preview
 * 3. On save, POSTs to agent_web API
 */

const STORAGE_KEY = 'job_saver_config';

// ─── DOM refs ───
const $ = id => document.getElementById(id);
const stateLoading   = $('state-loading');
const stateResult    = $('state-result');
const stateError     = $('state-error');
const jobTitle       = $('job-title');
const jobCompany     = $('job-company');
const jobLocation    = $('job-location');
const jobType        = $('job-type');
const jobDesc        = $('job-description');
const strategiesEl   = $('strategies-used');
const serverStatus   = $('server-status');
const statusText     = $('status-text');
const statusDot      = serverStatus.querySelector('.dot');
const btnSave        = $('btn-save');
const btnRetry       = $('btn-retry');
const saveResult     = $('save-result');
const errorMsg       = $('error-message');
const btnErrorRetry  = $('btn-error-retry');

// Settings elements
const settingsPanel = $('settings-panel');
const settingsBtn   = $('btn-settings-toggle');
const apiUrlInput   = $('api-url');
const saveSettingsBtn = $('btn-save-settings');

let currentJob = null;
let apiBase = 'http://localhost:9999';

// ─── Init ───
document.addEventListener('DOMContentLoaded', async () => {
  // Load saved config
  const config = await chrome.storage.sync.get(STORAGE_KEY);
  if (config[STORAGE_KEY] && config[STORAGE_KEY].apiBase) {
    apiBase = config[STORAGE_KEY].apiBase;
    apiUrlInput.value = apiBase;
  }

  // Check server health first
  const serverOk = await checkServer();

  // Then extract job from page
  if (serverOk !== false) {
    await extractAndShow();
  }
});

// ─── Settings Toggle ───
settingsBtn.addEventListener('click', () => {
  settingsPanel.classList.toggle('hidden');
});

saveSettingsBtn.addEventListener('click', async () => {
  const newUrl = apiUrlInput.value.trim().replace(/\/+$/, '');
  if (!newUrl) {
    apiUrlInput.style.borderColor = '#ef4444';
    return;
  }
  apiUrlInput.style.borderColor = '';
  apiBase = newUrl;
  await chrome.storage.sync.set({ [STORAGE_KEY]: { apiBase } });
  settingsPanel.classList.add('hidden');
  // Re-check server
  await checkServer();
});

// ─── Server Health Check ───
async function checkServer() {
  try {
    const resp = await fetch(`${apiBase}/api/list_resumes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (resp.ok) {
      statusDot.className = 'dot dot-online';
      statusText.textContent = `Agent 在线 (${apiBase}) ✓`;
      return true;
    } else {
      throw new Error(`HTTP ${resp.status}`);
    }
  } catch (e) {
    statusDot.className = 'dot dot-offline';
    statusText.textContent = `Agent 离线 — 请确认服务在 ${apiBase} 运行`;
    btnSave.disabled = true;
    return false;
  }
}

// ─── Extract Job ───
async function extractAndShow() {
  showLoading();

  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const tab = tabs[0];

    if (!tab) {
      showError('无法获取当前标签页');
      return;
    }

    // Check if we can inject into this page
    if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('about:') || tab.url.startsWith('edge://')) {
      showError('不支持在此页面提取（浏览器内部页面）');
      return;
    }

    // Request extraction from content script
    const response = await chrome.tabs.sendMessage(tab.id, { action: 'extract_job' });

    if (response && (response.title || response.description)) {
      currentJob = response;
      showResult(response);
    } else {
      // Content script may not be injected yet on some pages
      // Try injecting programmatically using scripting API
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['content/extractor.js'],
        });
        // Small delay to let script initialize
        await new Promise(r => setTimeout(r, 100));
        const retryResponse = await chrome.tabs.sendMessage(tab.id, { action: 'extract_job' });
        if (retryResponse && (retryResponse.title || retryResponse.description)) {
          currentJob = retryResponse;
          showResult(retryResponse);
        } else {
          showError('未能从页面提取到职位信息。\n请确保您在职位详情页面上。');
        }
      } catch (injectErr) {
        showError('提取失败：' + (injectErr.message || '未知错误'));
      }
    }
  } catch (e) {
    console.error('Extraction error:', e);
    if (e.message && e.message.includes('Receiving end does not exist')) {
      showError('页面尚未完全加载，请刷新后重试');
    } else {
      showError('提取失败：' + (e.message || '未知错误'));
    }
  }
}

// ─── Show States ───
function showLoading() {
  stateLoading.classList.remove('hidden');
  stateResult.classList.add('hidden');
  stateError.classList.add('hidden');
  saveResult.classList.add('hidden');
}

function showResult(job) {
  stateLoading.classList.add('hidden');
  stateResult.classList.remove('hidden');
  stateError.classList.add('hidden');
  saveResult.classList.add('hidden');

  jobTitle.textContent = job.title || '(未识别)';
  jobCompany.textContent = job.company || '(未识别)';
  jobLocation.textContent = job.location || '(未识别)';
  jobType.textContent = job.job_type || '(未识别)';
  jobDesc.value = job.description || '(无描述)';

  const strategies = job.strategies_used || [];
  strategiesEl.textContent = strategies.length
    ? strategies.join(' → ')
    : '标准提取';

  btnSave.disabled = false;
}

function showError(message) {
  stateLoading.classList.add('hidden');
  stateResult.classList.add('hidden');
  stateError.classList.remove('hidden');
  errorMsg.textContent = message;
}

// ─── Save Job ───
btnSave.addEventListener('click', async () => {
  if (!currentJob) return;

  btnSave.disabled = true;
  btnSave.textContent = '⏳ 保存中...';
  saveResult.classList.add('hidden');

  try {
    const jobData = {
      title: currentJob.title || document.title || 'Untitled Position',
      company: currentJob.company || '',
      location: currentJob.location || '',
      description: currentJob.description || '',
      job_type: currentJob.job_type || '',
      url: currentJob.url || window.location.href,
      source: currentJob.source || 'web_extractor',
    };

    const resp = await fetch(`${apiBase}/api/save_job`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job: jobData }),
    });

    const result = await resp.json();

    if (result.success) {
      showSaveMessage('✅ 职位已保存！Agent 会自动分析匹配度并生成求职信。', 'success');
      setTimeout(() => window.close(), 2000);
    } else {
      showSaveMessage('❌ 保存失败：' + (result.error || '未知错误'), 'error');
    }
  } catch (e) {
    showSaveMessage('❌ 保存失败：无法连接到求职 Agent (' + e.message + ')', 'error');
  } finally {
    btnSave.textContent = '💾 保存到求职Agent';
    btnSave.disabled = false;
  }
});

function showSaveMessage(text, type) {
  saveResult.textContent = text;
  saveResult.className = 'save-result ' + type;
  saveResult.classList.remove('hidden');
}

// ─── Retry ───
function retryAll() {
  currentJob = null;
  saveResult.classList.add('hidden');
  btnSave.disabled = true;
  extractAndShow();
}

btnRetry.addEventListener('click', retryAll);
btnErrorRetry.addEventListener('click', retryAll);
